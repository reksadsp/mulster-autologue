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
