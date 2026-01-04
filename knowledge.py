from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict
import subprocess
import requests
import asyncio
import uvicorn
import logging
import json
import time
import os
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== ngrok Management ====================
def get_ngrok_url(retries: int = 10, delay: float = 1) -> Optional[str]:
    """Retrieve ngrok public HTTPS URL using regex matching"""
    ngrok_api_url = "http://127.0.0.1:4040/api/tunnels"
    
    for attempt in range(retries):
        try:
            response = requests.get(ngrok_api_url, timeout=5)
            response.raise_for_status()
            
            # Use regex to extract the HTTPS URL from the response
            # Pattern: "public_url":"https://[^"]*"
            match = re.search(r'"public_url":"(https://[^"]*)"', response.text)
            if match:
                public_url = match.group(1)
                logger.info(f"Found ngrok URL: {public_url}")
                return public_url
            
            logger.warning(f"No HTTPS tunnel found (attempt {attempt + 1}/{retries})")
        except Exception as e:
            logger.warning(f"Failed to get ngrok URL (attempt {attempt + 1}/{retries}): {e}")
        
        if attempt < retries - 1:
            time.sleep(delay)
    
    logger.error("Failed to retrieve ngrok URL after all retries")
    return None

# ==================== Client Class ====================
class MCPClient:

    def __init__(self, bridge_url: str):
        self.bridge_url = bridge_url.rstrip("/")
        self.session = requests.Session()
        self.timeout = 30
        self.session.headers.update({
            "ngrok-skip-browser-warning": "true",
            "User-Agent": "MCP-Client/1.0"
        })
    
    def _request(self, method: str, endpoint: str, json_data: dict = None) -> dict:
        url = f"{self.bridge_url}{endpoint}"
        try:
            if method == "GET":
                response = self.session.get(url, timeout=self.timeout)
            elif method == "POST":
                response = self.session.post(url, json=json_data, timeout=self.timeout)
            elif method == "DELETE":
                response = self.session.delete(url, json=json_data, timeout=self.timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error(f"Request to {url} timed out")
            raise
        except requests.exceptions.ConnectionError:
            logger.error(f"Failed to connect to {url}. Is the server running?")
            raise
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise
            
    # ============ Entities ============
    def create_entities(self, entities: list) -> dict:
        """Create entities in knowledge graph"""
        return self._request("POST", "/entities", {"entities": entities})
    def delete_entities(self, entity_names: list) -> dict:
        """Delete entities by name"""
        return self._request("DELETE", "/entities", {"entityNames": entity_names})
    # ============ Relations ============
    def create_relations(self, relations: list) -> dict:
        """Create relations between entities"""
        return self._request("POST", "/relations", {"relations": relations})
    def delete_relations(self, relations: list) -> dict:
        """Delete relations"""
        return self._request("DELETE", "/relations", {"relations": relations})
    # ============ Observations ============
    def add_observations(self, observations: list) -> dict:
        """Add observations/facts to entities"""
        return self._request("POST", "/observations", {"observations": observations})
    def delete_observations(self, deletions: list) -> dict:
        """Delete observations"""
        return self._request("DELETE", "/observations", {"deletions": deletions})
    # ============ Graph ============
    def read_graph(self) -> dict:
        """Read entire knowledge graph"""
        return self._request("GET", "/graph")
    # ============ Nodes ============
    def search_nodes(self, query: str) -> dict:
        """Search for nodes by query"""
        return self._request("POST", "/nodes/search", {"query": query})
    def open_nodes(self, names: list) -> dict:
        """Retrieve specific nodes by name"""
        return self._request("POST", "/nodes/open", {"names": names})
    # ============ Utility ============
    def status(self) -> dict:
        """Check server status"""
        return self._request("GET", "/status")
    def reset(self) -> dict:
        """Reset knowledge graph"""
        return self._request("POST", "/reset")
    def health(self) -> dict:
        """Health check"""
        return self._request("GET", "/health")

# ==================== MCP Bridge ====================
class MCPStdioBridge:
    """Manages connection to MCP server via stdio (subprocess)"""
    
    def __init__(self, command: str = "memory-mcp-server", data_dir: str = "/bridge/data/knowledge-graphi.jsonl"):
        self.command = command
        self.data_dir = data_dir
        self.process = None
        self.lock = asyncio.Lock()
        self.initialized = False
        self.request_id = 0
    
    async def start(self):
        """Start the MCP server subprocess"""
        try:
            # Start with --path flag for memory-mcp-server
            self.process = await asyncio.create_subprocess_exec(
                self.command,
                "--path", self.data_dir,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            logger.info(f"MCP server started (PID: {self.process.pid})")
            logger.info(f"Data directory: {self.data_dir}")
            
            await asyncio.sleep(0.5)
            await self._initialize_mcp()
            
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            raise
    
    async def _initialize_mcp(self):
        """Initialize MCP connection"""
        try:
            init_request = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "mcp-bridge", "version": "1.0.0"}
                },
                "id": 1
            }
            
            json_line = json.dumps(init_request) + "\n"
            self.process.stdin.write(json_line.encode())
            await self.process.stdin.drain()
            
            # Read lines until we get a valid JSON-RPC response
            # (skip log lines that start with timestamps or don't contain jsonrpc)
            max_attempts = 5
            for attempt in range(max_attempts):
                response_line = await asyncio.wait_for(
                    self.process.stdout.readline(), timeout=10.0
                )
                
                if not response_line:
                    raise RuntimeError("No initialization response from MCP server")
                
                response_text = response_line.decode().strip()
                
                # Skip empty lines or log lines
                if not response_text or not response_text.startswith('{'):
                    logger.debug(f"Skipping non-JSON line: {response_text[:100]}")
                    continue
                
                try:
                    response = json.loads(response_text)
                    
                    # Check if this is a JSON-RPC response (not a notification)
                    if "jsonrpc" in response and "id" in response:
                        if "error" in response:
                            raise RuntimeError(f"MCP initialization failed: {response['error']}")
                        
                        logger.info("MCP server initialized successfully")
                        logger.info(f"Server info: {response.get('result', {}).get('serverInfo', {})}")
                        self.initialized = True
                        return
                    else:
                        # This is a notification or other message, keep reading
                        logger.debug(f"Received non-response message: {response_text[:100]}")
                        continue
                        
                except json.JSONDecodeError:
                    logger.debug(f"Skipping invalid JSON: {response_text[:100]}")
                    continue
            
            raise RuntimeError("Failed to get valid initialization response after multiple attempts")
            
        except Exception as e:
            logger.error(f"MCP initialization failed: {e}")
            raise
    
    async def send(self, method: str, params: dict = None) -> dict:
        """Send JSON-RPC request to MCP server"""
        if not self.process or self.process.returncode is not None:
            raise RuntimeError("MCP process is not running")
        
        if not self.initialized:
            raise RuntimeError("MCP server not initialized")
        
        async with self.lock:
            try:
                self.request_id += 1
                request = {
                    "jsonrpc": "2.0",
                    "method": method,
                    "params": params or {},
                    "id": self.request_id
                }
                
                json_line = json.dumps(request) + "\n"
                self.process.stdin.write(json_line.encode())
                await self.process.stdin.drain()
                
                # Read lines until we get a valid JSON-RPC response
                max_attempts = 10
                for attempt in range(max_attempts):
                    response_line = await asyncio.wait_for(
                        self.process.stdout.readline(), timeout=30.0
                    )
                    
                    if not response_line:
                        raise RuntimeError("No response from MCP server")
                    
                    response_text = response_line.decode().strip()
                    
                    # Skip empty lines or non-JSON lines
                    if not response_text or not response_text.startswith('{'):
                        continue
                    
                    try:
                        response = json.loads(response_text)
                        
                        # Check if this is the response to our request
                        if "jsonrpc" in response and response.get("id") == self.request_id:
                            if "error" in response:
                                error = response["error"]
                                raise RuntimeError(f"MCP error: {error.get('message', str(error))}")
                            
                            return response.get("result", {})
                        else:
                            # This is a notification or different response, keep reading
                            continue
                            
                    except json.JSONDecodeError:
                        # Skip invalid JSON lines
                        continue
                
                raise RuntimeError("Failed to get valid response after multiple attempts")
                
            except asyncio.TimeoutError:
                logger.error(f"Timeout waiting for response to: {method}")
                raise RuntimeError(f"MCP server timeout for method: {method}")
            except Exception as e:
                logger.error(f"Error communicating with MCP: {e}")
                raise
    
    async def stop(self):
        """Stop the MCP server"""
        if self.process and self.process.returncode is None:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5)
                logger.info("MCP server stopped gracefully")
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()

# ==================== FastAPI App ====================
app = FastAPI(title="MCP Bridge Server")

# Enable CORS for external clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "ngrok-skip-browser-warning"],
)

# Middleware to add ngrok bypass headers to all responses
@app.middleware("http")
async def add_ngrok_headers(request: Request, call_next):
    """Add ngrok bypass headers to prevent warning page"""
    response = await call_next(request)
    response.headers["ngrok-skip-browser-warning"] = "true"
    response.headers["User-Agent"] = "MCP-Bridge/1.0"
    return response

# Initialize bridge with data directory
mcp = MCPStdioBridge(command="memory-mcp-server", data_dir="/bridge/data/knowledge_graph.jsonl")

@app.on_event("startup")
async def startup_event():
    """Start MCP server on app startup"""
    await mcp.start()
    ngrok_url = get_ngrok_url()
    if ngrok_url:
        logger.info(f"Bridge accessible at: {ngrok_url}")
        logger.info(f"External LLM clients should use: {ngrok_url}")

@app.on_event("shutdown")
async def shutdown_event():
    """Stop MCP server on app shutdown"""
    await mcp.stop()

# ==================== Utility ====================
@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}

@app.get("/status")
async def status():
    """Check server status"""
    return {
        "status": "running",
        "mcp_mode": "stdio",
        "data_dir": mcp.data_dir,
        "initialized": mcp.initialized
    }

@app.post("/reset")
async def reset():
    """Reset the knowledge graph"""
    payload = {"type": "reset"}
    result = await mcp.send(payload)
    return result

@app.get("/tools")
async def list_tools():
    """List all available MCP tools"""
    try:
        result = await mcp.send("tools/list", {})
        return result
    except Exception as e:
        logger.error(f"List tools failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/graph")
async def read_graph():
    """Read entire knowledge graph"""
    try:
        result = await mcp.send("tools/call", {
            "name": "read_graph",
            "arguments": {}
        })
        return result
    except Exception as e:
        logger.error(f"Read graph failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/entities")
async def create_entities(request: Request):
    """Create entities in the knowledge graph"""
    try:
        data = await request.json()
        entities = data.get("entities")
        if not entities:
            raise HTTPException(status_code=400, detail="Missing 'entities' field")
        
        result = await mcp.send("tools/call", {
            "name": "create_entities",
            "arguments": {"entities": entities}
        })
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create entities failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/entities")
async def delete_entities(request: Request):
    """Delete entities from the knowledge graph"""
    try:
        data = await request.json()
        entity_names = data.get("entityNames")
        if not entity_names:
            raise HTTPException(status_code=400, detail="Missing 'entityNames' field")
        
        result = await mcp.send("tools/call", {
            "name": "delete_entities",
            "arguments": {"entityNames": entity_names}
        })
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete entities failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
@app.post("/relations")
async def create_relations(request: Request):
    """Create relations between entities"""
    try:
        data = await request.json()
        relations = data.get("relations")
        if not relations:
            raise HTTPException(status_code=400, detail="Missing 'relations' field")
        
        result = await mcp.send("tools/call", {
            "name": "create_relations",
            "arguments": {"relations": relations}
        })
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create relations failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/relations")
async def delete_relations(request: Request):
    """Delete relations between entities"""
    try:
        data = await request.json()
        relations = data.get("relations")
        if not relations:
            raise HTTPException(status_code=400, detail="Missing 'relations' field")
        
        result = await mcp.send("tools/call", {
            "name": "delete_relations",
            "arguments": {"relations": relations}
        })
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete relations failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/observations")
async def add_observations(request: Request):
    """Add observations to entities"""
    try:
        data = await request.json()
        observations = data.get("observations")
        if not observations:
            raise HTTPException(status_code=400, detail="Missing 'observations' field")
        
        result = await mcp.send("tools/call", {
            "name": "add_observations",
            "arguments": {"observations": observations}
        })
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Add observations failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/observations")
async def delete_observations(request: Request):
    """Delete observations from entities"""
    try:
        data = await request.json()
        deletions = data.get("deletions")
        if not deletions:
            raise HTTPException(status_code=400, detail="Missing 'deletions' field")
        
        result = await mcp.send("tools/call", {
            "name": "delete_observations",
            "arguments": {"deletions": deletions}
        })
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete observations failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/nodes/search")
async def search_nodes(request: Request):
    """Search for nodes by query"""
    try:
        data = await request.json()
        query = data.get("query")
        if not query:
            raise HTTPException(status_code=400, detail="Missing 'query' field")
        
        result = await mcp.send("tools/call", {
            "name": "search_nodes",
            "arguments": {"query": query}
        })
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search nodes failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/nodes/open")
async def open_nodes(request: Request):
    """Open specific nodes by name"""
    try:
        data = await request.json()
        names = data.get("names")
        if not names:
            raise HTTPException(status_code=400, detail="Missing 'names' field")
        
        result = await mcp.send("tools/call", {
            "name": "open_nodes",
            "arguments": {"names": names}
        })
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Open nodes failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

tools = [
{
  "type": "function",
  "function": {
    "name": "create_entities",
    "description": "Create multiple new entities in the knowledge graph. Ignores entities with existing names.",
    "parameters": {
      "type": "object",
      "properties": {
        "entities": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "name": { "type": "string" },
              "entityType": { "type": "string" },
              "observations": {
                "type": "array",
                "items": { "type": "string" }
              }
            },
            "required": ["name", "entityType"]
          }
        }
      },
      "required": ["entities"]
    }
  }
},
{
  "type": "function",
  "function": {
    "name": "create_relations",
    "description": "Create multiple new relations between entities. Skips duplicate relations.",
    "parameters": {
      "type": "object",
      "properties": {
        "relations": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "from": { "type": "string" },
              "to": { "type": "string" },
              "relationType": { "type": "string" }
            },
            "required": ["from", "to", "relationType"]
          }
        }
      },
      "required": ["relations"]
    }
  }
},
{
  "type": "function",
  "function": {
    "name": "add_observations",
    "description": "Add new observations to existing entities. Fails if entity doesn't exist.",
    "parameters": {
      "type": "object",
      "properties": {
        "observations": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "entityName": { "type": "string" },
              "contents": {
                "type": "array",
                "items": { "type": "string" }
              }
            },
            "required": ["entityName", "contents"]
          }
        }
      },
      "required": ["observations"]
    }
  }
},
{
  "type": "function",
  "function": {
    "name": "delete_entities",
    "description": "Remove entities and their relations. Silent if entity doesn't exist.",
    "parameters": {
      "type": "object",
      "properties": {
        "entityNames": {
          "type": "array",
          "items": { "type": "string" }
        }
      },
      "required": ["entityNames"]
    }
  }
},
{
  "type": "function",
  "function": {
    "name": "delete_observations",
    "description": "Remove specific observations from entities. Silent if observation doesn't exist.",
    "parameters": {
      "type": "object",
      "properties": {
        "deletions": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "entityName": { "type": "string" },
              "observations": {
                "type": "array",
                "items": { "type": "string" }
              }
            },
            "required": ["entityName", "observations"]
          }
        }
      },
      "required": ["deletions"]
    }
  }
},
{
  "type": "function",
  "function": {
    "name": "delete_relations",
    "description": "Remove specific relations from the graph. Silent if relation doesn't exist.",
    "parameters": {
      "type": "object",
      "properties": {
        "relations": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "from": { "type": "string" },
              "to": { "type": "string" },
              "relationType": { "type": "string" }
            },
            "required": ["from", "to", "relationType"]
          }
        }
      },
      "required": ["relations"]
    }
  }
},
{
  "type": "function",
  "function": {
    "name": "read_graph",
    "description": "Read the entire knowledge graph, including all entities and relations.",
    "parameters": {
      "type": "object",
      "properties": {}
    }
  }
},
{
  "type": "function",
  "function": {
    "name": "search_nodes",
    "description": "Search for nodes based on query across names, types, and observation content.",
    "parameters": {
      "type": "object",
      "properties": {
        "query": { "type": "string" }
      },
      "required": ["query"]
    }
  }
},
{
  "type": "function",
  "function": {
    "name": "open_nodes",
    "description": "Retrieve specific nodes by name. Silently skips non-existent nodes.",
    "parameters": {
      "type": "object",
      "properties": {
        "names": {
          "type": "array",
          "items": { "type": "string" }
        }
      },
      "required": ["names"]
    }
  }
}
]

# ==================== Run ====================
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
