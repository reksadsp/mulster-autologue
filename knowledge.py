from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import os
import time
import uvicorn
import logging
import requests
from typing import Optional, List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = FastAPI(title="MCP Bridge Server")

# Enable CORS for external clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MCPBridge:
    """Manages connection to MCP server running in Docker"""
    def __init__(self, mcp_url: str = "http://localhost:8001"):
        self.mcp_url = mcp_url.rstrip("/")
        self.session = None
    
    async def send(self, command: dict) -> dict:
        """Forward command to MCP server"""
        try:
            # For now, we'll use blocking requests since MCP server expects it
            # If you need async, implement a proper HTTP client
            response = requests.post(
                f"{self.mcp_url}/command",
                json=command,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error communicating with MCP: {e}")
            raise HTTPException(status_code=500, detail=str(e))

# Initialize bridge (connects to MCP in Docker)
mcp = MCPBridge(mcp_url="http://mcp-memory:8001")  # Docker service name

# ==================== Entities ====================
@app.post("/entities")
async def create_entities(request: Request):
    """Create entities in the knowledge graph"""
    data = await request.json()
    entities = data.get("entities")
    if not entities:
        raise HTTPException(status_code=400, detail="Missing 'entities' field")
    
    payload = {"type": "create_entities", "entities": entities}
    result = await mcp.send(payload)
    return result

@app.delete("/entities")
async def delete_entities(request: Request):
    """Delete entities from the knowledge graph"""
    data = await request.json()
    entity_names = data.get("entityNames")
    if not entity_names:
        raise HTTPException(status_code=400, detail="Missing 'entityNames' field")
    
    payload = {"type": "delete_entities", "entityNames": entity_names}
    result = await mcp.send(payload)
    return result

# ==================== Relations ====================
@app.post("/relations")
async def create_relations(request: Request):
    """Create relations between entities"""
    data = await request.json()
    relations = data.get("relations")
    if not relations:
        raise HTTPException(status_code=400, detail="Missing 'relations' field")
    
    payload = {"type": "create_relations", "relations": relations}
    result = await mcp.send(payload)
    return result

@app.delete("/relations")
async def delete_relations(request: Request):
    """Delete relations between entities"""
    data = await request.json()
    relations = data.get("relations")
    if not relations:
        raise HTTPException(status_code=400, detail="Missing 'relations' field")
    
    payload = {"type": "delete_relations", "relations": relations}
    result = await mcp.send(payload)
    return result

# ==================== Observations ====================
@app.post("/observations")
async def add_observations(request: Request):
    """Add observations to entities"""
    data = await request.json()
    observations = data.get("observations")
    if not observations:
        raise HTTPException(status_code=400, detail="Missing 'observations' field")
    
    payload = {"type": "add_observations", "observations": observations}
    result = await mcp.send(payload)
    return result

@app.delete("/observations")
async def delete_observations(request: Request):
    """Delete observations from entities"""
    data = await request.json()
    deletions = data.get("deletions")
    if not deletions:
        raise HTTPException(status_code=400, detail="Missing 'deletions' field")
    
    payload = {"type": "delete_observations", "deletions": deletions}
    result = await mcp.send(payload)
    return result

# ==================== Graph ====================
@app.get("/graph")
async def read_graph():
    """Read entire knowledge graph"""
    payload = {"type": "read_graph"}
    result = await mcp.send(payload)
    return result

# ==================== Nodes ====================
@app.post("/nodes/search")
async def search_nodes(request: Request):
    """Search for nodes by query"""
    data = await request.json()
    query = data.get("query")
    if not query:
        raise HTTPException(status_code=400, detail="Missing 'query' field")
    
    payload = {"type": "search_nodes", "query": query}
    result = await mcp.send(payload)
    return result

@app.post("/nodes/open")
async def open_nodes(request: Request):
    """Open/retrieve specific nodes by name"""
    data = await request.json()
    names = data.get("names")
    if not names:
        raise HTTPException(status_code=400, detail="Missing 'names' field")
    
    payload = {"type": "open_nodes", "names": names}
    result = await mcp.send(payload)
    return result

# ==================== Utility ====================
@app.get("/status")
async def status():
    """Check server status"""
    return {"status": "running", "mcp_url": mcp.mcp_url}

@app.post("/reset")
async def reset():
    """Reset the knowledge graph"""
    payload = {"type": "reset"}
    result = await mcp.send(payload)
    return result

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}

# ==================== Client Class ====================
class MCPClient:

    def __init__(self, bridge_url: str):
        self.bridge_url = bridge_url.rstrip("/")
        self.session = requests.Session()
        self.timeout = 30
    
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

# ==================== Run ====================
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
