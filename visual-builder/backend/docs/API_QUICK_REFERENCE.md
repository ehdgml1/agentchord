# API Quick Reference

Fast lookup guide for Tool Hub API endpoints, request/response formats, and error codes.

## Base Information

**Base URL**: `http://localhost:8000/api` (development) or `https://api.example.com/api` (production)

**Version**: 1.0.0

**Authentication**: All endpoints except health checks require `Authorization: Bearer <jwt_token>` header

**Content Type**: `application/json`

---

## Quick Endpoint Index

### Workflows
- [GET /workflows](#get-workflows) - List all workflows
- [POST /workflows](#post-workflows) - Create new workflow
- [GET /workflows/{id}](#get-workflowsid) - Get workflow details
- [PUT /workflows/{id}](#put-workflowsid) - Update workflow
- [DELETE /workflows/{id}](#delete-workflowsid) - Delete workflow
- [POST /workflows/{id}/run](#post-workflowsidrun) - Execute workflow
- [POST /workflows/{id}/validate](#post-workflowsidvalidate) - Validate workflow

### Executions
- [GET /executions](#get-executions) - List executions
- [GET /executions/{id}](#get-executionsid) - Get execution details
- [GET /executions/{id}/logs](#get-executionsidlogs) - Get execution logs
- [POST /executions/{id}/stop](#post-executionsidstop) - Stop execution
- [POST /executions/{id}/resume](#post-executionsidresume) - Resume execution

### Schedules
- [GET /schedules](#get-schedules) - List schedules
- [POST /schedules](#post-schedules) - Create schedule
- [GET /schedules/{id}](#get-schedulesid) - Get schedule
- [PUT /schedules/{id}](#put-schedulesid) - Update schedule
- [DELETE /schedules/{id}](#delete-schedulesid) - Delete schedule
- [POST /schedules/{id}/run](#post-schedulesidrun) - Run now

### MCP Servers
- [GET /mcp/servers](#get-mcpservers) - List servers
- [POST /mcp/servers](#post-mcpservers) - Connect server
- [DELETE /mcp/servers/{id}](#delete-mcpserversid) - Disconnect server
- [GET /mcp/servers/{id}/tools](#get-mcpserversidtools) - List tools
- [GET /mcp/servers/{id}/health](#get-mcpserversidhealth) - Check health

### Secrets
- [GET /secrets](#get-secrets) - List secrets
- [POST /secrets](#post-secrets) - Create secret
- [PUT /secrets/{name}](#put-secretsname) - Update secret
- [DELETE /secrets/{name}](#delete-secretsname) - Delete secret

### Versions
- [GET /versions](#get-versions) - List versions
- [POST /versions](#post-versions) - Create version
- [GET /versions/{id}](#get-versionsid) - Get version
- [GET /workflows/{id}/versions](#get-workflowsidversions) - List workflow versions

### Health
- [GET /health/live](#get-healthlive) - Liveness probe
- [GET /health/ready](#get-healthready) - Readiness probe
- [GET /health/mcp/{server_id}](#get-healthmcpserver_id) - MCP health

---

## Workflows

### GET /workflows

List all workflows owned by current user.

**Query Parameters**:
- `limit` (int, 1-1000, default: 100) - Max results
- `offset` (int, default: 0) - Skip count
- `search` (string, optional) - Search by name/description

**Response** (200 OK):
```json
{
  "workflows": [
    {
      "id": "wf-123",
      "name": "My Workflow",
      "description": "Brief description",
      "nodes": [],
      "edges": [],
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z",
      "version": 1
    }
  ],
  "total": 42,
  "limit": 100,
  "offset": 0
}
```

**cURL Example**:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/workflows?limit=10&offset=0"
```

---

### POST /workflows

Create a new workflow.

**Request Body**:
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
        "prompt": "You are a helpful assistant..."
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

**Response** (201 Created):
```json
{
  "id": "wf-456",
  "name": "My Workflow",
  "description": "Optional description",
  "nodes": [...],
  "edges": [...],
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "version": 1
}
```

**cURL Example**:
```bash
curl -X POST http://localhost:8000/api/workflows \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Workflow",
    "description": "Test workflow",
    "nodes": [],
    "edges": []
  }'
```

---

### GET /workflows/{id}

Get workflow by ID.

**Path Parameters**:
- `id` (string, required) - Workflow ID

**Response** (200 OK): Workflow object (same as POST response)

**Errors**:
- `404 WORKFLOW_NOT_FOUND` - Workflow doesn't exist

**cURL Example**:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/workflows/wf-123
```

---

### PUT /workflows/{id}

Update workflow.

**Path Parameters**:
- `id` (string, required) - Workflow ID

**Request Body** (all fields optional):
```json
{
  "name": "Updated Name",
  "description": "Updated description",
  "nodes": [],
  "edges": []
}
```

**Response** (200 OK): Updated workflow object

**Errors**:
- `404 WORKFLOW_NOT_FOUND` - Workflow doesn't exist

**cURL Example**:
```bash
curl -X PUT http://localhost:8000/api/workflows/wf-123 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Name"}'
```

---

### DELETE /workflows/{id}

Delete workflow.

**Path Parameters**:
- `id` (string, required) - Workflow ID

**Response** (204 No Content)

**Errors**:
- `404 WORKFLOW_NOT_FOUND` - Workflow doesn't exist

**cURL Example**:
```bash
curl -X DELETE http://localhost:8000/api/workflows/wf-123 \
  -H "Authorization: Bearer $TOKEN"
```

---

### POST /workflows/{id}/run

Execute workflow.

**Path Parameters**:
- `id` (string, required) - Workflow ID

**Request Body**:
```json
{
  "input": "Input string or JSON",
  "mode": "full"
}
```

**Mode Options**:
- `full` - Execute with real MCP servers
- `mock` - Execute with simulated responses
- `debug` - Execute with step-through debugging

**Response** (200 OK):
```json
{
  "execution_id": "exec-789",
  "workflow_id": "wf-123",
  "status": "pending",
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Errors**:
- `404 WORKFLOW_NOT_FOUND` - Workflow doesn't exist
- `400 INVALID_WORKFLOW` - Workflow validation failed

**cURL Example**:
```bash
curl -X POST http://localhost:8000/api/workflows/wf-123/run \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Analyze this data",
    "mode": "full"
  }'
```

---

### POST /workflows/{id}/validate

Validate workflow structure without executing.

**Path Parameters**:
- `id` (string, required) - Workflow ID

**Response** (200 OK):
```json
{
  "valid": true,
  "errors": []
}
```

Or if invalid:
```json
{
  "valid": false,
  "errors": [
    {
      "node_id": "node-1",
      "message": "Agent node missing required field: model"
    }
  ]
}
```

**Errors**:
- `404 WORKFLOW_NOT_FOUND` - Workflow doesn't exist

**cURL Example**:
```bash
curl -X POST http://localhost:8000/api/workflows/wf-123/validate \
  -H "Authorization: Bearer $TOKEN"
```

---

## Executions

### GET /executions

List all executions with optional filtering.

**Query Parameters**:
- `workflow_id` (string, optional) - Filter by workflow
- `status` (string, optional) - Filter by status (pending, running, completed, failed, stopped)
- `limit` (int, 1-1000, default: 100) - Max results
- `offset` (int, default: 0) - Skip count

**Response** (200 OK):
```json
{
  "executions": [
    {
      "id": "exec-789",
      "workflow_id": "wf-123",
      "status": "completed",
      "mode": "full",
      "trigger_type": "manual",
      "input": "Input data",
      "output": "Output data",
      "error": null,
      "started_at": "2024-01-15T10:30:00Z",
      "completed_at": "2024-01-15T10:31:00Z",
      "duration_ms": 60000
    }
  ],
  "total": 42,
  "limit": 100,
  "offset": 0
}
```

**cURL Example**:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/executions?workflow_id=wf-123&status=completed"
```

---

### GET /executions/{id}

Get execution details with full logs.

**Path Parameters**:
- `id` (string, required) - Execution ID

**Response** (200 OK):
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
      "input": "node input",
      "output": "node output",
      "error": null,
      "started_at": "2024-01-15T10:30:00Z",
      "completed_at": "2024-01-15T10:30:05Z",
      "duration_ms": 5000,
      "retry_count": 0
    }
  ],
  "started_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:31:00Z",
  "duration_ms": 60000
}
```

**Errors**:
- `404 EXECUTION_NOT_FOUND` - Execution doesn't exist

**cURL Example**:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/executions/exec-789
```

---

### GET /executions/{id}/logs

Get execution logs (node-by-node details).

**Path Parameters**:
- `id` (string, required) - Execution ID

**Query Parameters**:
- `node_id` (string, optional) - Filter by node

**Response** (200 OK):
```json
[
  {
    "node_id": "node-1",
    "status": "completed",
    "input": "...",
    "output": "...",
    "error": null,
    "started_at": "2024-01-15T10:30:00Z",
    "completed_at": "2024-01-15T10:30:05Z",
    "duration_ms": 5000,
    "retry_count": 0
  }
]
```

**cURL Example**:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/executions/exec-789/logs?node_id=node-1"
```

---

### POST /executions/{id}/stop

Stop a running execution.

**Path Parameters**:
- `id` (string, required) - Execution ID

**Response** (200 OK):
```json
{
  "message": "Execution stopped"
}
```

**Errors**:
- `404 EXECUTION_NOT_FOUND` - Execution doesn't exist
- `400 EXECUTION_NOT_STOPPABLE` - Execution not in running state

**cURL Example**:
```bash
curl -X POST http://localhost:8000/api/executions/exec-789/stop \
  -H "Authorization: Bearer $TOKEN"
```

---

### POST /executions/{id}/resume

Resume a paused execution (debug mode breakpoint).

**Path Parameters**:
- `id` (string, required) - Execution ID

**Request Body** (optional):
```json
{
  "override_values": {
    "node-1": "new value"
  }
}
```

**Response** (200 OK):
```json
{
  "message": "Execution resumed"
}
```

**Errors**:
- `404 EXECUTION_NOT_FOUND` - Execution doesn't exist
- `400 EXECUTION_NOT_RESUMABLE` - Execution not in paused state

**cURL Example**:
```bash
curl -X POST http://localhost:8000/api/executions/exec-789/resume \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## Schedules

### GET /schedules

List all schedules.

**Query Parameters**:
- `workflow_id` (string, optional) - Filter by workflow
- `enabled` (bool, optional) - Filter by status
- `limit` (int, 1-1000, default: 100)
- `offset` (int, default: 0)

**Response** (200 OK):
```json
{
  "schedules": [
    {
      "id": "sched-1",
      "workflow_id": "wf-123",
      "name": "Daily Report",
      "cron_expression": "0 9 * * *",
      "enabled": true,
      "next_run_time": "2024-01-16T09:00:00Z",
      "last_run_time": "2024-01-15T09:00:00Z",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 5,
  "limit": 100,
  "offset": 0
}
```

**cURL Example**:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/schedules?workflow_id=wf-123"
```

---

### POST /schedules

Create a new schedule.

**Request Body**:
```json
{
  "workflow_id": "wf-123",
  "name": "Daily Report",
  "cron_expression": "0 9 * * *",
  "enabled": true,
  "input": {
    "report_type": "daily"
  }
}
```

**Cron Expression Examples**:
- `0 9 * * *` - Every day at 9 AM
- `0 */6 * * *` - Every 6 hours
- `0 0 * * 0` - Every Sunday at midnight
- `*/5 * * * *` - Every 5 minutes

**Response** (201 Created): Schedule object (same as GET response item)

**Errors**:
- `404 WORKFLOW_NOT_FOUND` - Workflow doesn't exist
- `400 INVALID_CRON` - Invalid cron expression

**cURL Example**:
```bash
curl -X POST http://localhost:8000/api/schedules \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "wf-123",
    "name": "Daily Report",
    "cron_expression": "0 9 * * *",
    "enabled": true
  }'
```

---

### GET /schedules/{id}

Get schedule by ID.

**Response** (200 OK): Schedule object

**Errors**:
- `404 SCHEDULE_NOT_FOUND` - Schedule doesn't exist

---

### PUT /schedules/{id}

Update schedule.

**Request Body** (all fields optional):
```json
{
  "name": "Updated Name",
  "cron_expression": "0 10 * * *",
  "enabled": false
}
```

**Response** (200 OK): Updated schedule object

---

### DELETE /schedules/{id}

Delete schedule.

**Response** (204 No Content)

---

### POST /schedules/{id}/run

Run schedule immediately (ignoring next run time).

**Response** (200 OK):
```json
{
  "execution_id": "exec-999",
  "message": "Schedule executed"
}
```

---

## MCP Servers

### GET /mcp/servers

List connected MCP servers.

**Response** (200 OK):
```json
[
  {
    "id": "srv-123",
    "name": "filesystem",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
    "status": "connected",
    "connected_at": "2024-01-15T10:30:00Z",
    "description": "Filesystem access server"
  }
]
```

**cURL Example**:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/mcp/servers
```

---

### POST /mcp/servers

Connect a new MCP server.

**Request Body**:
```json
{
  "name": "filesystem",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
  "env": {
    "CUSTOM_VAR": "value"
  },
  "description": "Filesystem MCP server"
}
```

**Response** (201 Created): Server object

**Errors**:
- `400 INVALID_CONFIGURATION` - Invalid server configuration
- `400 CONNECTION_FAILED` - Failed to connect to server

**cURL Example**:
```bash
curl -X POST http://localhost:8000/api/mcp/servers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "filesystem",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
  }'
```

---

### DELETE /mcp/servers/{id}

Disconnect MCP server.

**Response** (204 No Content)

**Errors**:
- `404 SERVER_NOT_FOUND` - Server doesn't exist

---

### GET /mcp/servers/{id}/tools

List tools available on MCP server.

**Response** (200 OK):
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
    }
  }
]
```

**Errors**:
- `404 SERVER_NOT_FOUND` - Server doesn't exist

---

### GET /mcp/servers/{id}/health

Check MCP server health.

**Response** (200 OK):
```json
{
  "server_id": "srv-123",
  "status": "healthy",
  "message": null,
  "latency_ms": 15
}
```

**Status Values**:
- `healthy` - Server is responding
- `degraded` - Server responding slowly
- `unhealthy` - Server not responding

---

## Secrets

### GET /secrets

List secret metadata (values excluded).

**Response** (200 OK):
```json
[
  {
    "name": "OPENAI_API_KEY",
    "description": "OpenAI API key",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
]
```

**Security Note**: Secret values are never returned in API responses. They are only accessible within workflow execution context.

**cURL Example**:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/secrets
```

---

### POST /secrets

Create a new secret.

**Request Body**:
```json
{
  "name": "OPENAI_API_KEY",
  "value": "sk-...",
  "description": "OpenAI API key for workflows"
}
```

**Response** (201 Created):
```json
{
  "name": "OPENAI_API_KEY",
  "description": "OpenAI API key for workflows",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

**Errors**:
- `400 SECRET_ALREADY_EXISTS` - Secret with this name already exists

---

### PUT /secrets/{name}

Update secret value.

**Path Parameters**:
- `name` (string, required) - Secret name

**Request Body**:
```json
{
  "value": "sk-new-value",
  "description": "Updated description"
}
```

**Response** (200 OK): Updated secret metadata

**Errors**:
- `404 SECRET_NOT_FOUND` - Secret doesn't exist

---

### DELETE /secrets/{name}

Delete secret.

**Path Parameters**:
- `name` (string, required) - Secret name

**Response** (204 No Content)

**Errors**:
- `404 SECRET_NOT_FOUND` - Secret doesn't exist

---

## Versions

### GET /versions

List all workflow versions.

**Query Parameters**:
- `workflow_id` (string, required) - Filter by workflow
- `limit` (int, default: 100)
- `offset` (int, default: 0)

**Response** (200 OK):
```json
{
  "versions": [
    {
      "id": "ver-1",
      "workflow_id": "wf-123",
      "version_number": 2,
      "description": "Fixed node ordering",
      "created_at": "2024-01-15T10:30:00Z",
      "created_by": "user@example.com",
      "nodes": [],
      "edges": []
    }
  ],
  "total": 5,
  "limit": 100,
  "offset": 0
}
```

---

### POST /versions

Create a new version (snapshot) of workflow.

**Request Body**:
```json
{
  "workflow_id": "wf-123",
  "description": "Fixed node ordering",
  "nodes": [],
  "edges": []
}
```

**Response** (201 Created): Version object

---

### GET /versions/{id}

Get specific version details.

**Response** (200 OK): Version object with full workflow structure

---

### GET /workflows/{id}/versions

List all versions of a specific workflow.

**Path Parameters**:
- `id` (string, required) - Workflow ID

**Response** (200 OK): List of version objects

---

## Health

### GET /health/live

Liveness probe - process is running.

**Authentication**: Not required

**Response** (200 OK):
```json
{
  "status": "alive"
}
```

**Use in Kubernetes**:
```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 10
```

---

### GET /health/ready

Readiness probe - service is ready for traffic.

**Authentication**: Not required

**Response** (200 OK):
```json
{
  "status": "ready",
  "checks": {
    "database": true,
    "scheduler": true
  }
}
```

**Use in Kubernetes**:
```yaml
readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

---

### GET /health/mcp/{server_id}

Check MCP server health.

**Authentication**: Required (Bearer token)

**Path Parameters**:
- `server_id` (string, required) - MCP server ID

**Response** (200 OK):
```json
{
  "server_id": "srv-123",
  "status": "healthy",
  "message": null,
  "latency_ms": 15
}
```

---

## Common Error Responses

All error responses follow this format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message"
  }
}
```

### Error Codes

| Code | Status | Description |
|------|--------|-------------|
| `INVALID_TOKEN` | 401 | JWT token is invalid or expired |
| `UNAUTHORIZED` | 403 | User doesn't have permission |
| `WORKFLOW_NOT_FOUND` | 404 | Workflow doesn't exist |
| `EXECUTION_NOT_FOUND` | 404 | Execution doesn't exist |
| `SCHEDULE_NOT_FOUND` | 404 | Schedule doesn't exist |
| `SERVER_NOT_FOUND` | 404 | MCP server doesn't exist |
| `SECRET_NOT_FOUND` | 404 | Secret doesn't exist |
| `VERSION_NOT_FOUND` | 404 | Version doesn't exist |
| `INVALID_WORKFLOW` | 400 | Workflow validation failed |
| `INVALID_CRON` | 400 | Invalid cron expression |
| `INVALID_REQUEST` | 400 | Invalid request body |
| `EXECUTION_NOT_STOPPABLE` | 400 | Execution not in stoppable state |
| `EXECUTION_NOT_RESUMABLE` | 400 | Execution not in resumable state |
| `SECRET_ALREADY_EXISTS` | 400 | Secret with this name exists |
| `INTERNAL_ERROR` | 500 | Unexpected server error |
| `NOT_IMPLEMENTED` | 501 | Feature not yet implemented |

---

## Rate Limiting

Default rate limits (per user, per minute):

| Category | Limit | Examples |
|----------|-------|----------|
| Workflow execution | 10/min | POST /workflows/{id}/run |
| Webhooks | 100/min | POST /webhook/{id} |
| List operations | 1000/min | GET /workflows, /executions |
| General API | 1000/min | All other endpoints |
| Health checks | unlimited | /health/* |

**Headers in Response**:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1705326600
```

When rate limit exceeded:
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Reset at 2024-01-15T11:30:00Z"
  }
}
```

---

## Pagination

All list endpoints support pagination with `limit` and `offset`:

**Query Parameters**:
- `limit` (int, 1-1000, default: 100)
- `offset` (int, default: 0)

**Response Format**:
```json
{
  "[resource]s": [...],
  "total": 42,
  "limit": 100,
  "offset": 0
}
```

**Example**: Get next 100 items
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/workflows?limit=100&offset=100"
```

---

## Authentication

### Get JWT Token

Generate token for your user (implementation varies by auth provider):

```bash
# Example with password grant
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user@example.com",
    "password": "password"
  }'

# Response
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Use Token

Add token to every request:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/workflows
```

### Token Expiration

Tokens expire after 1 hour by default. Request new token before expiration:

```bash
# Token expires when "exp" claim is reached
# Get new token by repeating login request
```

---

## Interactive Documentation

When server is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

---

## Common Use Cases

### List Recent Executions

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/executions?limit=10&offset=0" | jq '.executions | reverse'
```

### Run Workflow and Check Result

```bash
# 1. Run workflow
EXEC_ID=$(curl -X POST http://localhost:8000/api/workflows/wf-123/run \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input": "test"}' | jq -r '.execution_id')

# 2. Wait for completion
sleep 5

# 3. Get results
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/executions/$EXEC_ID"
```

### Create Workflow and Schedule It

```bash
# 1. Create workflow
WF_ID=$(curl -X POST http://localhost:8000/api/workflows \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Hourly Report",
    "nodes": [],
    "edges": []
  }' | jq -r '.id')

# 2. Schedule it
curl -X POST http://localhost:8000/api/schedules \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "'$WF_ID'",
    "name": "Every Hour",
    "cron_expression": "0 * * * *",
    "enabled": true
  }'
```

---

**Document Version**: 1.0
**Last Updated**: 2024-01-15
**API Version**: 1.0.0
