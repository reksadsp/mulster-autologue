#!/usr/bin/env bash
set -e  # stop on error

echo "🚀 Starting Mulster environment..."
export CI=1
source .ngrok
source .env
export "NGROK_AUTH_TOKEN"
export "PERPLEXITY_API_KEY"

# 1️⃣ Ensure Docker is available (macOS)
if ! command -v docker &> /dev/null; then
    echo "Installing Docker via Homebrew..."
    brew install --cask docker
    open -a Docker
    echo "🕓 Waiting for Docker Desktop to start..."
    while ! docker info >/dev/null 2>&1; do
        sleep 2
    done
fi
echo -e "✅ Docker is installed.\n"

echo "🧹 Cleaning up old containers..."
docker-compose down
docker rm bridge 2>/dev/null || true
docker rm llama 2>/dev/null || true
docker rm auto 2>/dev/null || true
docker rm mcp 2>/dev/null || true
# Force kill any lingering ollama processes
docker kill llama 2>/dev/null || true
sleep 2

# 2️⃣ Start services in detached mode
echo -e "\n🧩 Starting docker-compose services..."
docker-compose up -d
echo -e "✅ Docker is ready.\n"

# 3️⃣ Copy environment and data
echo "📦 Copying environment files..."
docker cp ~/Mulster/autologue/.env auto:/app/
docker cp ~/Mulster/autologue/.ngrok bridge:/bridge/
docker cp ~/Mulster/autologue/mulsterdb.dump data:/mulsterdb.dump
echo -e "✅ Environment is ready.\n"

# 4️⃣ Wait for Postgres to be ready
echo "⏳ Waiting for Postgres to accept connections..."
until docker exec data pg_isready -U admin -d mulsterdb > /dev/null 2>&1; do
  sleep 1
done
echo -e "✅ Postgres is ready.\n"

# 5️⃣ Restore DB dump (idempotent)
echo "🗄️ Restoring database..."
docker exec -i data psql -U admin -d postgres \
  -c "DROP DATABASE IF EXISTS mulsterdb;"
docker exec -i data psql -U admin -d postgres \
  -c "CREATE DATABASE mulsterdb;"
docker exec -i data pg_restore -U admin -d mulsterdb --no-owner /mulsterdb.dump
docker exec -i data psql -q --set=ON_ERROR_STOP=1 -U admin -d mulsterdb \
  -c "ALTER ROLE admin SET search_path TO mulsterdb, public;"
echo -e "✅ Database is ready.\n"

# 6️⃣ Run NGROK port tunneling
echo "📡 Port forwarding..."
docker exec bridge ngrok config add-authtoken $NGROK_AUTH_TOKEN >/dev/null 2>&1
# Start ngrok in background (v3 syntax)
docker exec -d bridge bash -c "ngrok http 8000 --log=stdout > /tmp/ngrok.log 2>&1"
# Wait for ngrok to be ready
echo "Waiting for ngrok to start..."
for i in {1..30}; do
    if docker exec bridge curl -s http://127.0.0.1:4040/api/tunnels >/dev/null 2>&1; then
        break
    fi
    sleep 1
done
sleep 1
# Get the URL
NGROK_RESPONSE=$(docker exec bridge curl -s http://127.0.0.1:4040/api/tunnels)
NGROK_URL=$(echo "$NGROK_RESPONSE" | grep -o '"public_url":"https://[^"]*"' | cut -d'"' -f4 | head -n 1)
if [ -z "$NGROK_URL" ]; then
    echo "❌ Failed to get ngrok URL"
    docker exec bridge cat /tmp/ngrok.log
    exit 1
fi
echo "Ngrok public URL: $NGROK_URL"
echo -e "✅ Ngrok is ready.\n"

# 7️⃣ Preparing Ollama
echo "🦙 Preparing Ollama..."
echo "Waiting for Ollama to be ready..."
max_attempts=60
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if docker exec llama ollama list >/dev/null 2>&1; then
        echo "✅ Ollama service is responsive"
        break
    fi
    attempt=$((attempt + 1))
    echo "Waiting... ($attempt/$max_attempts)"
    sleep 2
done
if [ $attempt -eq $max_attempts ]; then
    echo "❌ Ollama failed to start. Checking logs..."
    docker logs llama
    exit 1
fi
# Pull model
echo "Pulling phi model..."
docker exec llama ollama pull phi
if [ $? -eq 0 ]; then
    echo -e "✅ Ollama is ready with phi model.\n"
else
    echo "❌ Failed to pull phi."
    exit 1
fi

echo -e "🎉 Mulster autologue system ready!\n"

echo "⚙️ Starting catalogue automatic refill..."
docker exec -i auto bash -c "python main.py"

echo "Cleaning up containers..."
docker-compose down
docker rm bridge 2>/dev/null || true
docker rm llama 2>/dev/null || true
docker rm auto 2>/dev/null || true
docker rm mcp 2>/dev/null || true
# Force kill any lingering ollama processes
docker kill llama 2>/dev/null || true
sleep 2
