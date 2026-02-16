# Tool Hub API Reference - Phase 0 MVP

## Base URL
```
http://localhost:8000
```

## Authentication
All endpoints (except health checks) require JWT authentication:
```
Authorization: Bearer <jwt_token>
```

### Token Generation
Tokens are created using `create_access_token()` from `app.auth.jwt`:
```python
from app.auth import create_access_token

token = create_access_token(
    user_id="user-123",
    email="user@example.com",
    role="user"  # or "admin"
)
```

Token payload includes:
- `sub` - User ID
- `email` - User email
- `role` - User role
- `exp` - Expiration timestamp
- `iat` - Issued at timestamp

---

## Workflows API

### List Workflows
```http
GET /api/workflows?limit=100&offset=0
Authorization: Bearer <token>
```

**Query Parameters:**
- `limit` (int, optional) - Max results (1-1000, default: 100)
- `offset` (int, optional) - Skip count (default: 0)

**Response:** `200 OK`
```json
{
  "workflows": [
    {
      "id": "wf-123",
      "name": "My Workflow",
      "description": "Description here",
      "nodes": [...],
      "edges": [...],
      "created_at": "2024-01-01T00:00:00",
      "updated_at": "2024-01-01T00:00:00"
    }
  ],
  "total": 42,
  "limit": 100,
  "offset": 0
}
```

---

### Create Workflow
```http
POST /api/workflows
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "My Workflow",
  "description": "Optional description",
  "nodes": [
    {
      "id": "node-1",
      "type": "agent",
      "data": {
        "model": "claude-3-5-sonnet-20241022",
        "prompt": "System prompt here"
      },
      "position": {"x": 100, "y": 100}
    }
  ],
  "edges": [
    {
      "id": "edge-1",
      "source": "node-1",
      "target": "node-2"
    }
  ]
}
```

**Response:** `201 Created`
```json
{
  "id": "wf-456",
  "name": "My Workflow",
  ...
}
```

---

### Get Workflow
```http
GET /api/workflows/:id
Authorization: Bearer <token>
```

**Response:** `200 OK` - Same structure as workflow list item

**Errors:**
- `404` - Workflow not found

---

### Update Workflow
```http
PUT /api/workflows/:id
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:** (all fields optional)
```json
{
  "name": "Updated Name",
  "description": "Updated description",
  "nodes": [...],
  "edges": [...]
}
```

**Response:** `200 OK` - Updated workflow

**Errors:**
- `404` - Workflow not found

---

### Delete Workflow
```http
DELETE /api/workflows/:id
Authorization: Bearer <token>
```

**Response:** `204 No Content`

**Errors:**
- `404` - Workflow not found

---

### Run Workflow
```http
POST /api/workflows/:id/run
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "input": "Input string for workflow",
  "mode": "full"  // "full", "mock", or "debug"
}
```

**Response:** `200 OK`
```json
{
  "execution_id": "exec-789",
  "status": "pending",
  "workflow_id": "wf-123"
}
```

**Errors:**
- `404` - Workflow not found
- `400` - Invalid workflow or execution request

---

### Validate Workflow
```http
POST /api/workflows/:id/validate
Authorization: Bearer <token>
```

**Response:** `200 OK`
```json
{
  "valid": false,
  "errors": [
    {
      "message": "Agent node 'node-1' missing model"
    },
    {
      "message": "Workflow contains a cycle"
    }
  ]
}
```

**Errors:**
- `404` - Workflow not found

---

## Executions API

### List Executions
```http
GET /api/executions?workflow_id=wf-123&status=running&limit=100&offset=0
Authorization: Bearer <token>
```

**Query Parameters:**
- `workflow_id` (string, optional) - Filter by workflow
- `status` (string, optional) - Filter by status
- `limit` (int, optional) - Max results (1-1000, default: 100)
- `offset` (int, optional) - Skip count (default: 0)

**Response:** `200 OK`
```json
{
  "executions": [
    {
      "id": "exec-789",
      "workflow_id": "wf-123",
      "status": "running",
      "mode": "full",
      "trigger_type": "manual",
      "started_at": "2024-01-01T00:00:00",
      "completed_at": null,
      "duration_ms": null
    }
  ],
  "total": 15,
  "limit": 100,
  "offset": 0
}
```

---

### Get Execution
```http
GET /api/executions/:id
Authorization: Bearer <token>
```

**Response:** `200 OK`
```json
{
  "id": "exec-789",
  "workflow_id": "wf-123",
  "status": "completed",
  "mode": "full",
  "trigger_type": "manual",
  "trigger_id": null,
  "input": "Input string",
  "output": "Final output",
  "error": null,
  "node_logs": [
    {
      "node_id": "node-1",
      "status": "completed",
      "input": "...",
      "output": "...",
      "error": null,
      "started_at": "2024-01-01T00:00:00",
      "completed_at": "2024-01-01T00:00:05",
      "duration_ms": 5000,
      "retry_count": 0
    }
  ],
  "started_at": "2024-01-01T00:00:00",
  "completed_at": "2024-01-01T00:01:00",
  "duration_ms": 60000
}
```

**Errors:**
- `404` - Execution not found

---

### Stop Execution
```http
POST /api/executions/:id/stop
Authorization: Bearer <token>
```

**Response:** `200 OK`
```json
{
  "message": "Execution stopped"
}
```

**Errors:**
- `404` - Execution not found
- `400` - Execution not in stoppable state

---

### Resume Execution
```http
POST /api/executions/:id/resume
Authorization: Bearer <token>
```

**Response:** `200 OK`
```json
{
  "message": "Execution resumed"
}
```

**Errors:**
- `404` - Execution not found
- `400` - Execution not in resumable state

---

### Get Execution Logs
```http
GET /api/executions/:id/logs?node_id=node-1
Authorization: Bearer <token>
```

**Query Parameters:**
- `node_id` (string, optional) - Filter by node

**Response:** `200 OK`
```json
[
  {
    "node_id": "node-1",
    "status": "completed",
    "input": "...",
    "output": "...",
    "error": null,
    "started_at": "2024-01-01T00:00:00",
    "completed_at": "2024-01-01T00:00:05",
    "duration_ms": 5000,
    "retry_count": 0
  }
]
```

**Errors:**
- `404` - Execution not found

---

## MCP Servers API

### List Servers
```http
GET /api/mcp/servers
Authorization: Bearer <token>
```

**Response:** `200 OK`
```json
[
  {
    "id": "srv-123",
    "name": "filesystem",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
    "description": "Filesystem MCP server",
    "status": "connected",
    "connected_at": "2024-01-01T00:00:00"
  }
]
```

---

### Connect Server
```http
POST /api/mcp/servers
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "filesystem",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
  "env": {
    "CUSTOM_VAR": "value"
  },
  "description": "Optional description"
}
```

**Response:** `201 Created`
```json
{
  "id": "srv-456",
  "name": "filesystem",
  ...
}
```

**Errors:**
- `400` - Invalid configuration or connection failed

---

### Disconnect Server
```http
DELETE /api/mcp/servers/:id
Authorization: Bearer <token>
```

**Response:** `204 No Content`

**Errors:**
- `404` - Server not found

---

### List Server Tools
```http
GET /api/mcp/servers/:id/tools
Authorization: Bearer <token>
```

**Response:** `200 OK`
```json
[
  {
    "name": "read_file",
    "description": "Read contents of a file",
    "input_schema": {
      "type": "object",
      "properties": {
        "path": {"type": "string"}
      },
      "required": ["path"]
    },
    "server_id": "srv-123"
  }
]
```

**Errors:**
- `404` - Server not found

---

### Check Server Health
```http
GET /api/mcp/servers/:id/health
Authorization: Bearer <token>
```

**Response:** `200 OK`
```json
{
  "server_id": "srv-123",
  "status": "healthy",
  "message": null,
  "latency_ms": 15
}
```

**Errors:**
- `404` - Server not found

---

## Secrets API

### List Secrets
```http
GET /api/secrets
Authorization: Bearer <token>
```

**Response:** `200 OK` (values excluded for security)
```json
[
  {
    "name": "OPENAI_API_KEY",
    "description": "OpenAI API key for workflows",
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
]
```

---

### Create Secret
```http
POST /api/secrets
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "OPENAI_API_KEY",
  "value": "sk-...",
  "description": "OpenAI API key for workflows"
}
```

**Response:** `201 Created` (value excluded)
```json
{
  "name": "OPENAI_API_KEY",
  "description": "OpenAI API key for workflows",
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

**Errors:**
- `400` - Secret already exists

---

### Update Secret
```http
PUT /api/secrets/:name
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "value": "new-secret-value",
  "description": "Updated description (optional)"
}
```

**Response:** `200 OK` (value excluded)

**Errors:**
- `404` - Secret not found

---

### Delete Secret
```http
DELETE /api/secrets/:name
Authorization: Bearer <token>
```

**Response:** `204 No Content`

**Errors:**
- `404` - Secret not found

---

## Error Responses

All errors follow this format:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message"
  }
}
```

### Common Error Codes

| Code | Status | Description |
|------|--------|-------------|
| `INVALID_TOKEN` | 401 | JWT token is invalid or expired |
| `WORKFLOW_NOT_FOUND` | 404 | Workflow does not exist |
| `EXECUTION_NOT_FOUND` | 404 | Execution does not exist |
| `SERVER_NOT_FOUND` | 404 | MCP server does not exist |
| `SECRET_NOT_FOUND` | 404 | Secret does not exist |
| `NOT_IMPLEMENTED` | 501 | Feature not yet implemented |
| `HTTP_XXX` | XXX | Generic HTTP error |

---

## Health Check Endpoints

### Liveness Probe
```http
GET /health/live
```

**Response:** `200 OK`
```json
{
  "status": "alive"
}
```

---

### Readiness Probe
```http
GET /health/ready
```

**Response:** `200 OK`
```json
{
  "status": "ready",
  "checks": {
    "database": true,
    "scheduler": true
  }
}
```

---

### MCP Health Check
```http
GET /health/mcp/:server_id
```

**Response:** `200 OK`
```json
{
  "server_id": "srv-123",
  "status": "unknown",
  "message": "MCP health check not yet implemented"
}
```

---

## Interactive Documentation

When the server is running:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json
