# Tool Hub 구현 계획서

> Visual Builder를 범용 워크플로우 자동화 플랫폼으로 확장하기 위한 구현 계획

## 목차

1. [개요](#1-개요)
2. [전문가 리뷰 결과 요약](#2-전문가-리뷰-결과-요약)
3. [시스템 아키텍처](#3-시스템-아키텍처)
4. [Phase -1: 아키텍처 스파이크 (2-3일)](#4-phase--1-아키텍처-스파이크-2-3일)
5. [Phase 0: MVP (2주)](#5-phase-0-mvp-2주)
6. [Phase 1: 핵심 기능 (2주)](#6-phase-1-핵심-기능-2주)
7. [Phase 2: 확장 기능 (2주)](#7-phase-2-확장-기능-2주)
8. [Phase 3: 고급 기능 (1주+)](#8-phase-3-고급-기능-1주)
9. [기술 스택](#9-기술-스택)
10. [데이터 모델](#10-데이터-모델)
11. [API 설계](#11-api-설계)
12. [보안 고려사항](#12-보안-고려사항)
13. [시스템 제한값 (가드레일)](#13-시스템-제한값-가드레일)
14. [에러 코드 정의](#14-에러-코드-정의)

---

## 1. 개요

### 1.1 목표

Visual Builder를 **범용 워크플로우 자동화 플랫폼**으로 확장:
- 코드 없이 드래그앤드롭으로 자동화 워크플로우 구축
- MCP 생태계(1000+ 서버) 활용으로 다양한 서비스 연동
- 스케줄링, 트리거로 자동 실행
- 프로덕션 레벨의 안정성과 보안

### 1.2 경쟁 플랫폼 대비 차별화

| 특징 | Zapier | n8n | Make | **AgentWeave** |
|------|--------|-----|------|----------------|
| AI Agent 네이티브 | △ | △ | △ | **◎** |
| 코드 양방향 동기화 | ✗ | ✗ | ✗ | **◎** |
| MCP 프로토콜 | ✗ | ✗ | ✗ | **◎** |
| 셀프호스팅 | ✗ | ◎ | ✗ | **◎** |
| 오픈소스 | ✗ | ◎ | ✗ | **◎** |

### 1.3 전체 로드맵

```
Day 1-3: Phase -1 (아키텍처 스파이크)
├── CRITICAL 버그 수정
├── 보안 취약점 해결
├── 기반 설계 확정
└── 기존 AgentWeave 코드 통합 계획

Week 1-2: Phase 0 (MVP)
├── MCP 서버 연동
├── 실행 엔진
├── 시크릿 관리
└── 기본 로깅

Week 3-4: Phase 1 (핵심)
├── Cron 스케줄링
├── Webhook 트리거
├── Mock 모드
└── 상태 저장

Week 5-6: Phase 2 (확장)
├── MCP 마켓플레이스
├── 디버그 모드
└── 버전 관리

Week 7+: Phase 3 (고급)
├── RBAC 권한
├── A/B 테스트
└── 분산 실행
```

---

## 2. 전문가 리뷰 결과 요약

> 2025-02-05 전문가 패널 리뷰 결과 (Martin Fowler, Michael Nygard, 보안 전문가, Karl Wiegers)

### 2.1 발견된 이슈 현황

| 전문가 | Critical | High | Medium | Low |
|--------|----------|------|--------|-----|
| Martin Fowler (아키텍처) | 3 | 3 | 3 | 2 |
| Michael Nygard (안정성) | 3 | 5 | 4 | 1 |
| 보안 전문가 | 3 | 5 | 4 | 3 |
| Karl Wiegers (요구사항) | 1 | 4 | 3 | 3 |
| **총계** | **10** | **17** | **14** | **9** |

### 2.2 CRITICAL 이슈 (P0 전 필수 해결)

| # | 이슈 | 위치 | 해결 방안 |
|---|------|------|----------|
| 1 | `asyncio.run()` 버그 | `secret_store.py:640` | `resolve()`를 async로 변경 |
| 2 | MCP 명령어 인젝션 | `MCPServerConfig` | 명령어 허용목록 구현 |
| 3 | Webhook 무인증 | `/webhook/:id` | HMAC 서명 검증 추가 |
| 4 | Circuit Breaker 부재 | MCP 연결 | 기존 `agentweave/resilience/` 활용 |
| 5 | 서비스 레이어 부재 | API → Core 직접 연결 | 서비스 추상화 레이어 추가 |
| 6 | 분산 실행 설계 지연 | P3의 Celery | `ExecutionRequest` DTO 선설계 |
| 7 | 크래시 전 체크포인트 없음 | StateStore 미통합 | 노드 실행 전 상태 저장 |

### 2.3 기존 AgentWeave 코드 활용

기존 AgentWeave에 이미 구현된 우수한 인프라를 활용해야 함:

| 컴포넌트 | 위치 | Tool Hub에서 활용 |
|----------|------|------------------|
| CircuitBreaker | `agentweave/resilience/circuit_breaker.py` | MCP 연결 보호 |
| RetryPolicy | `agentweave/resilience/retry.py` | 노드 실행 재시도 |
| TimeoutManager | `agentweave/resilience/timeout.py` | 모든 async 작업 |
| MCPClient | `agentweave/protocols/mcp/client.py` | MCPManager 대체 |

### 2.4 누락된 명세

**필수 가드레일:**
- 워크플로우당 최대 100개 노드
- MCP Tool 호출당 최대 30초
- 워크플로우 실행당 최대 5분
- Webhook 페이로드 최대 10MB

**필수 에러 코드:**
- `WORKFLOW_VALIDATION_FAILED`
- `MCP_SERVER_NOT_CONNECTED`
- `EXECUTION_TIMEOUT`
- `CIRCUIT_OPEN`
- `SECRET_NOT_FOUND`

**누락된 테이블:**
- `webhooks` (참조되었으나 정의 안됨)
- `audit_logs` (감사 로깅용)

**누락된 엔드포인트:**
- `GET /health/live`
- `GET /health/ready`
- `POST /api/workflows/:id/validate`
- `GET /api/webhooks`

---

## 3. 시스템 아키텍처

### 2.1 전체 구조

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Visual Builder (React Frontend)                  │
│  ┌────────────┬──────────────────────┬────────────────────────┐     │
│  │  Sidebar   │       Canvas         │    Properties Panel    │     │
│  │            │                      │                        │     │
│  │ ┌────────┐ │  ┌─────┐   ┌─────┐  │  ┌──────────────────┐  │     │
│  │ │ Agent  │ │  │Agent│──▶│Tool │  │  │ Configuration    │  │     │
│  │ │ Tool   │ │  └─────┘   └─────┘  │  │ Secrets (****)   │  │     │
│  │ │Trigger │ │      │              │  │ Test Options     │  │     │
│  │ │ Logic  │ │      ▼              │  │ ○ Full Run       │  │     │
│  │ └────────┘ │  ┌─────┐            │  │ ○ Dry Run        │  │     │
│  │            │  │Cond │            │  │ ○ Debug Mode     │  │     │
│  │ ┌────────┐ │  └─────┘            │  └──────────────────┘  │     │
│  │ │MCP Hub │ │                      │                        │     │
│  │ └────────┘ │                      │                        │     │
│  └────────────┴──────────────────────┴────────────────────────┘     │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Code Preview Panel                         │   │
│  │  from agentweave import Agent, Workflow, MCPTool...           │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                          REST API / WebSocket
                                    │
┌───────────────────────────────────▼─────────────────────────────────┐
│                    Workflow Engine (FastAPI Backend)                 │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   Executor   │  │  Scheduler   │  │ MCP Manager  │              │
│  │              │  │              │  │              │              │
│  │ • run()      │  │ • add_cron() │  │ • connect()  │              │
│  │ • run_debug()│  │ • add_hook() │  │ • list()     │              │
│  │ • run_mock() │  │ • remove()   │  │ • execute()  │              │
│  │ • stop()     │  │ • list()     │  │ • disconnect │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │Secret Store  │  │  Log Store   │  │ State Store  │              │
│  │              │  │              │  │              │              │
│  │ • get()      │  │ • write()    │  │ • save()     │              │
│  │ • set()      │  │ • query()    │  │ • load()     │              │
│  │ • delete()   │  │ • stream()   │  │ • resume()   │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │
┌───────────────────────────────────▼─────────────────────────────────┐
│                         Storage Layer                                │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    SQLite / PostgreSQL                        │   │
│  │  • workflows      • executions      • secrets (encrypted)     │   │
│  │  • schedules      • logs            • users (P3)              │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │
┌───────────────────────────────────▼─────────────────────────────────┐
│                       MCP Server Ecosystem                           │
│                                                                      │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │  Fetch  │ │Filesys  │ │  Slack  │ │   Git   │ │ Custom  │       │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘       │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │Postgres │ │  Redis  │ │  Email  │ │ Browser │ │   ...   │       │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘       │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 디렉토리 구조

```
visual-builder/
├── src/                          # Frontend (React)
│   ├── components/
│   │   ├── Blocks/               # 기존 블록 컴포넌트
│   │   ├── Canvas/
│   │   ├── Sidebar/
│   │   │   ├── BlockPalette.tsx
│   │   │   └── MCPHub.tsx        # NEW: MCP 서버 브라우저
│   │   ├── PropertiesPanel/
│   │   │   ├── AgentProperties.tsx
│   │   │   ├── MCPToolProperties.tsx
│   │   │   ├── TriggerProperties.tsx  # NEW
│   │   │   └── SecretInput.tsx        # NEW: 마스킹된 시크릿 입력
│   │   ├── ExecutionPanel/       # NEW: 실행 상태 표시
│   │   │   ├── ExecutionPanel.tsx
│   │   │   ├── LogViewer.tsx
│   │   │   └── DebugControls.tsx
│   │   └── RunDialog/            # NEW: 실행 옵션 다이얼로그
│   ├── stores/
│   │   ├── workflowStore.ts
│   │   ├── executionStore.ts     # NEW
│   │   └── mcpStore.ts           # NEW
│   ├── services/
│   │   └── api.ts                # NEW: Backend API 클라이언트
│   └── types/
│       ├── blocks.ts
│       ├── execution.ts          # NEW
│       └── mcp.ts                # NEW
│
├── backend/                      # NEW: Backend (FastAPI)
│   ├── app/
│   │   ├── main.py               # FastAPI app
│   │   ├── config.py             # 설정
│   │   ├── api/
│   │   │   ├── workflows.py      # 워크플로우 CRUD
│   │   │   ├── executions.py     # 실행 관리
│   │   │   ├── mcp.py            # MCP 서버 관리
│   │   │   ├── schedules.py      # 스케줄 관리
│   │   │   └── secrets.py        # 시크릿 관리
│   │   ├── core/
│   │   │   ├── executor.py       # 워크플로우 실행 엔진
│   │   │   ├── scheduler.py      # 스케줄러
│   │   │   ├── mcp_manager.py    # MCP 연결 관리
│   │   │   └── secret_store.py   # 시크릿 저장소
│   │   ├── models/
│   │   │   ├── workflow.py
│   │   │   ├── execution.py
│   │   │   └── schedule.py
│   │   └── db/
│   │       ├── database.py
│   │       └── migrations/
│   ├── tests/
│   └── requirements.txt
│
└── mcp-servers/                  # NEW: 내장 MCP 서버 (선택)
    ├── email/
    └── http/
```

---

## 4. Phase -1: 아키텍처 스파이크 (2-3일)

> **목표**: P0 개발 전 CRITICAL 이슈 해결 및 기반 아키텍처 확정

### 4.1 CRITICAL 버그 수정

#### 4.1.1 SecretStore asyncio.run() 버그 수정

**문제**: `resolve()` 메서드에서 `asyncio.run()`을 동기 컨텍스트에서 호출하면 async 컨텍스트에서 크래시 발생

**수정된 코드**:
```python
# backend/app/core/secret_store.py

import re
from typing import Set

SECRET_NAME_PATTERN = re.compile(r'^[A-Z][A-Z0-9_]{0,63}$')

class SecretStore:
    """암호화된 시크릿 저장소"""

    def __init__(self, db: Database):
        self.db = db
        self._key = os.environ.get("SECRET_KEY")
        if not self._key:
            raise RuntimeError(
                "SECRET_KEY 환경변수가 필요합니다. "
                "생성: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        try:
            self._fernet = Fernet(self._key.encode() if isinstance(self._key, str) else self._key)
        except Exception as e:
            raise RuntimeError(f"SECRET_KEY 형식 오류: {e}")

    async def resolve(self, text: str, allowed_secrets: Set[str] = None) -> str:
        """텍스트 내 시크릿 참조 치환 (async 버전)

        Args:
            text: ${SECRET_NAME} 형식의 참조를 포함한 텍스트
            allowed_secrets: 이 컨텍스트에서 접근 허용된 시크릿 화이트리스트
        """
        pattern = r'\$\{([^}]+)\}'
        matches = list(re.finditer(pattern, text))

        if not matches:
            return text

        result = text
        for match in reversed(matches):  # 위치 유지를 위해 역순
            name = match.group(1)

            # 시크릿 이름 형식 검증
            if not SECRET_NAME_PATTERN.match(name):
                raise ValueError(f"잘못된 시크릿 이름 형식: {name}")

            # 화이트리스트 체크
            if allowed_secrets and name not in allowed_secrets:
                raise PermissionError(f"시크릿 {name}에 대한 접근 권한 없음")

            value = await self.get(name)
            if value is None:
                raise ValueError(f"시크릿 {name}을 찾을 수 없음")

            result = result[:match.start()] + value + result[match.end():]

        return result
```

#### 4.1.2 MCP 명령어 인젝션 방지

**수정된 코드**:
```python
# backend/app/core/mcp_manager.py

import shutil
import re
import resource
from dataclasses import dataclass

# 허용된 명령어 화이트리스트
ALLOWED_MCP_COMMANDS = {
    "npx": shutil.which("npx"),
    "node": shutil.which("node"),
    "python": shutil.which("python"),
    "python3": shutil.which("python3"),
    "uvx": shutil.which("uvx"),
}

# 차단된 인자
BLOCKED_ARGS = {"--eval", "-e", "--exec", "-c"}

@dataclass
class MCPServerConfig:
    """MCP 서버 설정 (보안 검증 포함)"""
    id: str
    name: str
    command: str
    args: list[str]
    env: dict[str, str] | None = None

    def __post_init__(self):
        # 명령어 허용목록 검증
        if self.command not in ALLOWED_MCP_COMMANDS:
            raise ValueError(
                f"명령어 '{self.command}' 허용 안됨. "
                f"허용: {list(ALLOWED_MCP_COMMANDS.keys())}"
            )

        # 위험한 인자 체크
        for arg in self.args:
            if arg in BLOCKED_ARGS:
                raise ValueError(f"인자 '{arg}'는 보안상 차단됨")

            # 경로 탐색 방지
            if ".." in arg or arg.startswith("/"):
                raise ValueError(f"경로 탐색 감지됨: {arg}")

        # 환경변수 키 검증
        if self.env:
            for key in self.env.keys():
                if not re.match(r'^[A-Z_][A-Z0-9_]*$', key):
                    raise ValueError(f"잘못된 환경변수 이름: {key}")
```

#### 4.1.3 Webhook HMAC 서명 검증

**수정된 코드**:
```python
# backend/app/api/webhooks.py

import hmac
import hashlib
import time
from fastapi import APIRouter, Request, HTTPException

router = APIRouter()

@router.post("/webhook/{webhook_id}")
async def handle_webhook(
    webhook_id: str,
    request: Request,
    executor: WorkflowExecutor = Depends(),
):
    """HMAC 서명 검증이 포함된 Webhook 핸들러"""

    webhook = await db.fetchone(
        "SELECT workflow_id, secret, allowed_ips FROM webhooks WHERE id = ?",
        (webhook_id,),
    )

    if not webhook:
        raise HTTPException(404, "Webhook not found")

    # IP 허용목록 체크
    client_ip = request.client.host
    if webhook["allowed_ips"]:
        allowed = webhook["allowed_ips"].split(",")
        if client_ip not in allowed:
            raise HTTPException(403, "IP not allowed")

    # HMAC 서명 검증
    body = await request.body()
    signature = request.headers.get("X-Webhook-Signature")
    timestamp = request.headers.get("X-Webhook-Timestamp")

    if not signature or not timestamp:
        raise HTTPException(401, "서명 헤더 누락")

    # 리플레이 공격 방지 (5분 윈도우)
    try:
        ts = int(timestamp)
        if abs(time.time() - ts) > 300:
            raise HTTPException(401, "타임스탬프 만료")
    except ValueError:
        raise HTTPException(401, "잘못된 타임스탬프")

    # 예상 서명 계산
    payload = f"{timestamp}.{body.decode()}"
    expected = hmac.new(
        webhook["secret"].encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature, f"sha256={expected}"):
        raise HTTPException(401, "잘못된 서명")

    # 워크플로우 실행
    data = json.loads(body)
    workflow = await db.get_workflow(webhook["workflow_id"])
    execution = await executor.run(workflow, input=json.dumps(data))

    return {"execution_id": execution.id, "status": execution.status.value}
```

### 4.2 회복탄력성 통합

기존 AgentWeave 회복탄력성 모듈을 통합:

```python
# backend/app/core/executor.py

from agentweave.resilience.config import ResilienceConfig
from agentweave.resilience.circuit_breaker import CircuitBreaker
from agentweave.resilience.retry import RetryPolicy, RetryStrategy
from agentweave.resilience.timeout import TimeoutManager

class WorkflowExecutor:
    """회복탄력성이 통합된 워크플로우 실행 엔진"""

    def __init__(
        self,
        mcp_manager: MCPManager,
        secret_store: SecretStore,
        state_store: ExecutionStateStore,
    ):
        self.mcp_manager = mcp_manager
        self.secret_store = secret_store
        self.state_store = state_store
        self._mcp_breakers: dict[str, CircuitBreaker] = {}

        # 회복탄력성 설정
        self._resilience = ResilienceConfig(
            retry_enabled=True,
            retry_policy=RetryPolicy(
                max_retries=3,
                strategy=RetryStrategy.EXPONENTIAL,
                retryable_errors=(ConnectionError, asyncio.TimeoutError),
            ),
            circuit_breaker_enabled=True,
            timeout_enabled=True,
            timeout_manager=TimeoutManager(default_timeout=30.0),
        )

    def _get_or_create_breaker(self, server_id: str) -> CircuitBreaker:
        """MCP 서버별 Circuit Breaker 가져오기/생성"""
        if server_id not in self._mcp_breakers:
            self._mcp_breakers[server_id] = CircuitBreaker(
                failure_threshold=3,
                timeout=60.0,
                name=f"mcp_{server_id}",
            )
        return self._mcp_breakers[server_id]

    async def _execute_node_with_checkpoint(
        self,
        execution_id: str,
        node: WorkflowNode,
        context: dict,
        mode: str,
    ) -> NodeExecution:
        """체크포인트와 함께 노드 실행"""
        # 실행 전 상태 저장
        await self.state_store.save_state(execution_id, node.id, context)

        try:
            result = await self._execute_node(node, context, mode)
            return result
        except Exception as e:
            await self.state_store.mark_failed(execution_id, node.id, str(e))
            raise

    async def _run_mcp_tool(self, node: WorkflowNode, context: dict) -> Any:
        """Circuit Breaker와 타임아웃이 적용된 MCP Tool 실행"""
        server_id = node.data["serverId"]
        breaker = self._get_or_create_breaker(server_id)

        # 시크릿 치환 (async)
        parameters = node.data.get("parameters", {})
        resolved_params = {}
        for key, value in parameters.items():
            if isinstance(value, str):
                resolved_params[key] = await self.secret_store.resolve(value)
            else:
                resolved_params[key] = value

        # Circuit Breaker + 타임아웃 적용 실행
        async def execute():
            return await asyncio.wait_for(
                self.mcp_manager.execute_tool(
                    server_id=server_id,
                    tool_name=node.data["toolName"],
                    arguments=resolved_params,
                ),
                timeout=30.0,  # 노드별 타임아웃
            )

        return await breaker.execute(execute)
```

### 4.3 확장된 ExecutionStatus

```python
# backend/app/core/executor.py

class ExecutionStatus(Enum):
    """확장된 실행 상태 (디버그/분산 실행 지원)"""
    PENDING = "pending"
    QUEUED = "queued"        # 분산 실행 대기
    RUNNING = "running"
    PAUSED = "paused"        # 디버그 모드 중단점
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"    # 재시도 중
    TIMED_OUT = "timed_out"  # 타임아웃 (FAILED와 구분)
```

### 4.4 서비스 레이어 추가

```python
# backend/app/services/workflow_service.py

class WorkflowService:
    """API와 Core 사이의 서비스 레이어"""

    def __init__(
        self,
        executor: WorkflowExecutor,
        repository: IWorkflowRepository,
        audit_logger: AuditLogger,
    ):
        self.executor = executor
        self.repository = repository
        self.audit_logger = audit_logger

    async def run_workflow(
        self,
        workflow_id: str,
        input: str,
        mode: str,
        user: User,
    ) -> WorkflowExecution:
        """워크플로우 실행 (감사 로깅 포함)"""
        workflow = await self.repository.get_by_id(workflow_id)
        if not workflow:
            raise WorkflowNotFoundError(workflow_id)

        # 실행 전 검증
        await self._validate_workflow(workflow)

        # 감사 로그
        await self.audit_logger.log(
            event_type=AuditEventType.WORKFLOW_EXECUTE,
            user=user,
            resource_type="workflow",
            resource_id=workflow_id,
            action="run",
            details={"mode": mode},
        )

        return await self.executor.run(workflow, input, mode)

    async def _validate_workflow(self, workflow: Workflow) -> None:
        """실행 전 워크플로우 검증"""
        # 순환 의존성 체크
        if self._has_cycle(workflow):
            raise WorkflowValidationError("워크플로우에 순환 의존성 존재")

        # 노드 수 제한 체크
        if len(workflow.nodes) > 100:
            raise WorkflowValidationError("노드 수가 100개를 초과함")

        # 연결 안된 노드 체크
        orphans = self._find_orphan_nodes(workflow)
        if orphans:
            raise WorkflowValidationError(f"연결 안된 노드: {orphans}")
```

### 4.5 분산 실행을 위한 DTO 설계

```python
# backend/app/dtos/execution.py

from dataclasses import dataclass
from typing import Any
import json

@dataclass
class ExecutionRequest:
    """직렬화 가능한 실행 요청 DTO (Celery 호환)"""
    workflow_id: str
    input: str
    mode: str = "full"
    user_id: str | None = None
    start_from_node: str | None = None
    context: dict[str, Any] | None = None

    def to_json(self) -> str:
        return json.dumps({
            "workflow_id": self.workflow_id,
            "input": self.input,
            "mode": self.mode,
            "user_id": self.user_id,
            "start_from_node": self.start_from_node,
            "context": self.context,
        })

    @classmethod
    def from_json(cls, data: str) -> "ExecutionRequest":
        d = json.loads(data)
        return cls(**d)
```

### 4.6 Phase -1 체크리스트

- [ ] SecretStore `resolve()` async 버전으로 수정
- [ ] MCPServerConfig 명령어 허용목록 구현
- [ ] Webhook HMAC 서명 검증 추가
- [ ] 기존 AgentWeave CircuitBreaker 통합
- [ ] 기존 AgentWeave TimeoutManager 통합
- [ ] ExecutionStatus enum 확장
- [ ] WorkflowService 레이어 추가
- [ ] ExecutionRequest DTO 정의
- [ ] 노드 실행 전 체크포인트 저장 로직 추가

---

## 5. Phase 0: MVP (2주)

### 3.1 MCP 서버 연동

#### 3.1.1 목표
- 기존 MCP 서버에 연결하여 Tool 목록 가져오기
- Tool을 워크플로우에서 실행 가능하게 하기

#### 3.1.2 구현 항목

**Backend: MCP Manager**
```python
# backend/app/core/mcp_manager.py

from dataclasses import dataclass
from typing import Any
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

@dataclass
class MCPServerConfig:
    """MCP 서버 설정"""
    id: str
    name: str
    command: str  # e.g., "npx", "python"
    args: list[str]  # e.g., ["-y", "@anthropic/mcp-fetch"]
    env: dict[str, str] | None = None

@dataclass
class MCPTool:
    """MCP Tool 정보"""
    server_id: str
    name: str
    description: str
    input_schema: dict[str, Any]

class MCPManager:
    """MCP 서버 연결 및 Tool 실행 관리"""

    def __init__(self):
        self._sessions: dict[str, ClientSession] = {}
        self._tools: dict[str, list[MCPTool]] = {}

    async def connect(self, config: MCPServerConfig) -> None:
        """MCP 서버에 연결"""
        server_params = StdioServerParameters(
            command=config.command,
            args=config.args,
            env=config.env,
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Tool 목록 가져오기
                tools_result = await session.list_tools()
                self._tools[config.id] = [
                    MCPTool(
                        server_id=config.id,
                        name=tool.name,
                        description=tool.description or "",
                        input_schema=tool.inputSchema,
                    )
                    for tool in tools_result.tools
                ]

                self._sessions[config.id] = session

    async def execute_tool(
        self,
        server_id: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> Any:
        """Tool 실행"""
        session = self._sessions.get(server_id)
        if not session:
            raise ValueError(f"Server {server_id} not connected")

        result = await session.call_tool(tool_name, arguments)
        return result.content

    def list_tools(self, server_id: str | None = None) -> list[MCPTool]:
        """연결된 Tool 목록"""
        if server_id:
            return self._tools.get(server_id, [])
        return [tool for tools in self._tools.values() for tool in tools]

    async def disconnect(self, server_id: str) -> None:
        """연결 해제"""
        if server_id in self._sessions:
            del self._sessions[server_id]
            del self._tools[server_id]
```

**Frontend: MCP Hub UI**
```typescript
// src/components/Sidebar/MCPHub.tsx

interface MCPServer {
  id: string;
  name: string;
  status: 'connected' | 'disconnected' | 'connecting';
  tools: MCPTool[];
}

interface MCPTool {
  serverId: string;
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
}

export const MCPHub = memo(function MCPHub() {
  const [servers, setServers] = useState<MCPServer[]>([]);
  const [selectedServer, setSelectedServer] = useState<string | null>(null);

  // 서버 연결
  const connectServer = async (config: MCPServerConfig) => {
    await api.mcp.connect(config);
    await refreshServers();
  };

  // Tool을 캔버스에 드래그
  const onDragStart = (e: DragEvent, tool: MCPTool) => {
    e.dataTransfer.setData('application/reactflow', 'mcp_tool');
    e.dataTransfer.setData('tool', JSON.stringify(tool));
  };

  return (
    <div className="mcp-hub">
      <h3>MCP Servers</h3>

      {/* 서버 목록 */}
      {servers.map(server => (
        <div key={server.id} className="server-item">
          <span className={`status-${server.status}`} />
          <span>{server.name}</span>

          {/* Tool 목록 */}
          {server.status === 'connected' && (
            <div className="tools">
              {server.tools.map(tool => (
                <div
                  key={tool.name}
                  draggable
                  onDragStart={(e) => onDragStart(e, tool)}
                  className="tool-item"
                >
                  {tool.name}
                </div>
              ))}
            </div>
          )}
        </div>
      ))}

      {/* 서버 추가 버튼 */}
      <button onClick={() => openAddServerDialog()}>
        + Add MCP Server
      </button>
    </div>
  );
});
```

#### 3.1.3 지원할 기본 MCP 서버

| 서버 | 패키지 | 용도 |
|------|--------|------|
| Fetch | `@anthropic/mcp-fetch` | HTTP 요청, 웹 크롤링 |
| Filesystem | `@anthropic/mcp-filesystem` | 파일 읽기/쓰기 |
| Sequential Thinking | `@anthropic/mcp-sequentialthinking` | 복잡한 추론 |

---

### 3.2 실행 엔진

#### 3.2.1 목표
- 워크플로우를 실제로 실행
- 각 노드를 순서대로 실행하고 결과 전달
- 에러 처리 및 로깅

#### 3.2.2 구현 항목

**Backend: Workflow Executor**
```python
# backend/app/core/executor.py

from dataclasses import dataclass
from enum import Enum
from typing import Any
import asyncio
from datetime import datetime

class ExecutionStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class NodeExecution:
    """개별 노드 실행 결과"""
    node_id: str
    status: ExecutionStatus
    input: Any
    output: Any | None
    error: str | None
    started_at: datetime
    completed_at: datetime | None

@dataclass
class WorkflowExecution:
    """워크플로우 전체 실행 결과"""
    id: str
    workflow_id: str
    status: ExecutionStatus
    node_executions: list[NodeExecution]
    started_at: datetime
    completed_at: datetime | None

class WorkflowExecutor:
    """워크플로우 실행 엔진"""

    def __init__(
        self,
        mcp_manager: MCPManager,
        secret_store: SecretStore,
    ):
        self.mcp_manager = mcp_manager
        self.secret_store = secret_store
        self._running: dict[str, asyncio.Task] = {}

    async def run(
        self,
        workflow: Workflow,
        input: str,
        mode: str = "full",  # full, mock, debug
    ) -> WorkflowExecution:
        """워크플로우 실행"""
        execution = WorkflowExecution(
            id=generate_id(),
            workflow_id=workflow.id,
            status=ExecutionStatus.RUNNING,
            node_executions=[],
            started_at=datetime.now(),
            completed_at=None,
        )

        try:
            # 토폴로지 정렬로 실행 순서 결정
            ordered_nodes = self._topological_sort(workflow)

            # 각 노드 실행
            context = {"input": input}

            for node in ordered_nodes:
                node_result = await self._execute_node(
                    node, context, mode
                )
                execution.node_executions.append(node_result)

                if node_result.status == ExecutionStatus.FAILED:
                    execution.status = ExecutionStatus.FAILED
                    break

                # 다음 노드에 결과 전달
                context[node.id] = node_result.output

            if execution.status != ExecutionStatus.FAILED:
                execution.status = ExecutionStatus.COMPLETED

        except Exception as e:
            execution.status = ExecutionStatus.FAILED

        execution.completed_at = datetime.now()
        return execution

    async def _execute_node(
        self,
        node: WorkflowNode,
        context: dict,
        mode: str,
    ) -> NodeExecution:
        """개별 노드 실행"""
        started_at = datetime.now()

        try:
            if mode == "mock":
                # Mock 모드: 실제 실행 없이 샘플 출력
                output = self._get_mock_output(node)
            else:
                # 실제 실행
                if node.type == "agent":
                    output = await self._run_agent(node, context)
                elif node.type == "mcp_tool":
                    output = await self._run_mcp_tool(node, context)
                elif node.type == "condition":
                    output = await self._run_condition(node, context)
                else:
                    output = None

            return NodeExecution(
                node_id=node.id,
                status=ExecutionStatus.COMPLETED,
                input=context.get("input"),
                output=output,
                error=None,
                started_at=started_at,
                completed_at=datetime.now(),
            )

        except Exception as e:
            return NodeExecution(
                node_id=node.id,
                status=ExecutionStatus.FAILED,
                input=context.get("input"),
                output=None,
                error=str(e),
                started_at=started_at,
                completed_at=datetime.now(),
            )

    async def _run_agent(self, node: WorkflowNode, context: dict) -> str:
        """Agent 노드 실행"""
        from agentweave import Agent

        data = node.data
        agent = Agent(
            name=data["name"],
            role=data["role"],
            model=data["model"],
            temperature=data.get("temperature", 0.7),
            system_prompt=data.get("systemPrompt"),
        )

        # 이전 노드의 출력을 입력으로 사용
        input_text = self._resolve_input(node, context)
        result = await agent.run(input_text)

        return result.output

    async def _run_mcp_tool(self, node: WorkflowNode, context: dict) -> Any:
        """MCP Tool 노드 실행"""
        data = node.data

        # 시크릿 치환
        arguments = self._resolve_secrets(data.get("parameters", {}))

        result = await self.mcp_manager.execute_tool(
            server_id=data["serverId"],
            tool_name=data["toolName"],
            arguments=arguments,
        )

        return result

    def stop(self, execution_id: str) -> None:
        """실행 중단"""
        if execution_id in self._running:
            self._running[execution_id].cancel()
```

---

### 3.3 시크릿 관리

#### 3.3.1 목표
- API 키 등 민감 정보를 안전하게 저장
- 워크플로우 정의에 하드코딩 방지
- UI에서 마스킹 표시

#### 3.3.2 구현 항목

**Backend: Secret Store**
```python
# backend/app/core/secret_store.py

from cryptography.fernet import Fernet
import os

class SecretStore:
    """암호화된 시크릿 저장소"""

    def __init__(self, db: Database):
        self.db = db
        self._key = os.environ.get("SECRET_KEY") or Fernet.generate_key()
        self._fernet = Fernet(self._key)

    async def set(self, name: str, value: str) -> None:
        """시크릿 저장 (암호화)"""
        encrypted = self._fernet.encrypt(value.encode())
        await self.db.execute(
            "INSERT OR REPLACE INTO secrets (name, value) VALUES (?, ?)",
            (name, encrypted),
        )

    async def get(self, name: str) -> str | None:
        """시크릿 조회 (복호화)"""
        row = await self.db.fetchone(
            "SELECT value FROM secrets WHERE name = ?",
            (name,),
        )
        if row:
            return self._fernet.decrypt(row["value"]).decode()
        return None

    async def delete(self, name: str) -> None:
        """시크릿 삭제"""
        await self.db.execute(
            "DELETE FROM secrets WHERE name = ?",
            (name,),
        )

    async def list(self) -> list[str]:
        """시크릿 이름 목록 (값은 반환 안 함)"""
        rows = await self.db.fetchall("SELECT name FROM secrets")
        return [row["name"] for row in rows]

    def resolve(self, text: str) -> str:
        """텍스트 내 시크릿 참조 치환

        예: "${OPENAI_API_KEY}" -> 실제 값
        """
        import re
        pattern = r'\$\{([^}]+)\}'

        def replacer(match):
            name = match.group(1)
            value = asyncio.run(self.get(name))
            return value or match.group(0)

        return re.sub(pattern, replacer, text)
```

**Frontend: Secret Input Component**
```typescript
// src/components/PropertiesPanel/SecretInput.tsx

interface SecretInputProps {
  label: string;
  value: string;  // "${SECRET_NAME}" 형식
  onChange: (value: string) => void;
  secrets: string[];  // 사용 가능한 시크릿 목록
}

export const SecretInput = memo(function SecretInput({
  label,
  value,
  onChange,
  secrets,
}: SecretInputProps) {
  const isSecretRef = value.startsWith('${') && value.endsWith('}');

  return (
    <div className="secret-input">
      <Label>{label}</Label>

      {isSecretRef ? (
        // 시크릿 참조 모드
        <div className="flex gap-2">
          <Select value={value} onValueChange={onChange}>
            <SelectTrigger>
              <SelectValue placeholder="Select secret" />
            </SelectTrigger>
            <SelectContent>
              {secrets.map(name => (
                <SelectItem key={name} value={`\${${name}}`}>
                  {name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => onChange('')}
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
      ) : (
        // 직접 입력 모드
        <div className="flex gap-2">
          <Input
            type="password"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder="Enter value or use secret"
          />
          <Button
            variant="ghost"
            size="icon"
            onClick={() => onChange('${}')}
            title="Use secret reference"
          >
            <Key className="w-4 h-4" />
          </Button>
        </div>
      )}

      <p className="text-xs text-muted-foreground mt-1">
        Use ${'{SECRET_NAME}'} to reference stored secrets
      </p>
    </div>
  );
});
```

---

### 3.4 기본 로깅

#### 3.4.1 목표
- 워크플로우 실행 결과 저장
- 각 노드별 입/출력 기록
- UI에서 실행 히스토리 조회

#### 3.4.2 구현 항목

**Backend: Execution Log**
```python
# backend/app/models/execution.py

from sqlalchemy import Column, String, DateTime, JSON, Enum
from datetime import datetime

class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id = Column(String, primary_key=True)
    workflow_id = Column(String, index=True)
    status = Column(Enum(ExecutionStatus))
    input = Column(String)
    output = Column(String, nullable=True)
    error = Column(String, nullable=True)
    node_logs = Column(JSON)  # 각 노드별 로그
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
```

**Frontend: Execution Panel**
```typescript
// src/components/ExecutionPanel/ExecutionPanel.tsx

export const ExecutionPanel = memo(function ExecutionPanel() {
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [selectedExecution, setSelectedExecution] = useState<string | null>(null);

  return (
    <div className="execution-panel">
      <h3>Execution History</h3>

      <div className="execution-list">
        {executions.map(exec => (
          <div
            key={exec.id}
            className={cn(
              "execution-item",
              exec.status === 'completed' && "bg-green-50",
              exec.status === 'failed' && "bg-red-50",
            )}
            onClick={() => setSelectedExecution(exec.id)}
          >
            <span className={`status-${exec.status}`}>
              {exec.status}
            </span>
            <span className="time">
              {formatTime(exec.startedAt)}
            </span>
            <span className="duration">
              {exec.durationMs}ms
            </span>
          </div>
        ))}
      </div>

      {selectedExecution && (
        <LogViewer executionId={selectedExecution} />
      )}
    </div>
  );
});
```

---

## 4. Phase 1: 핵심 기능 (2주)

### 4.1 Cron 스케줄링

#### 4.1.1 목표
- "매일 9시", "매주 월요일" 같은 예약 실행
- Cron 표현식 지원
- 스케줄 관리 UI

#### 4.1.2 구현 항목

**Backend: Scheduler**
```python
# backend/app/core/scheduler.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

class WorkflowScheduler:
    """워크플로우 스케줄러"""

    def __init__(self, executor: WorkflowExecutor, db: Database):
        self.executor = executor
        self.db = db
        self.scheduler = AsyncIOScheduler()

    def start(self):
        """스케줄러 시작"""
        self.scheduler.start()
        # DB에서 스케줄 로드
        asyncio.create_task(self._load_schedules())

    async def add_cron(
        self,
        workflow_id: str,
        cron_expression: str,
        input: str = "",
    ) -> str:
        """Cron 스케줄 추가

        Args:
            cron_expression: "0 9 * * *" (매일 9시)
        """
        schedule_id = generate_id()

        # APScheduler에 추가
        self.scheduler.add_job(
            self._run_workflow,
            CronTrigger.from_crontab(cron_expression),
            args=[workflow_id, input],
            id=schedule_id,
        )

        # DB에 저장
        await self.db.execute(
            """INSERT INTO schedules
               (id, workflow_id, type, expression, input, enabled)
               VALUES (?, ?, 'cron', ?, ?, true)""",
            (schedule_id, workflow_id, cron_expression, input),
        )

        return schedule_id

    async def remove(self, schedule_id: str) -> None:
        """스케줄 제거"""
        self.scheduler.remove_job(schedule_id)
        await self.db.execute(
            "DELETE FROM schedules WHERE id = ?",
            (schedule_id,),
        )

    async def _run_workflow(self, workflow_id: str, input: str):
        """스케줄된 워크플로우 실행"""
        workflow = await self.db.get_workflow(workflow_id)
        await self.executor.run(workflow, input)
```

**Frontend: Trigger Block**
```typescript
// src/components/Blocks/TriggerNode.tsx

export const TriggerNode = memo(function TriggerNode({ data, selected }) {
  return (
    <BaseNode color="#6366F1" selected={selected} hasInput={false}>
      <div className="p-3">
        <div className="flex items-center gap-2 mb-2">
          <div className="p-1.5 rounded bg-indigo-100">
            <Clock className="w-4 h-4 text-indigo-600" />
          </div>
          <div>
            <div className="font-medium text-sm">
              {data.type === 'cron' ? 'Schedule' : 'Webhook'}
            </div>
            <div className="text-xs text-muted-foreground">
              {data.type === 'cron'
                ? cronToHuman(data.expression)  // "Every day at 9:00 AM"
                : `POST /webhook/${data.webhookId}`
              }
            </div>
          </div>
        </div>
      </div>
    </BaseNode>
  );
});
```

---

### 4.2 Webhook 트리거

#### 4.2.1 목표
- 외부 서비스에서 HTTP 요청으로 워크플로우 실행
- 고유 Webhook URL 생성
- 요청 데이터를 워크플로우 입력으로 전달

#### 4.2.2 구현 항목

**Backend: Webhook Handler**
```python
# backend/app/api/webhooks.py

from fastapi import APIRouter, Request

router = APIRouter()

@router.post("/webhook/{webhook_id}")
async def handle_webhook(
    webhook_id: str,
    request: Request,
    executor: WorkflowExecutor = Depends(),
):
    """Webhook 수신 및 워크플로우 실행"""
    # Webhook ID로 워크플로우 조회
    webhook = await db.fetchone(
        "SELECT workflow_id, input_mapping FROM webhooks WHERE id = ?",
        (webhook_id,),
    )

    if not webhook:
        raise HTTPException(404, "Webhook not found")

    # 요청 데이터 파싱
    body = await request.json()

    # 워크플로우 실행
    workflow = await db.get_workflow(webhook["workflow_id"])
    execution = await executor.run(
        workflow,
        input=json.dumps(body),
    )

    return {
        "execution_id": execution.id,
        "status": execution.status.value,
    }
```

---

### 4.3 Mock 모드

#### 4.3.1 목표
- 실제 API 호출 없이 워크플로우 테스트
- 각 Tool에 대한 Mock 응답 설정
- 빠른 개발/디버깅 지원

#### 4.3.2 구현 항목

**Backend: Mock Executor**
```python
# backend/app/core/executor.py (확장)

class WorkflowExecutor:

    def _get_mock_output(self, node: WorkflowNode) -> Any:
        """노드 타입별 Mock 출력"""
        if node.type == "agent":
            return f"[Mock] Agent '{node.data['name']}' response"

        elif node.type == "mcp_tool":
            tool_name = node.data["toolName"]

            # 사용자 정의 Mock 응답이 있으면 사용
            if "mockResponse" in node.data:
                return node.data["mockResponse"]

            # 기본 Mock 응답
            return {
                "fetch": {"content": "[Mock] Fetched content..."},
                "send_email": {"success": True, "message_id": "mock-123"},
                "query_database": {"rows": [], "count": 0},
            }.get(tool_name, {"result": "mock"})

        elif node.type == "condition":
            return True  # 항상 true 경로

        return None
```

**Frontend: Run Dialog**
```typescript
// src/components/RunDialog/RunDialog.tsx

export const RunDialog = memo(function RunDialog({
  open,
  onOpenChange,
  onRun,
}) {
  const [mode, setMode] = useState<'full' | 'mock' | 'debug'>('full');
  const [input, setInput] = useState('');

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Run Workflow</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {/* 실행 모드 선택 */}
          <div className="space-y-2">
            <Label>Execution Mode</Label>
            <RadioGroup value={mode} onValueChange={setMode}>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="full" id="full" />
                <Label htmlFor="full">
                  Full Run
                  <span className="text-xs text-muted-foreground ml-2">
                    Execute all nodes with real APIs
                  </span>
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="mock" id="mock" />
                <Label htmlFor="mock">
                  Mock Run
                  <span className="text-xs text-muted-foreground ml-2">
                    Use mock responses (no API calls)
                  </span>
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <RadioGroupItem value="debug" id="debug" />
                <Label htmlFor="debug">
                  Debug Mode
                  <span className="text-xs text-muted-foreground ml-2">
                    Step through nodes one at a time
                  </span>
                </Label>
              </div>
            </RadioGroup>
          </div>

          {/* 입력 */}
          <div className="space-y-2">
            <Label>Input</Label>
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Enter workflow input..."
              rows={4}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={() => onRun(mode, input)}>
            <Play className="w-4 h-4 mr-2" />
            Run
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
});
```

---

### 4.4 상태 저장/복구

#### 4.4.1 목표
- 실행 중 상태를 저장하여 중단/재개 가능
- 서버 재시작 후에도 실행 복구
- 장시간 실행 워크플로우 지원

#### 4.4.2 구현 항목

**Backend: State Store**
```python
# backend/app/core/state_store.py

class ExecutionStateStore:
    """실행 상태 저장소"""

    async def save_state(
        self,
        execution_id: str,
        current_node: str,
        context: dict,
    ) -> None:
        """현재 실행 상태 저장"""
        await self.db.execute(
            """INSERT OR REPLACE INTO execution_states
               (execution_id, current_node, context, updated_at)
               VALUES (?, ?, ?, ?)""",
            (execution_id, current_node, json.dumps(context), datetime.now()),
        )

    async def load_state(self, execution_id: str) -> dict | None:
        """저장된 실행 상태 로드"""
        row = await self.db.fetchone(
            "SELECT * FROM execution_states WHERE execution_id = ?",
            (execution_id,),
        )
        if row:
            return {
                "current_node": row["current_node"],
                "context": json.loads(row["context"]),
            }
        return None

    async def resume(self, execution_id: str) -> WorkflowExecution:
        """중단된 실행 재개"""
        state = await self.load_state(execution_id)
        if not state:
            raise ValueError("No saved state found")

        # 중단된 노드부터 실행 재개
        return await self.executor.run(
            workflow,
            start_from=state["current_node"],
            context=state["context"],
        )
```

---

## 5. Phase 2: 확장 기능 (2주)

### 5.1 MCP 마켓플레이스

#### 5.1.1 목표
- 인기 MCP 서버 카탈로그 제공
- 원클릭 설치/연결
- 카테고리별 검색

#### 5.1.2 구현 항목

**MCP Server Catalog**
```typescript
// src/data/mcpCatalog.ts

export const MCP_CATALOG: MCPServerInfo[] = [
  {
    id: 'fetch',
    name: 'Fetch',
    category: 'Web',
    description: 'HTTP requests and web content fetching',
    package: '@anthropic/mcp-fetch',
    command: 'npx',
    args: ['-y', '@anthropic/mcp-fetch'],
    official: true,
    stars: 1200,
  },
  {
    id: 'filesystem',
    name: 'Filesystem',
    category: 'Storage',
    description: 'Read and write local files',
    package: '@anthropic/mcp-filesystem',
    command: 'npx',
    args: ['-y', '@anthropic/mcp-filesystem', '--allow', '.'],
    official: true,
    stars: 800,
  },
  {
    id: 'slack',
    name: 'Slack',
    category: 'Communication',
    description: 'Send and receive Slack messages',
    package: '@anthropic/mcp-slack',
    command: 'npx',
    args: ['-y', '@anthropic/mcp-slack'],
    official: true,
    stars: 600,
    requiredSecrets: ['SLACK_BOT_TOKEN'],
  },
  // ... 더 많은 서버
];
```

**Frontend: MCP Marketplace UI**
```typescript
// src/components/Sidebar/MCPMarketplace.tsx

export const MCPMarketplace = memo(function MCPMarketplace() {
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState<string | null>(null);

  const filtered = MCP_CATALOG.filter(server => {
    const matchesSearch = server.name.toLowerCase().includes(search.toLowerCase());
    const matchesCategory = !category || server.category === category;
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="mcp-marketplace">
      <div className="flex gap-2 mb-4">
        <Input
          placeholder="Search MCP servers..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <Select value={category} onValueChange={setCategory}>
          <SelectTrigger className="w-32">
            <SelectValue placeholder="Category" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={null}>All</SelectItem>
            <SelectItem value="Web">Web</SelectItem>
            <SelectItem value="Storage">Storage</SelectItem>
            <SelectItem value="Communication">Communication</SelectItem>
            <SelectItem value="Database">Database</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="grid gap-2">
        {filtered.map(server => (
          <div key={server.id} className="server-card p-3 border rounded-lg">
            <div className="flex justify-between items-start">
              <div>
                <div className="font-medium flex items-center gap-2">
                  {server.name}
                  {server.official && (
                    <Badge variant="secondary">Official</Badge>
                  )}
                </div>
                <div className="text-xs text-muted-foreground">
                  {server.description}
                </div>
              </div>
              <Button
                size="sm"
                onClick={() => installServer(server)}
              >
                Install
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
});
```

---

### 5.2 디버그 모드

#### 5.2.1 목표
- Step-by-step 실행
- 각 노드에서 중단점 설정
- 중간 결과 실시간 확인

#### 5.2.2 구현 항목

**Backend: Debug Executor**
```python
# backend/app/core/executor.py (확장)

class DebugExecutor(WorkflowExecutor):
    """디버그 모드 실행기"""

    async def run_debug(
        self,
        workflow: Workflow,
        input: str,
        breakpoints: list[str] = None,
    ) -> AsyncIterator[DebugEvent]:
        """디버그 모드 실행 (스트리밍)"""
        breakpoints = breakpoints or []
        context = {"input": input}

        for node in self._topological_sort(workflow):
            # 중단점에서 대기
            if node.id in breakpoints:
                yield DebugEvent(
                    type="breakpoint",
                    node_id=node.id,
                    context=context,
                )
                # 클라이언트의 "continue" 신호 대기
                await self._wait_for_continue()

            # 노드 실행 시작
            yield DebugEvent(
                type="node_start",
                node_id=node.id,
                input=context,
            )

            # 노드 실행
            result = await self._execute_node(node, context, "full")
            context[node.id] = result.output

            # 노드 실행 완료
            yield DebugEvent(
                type="node_complete",
                node_id=node.id,
                output=result.output,
                duration_ms=result.duration_ms,
            )

        yield DebugEvent(type="complete", context=context)
```

**Frontend: Debug Controls**
```typescript
// src/components/ExecutionPanel/DebugControls.tsx

export const DebugControls = memo(function DebugControls({
  isDebugging,
  isPaused,
  currentNode,
  onContinue,
  onStepOver,
  onStop,
}) {
  if (!isDebugging) return null;

  return (
    <div className="debug-controls flex items-center gap-2 p-2 bg-amber-50 border-b">
      <Badge variant="outline" className="bg-amber-100">
        Debug Mode
      </Badge>

      {isPaused && (
        <>
          <span className="text-sm">
            Paused at: <strong>{currentNode}</strong>
          </span>
          <Button size="sm" onClick={onContinue}>
            <Play className="w-3 h-3 mr-1" />
            Continue
          </Button>
          <Button size="sm" variant="outline" onClick={onStepOver}>
            <StepForward className="w-3 h-3 mr-1" />
            Step
          </Button>
        </>
      )}

      <Button size="sm" variant="destructive" onClick={onStop}>
        <Square className="w-3 h-3 mr-1" />
        Stop
      </Button>
    </div>
  );
});
```

---

### 5.3 버전 관리

#### 5.3.1 목표
- 워크플로우 변경 히스토리 저장
- 이전 버전으로 롤백 가능
- 버전 간 비교

#### 5.3.2 구현 항목

**Backend: Version Store**
```python
# backend/app/core/version_store.py

class WorkflowVersionStore:
    """워크플로우 버전 관리"""

    async def save_version(
        self,
        workflow_id: str,
        workflow_data: dict,
        message: str = "",
    ) -> str:
        """새 버전 저장"""
        version_id = generate_id()
        version_number = await self._get_next_version_number(workflow_id)

        await self.db.execute(
            """INSERT INTO workflow_versions
               (id, workflow_id, version, data, message, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (version_id, workflow_id, version_number,
             json.dumps(workflow_data), message, datetime.now()),
        )

        return version_id

    async def list_versions(self, workflow_id: str) -> list[dict]:
        """버전 목록 조회"""
        rows = await self.db.fetchall(
            """SELECT id, version, message, created_at
               FROM workflow_versions
               WHERE workflow_id = ?
               ORDER BY version DESC""",
            (workflow_id,),
        )
        return [dict(row) for row in rows]

    async def restore_version(self, version_id: str) -> dict:
        """특정 버전으로 복원"""
        row = await self.db.fetchone(
            "SELECT data FROM workflow_versions WHERE id = ?",
            (version_id,),
        )
        return json.loads(row["data"])
```

---

## 6. Phase 3: 고급 기능 (1주+)

### 6.1 RBAC 권한 시스템

#### 6.1.1 역할 정의

| 역할 | 권한 |
|------|------|
| **Viewer** | 워크플로우 조회, 실행 로그 조회 |
| **Editor** | + 워크플로우 생성/수정 |
| **Operator** | + 워크플로우 실행, 스케줄 관리 |
| **Admin** | + 사용자 관리, 시크릿 관리, 설정 |

#### 6.1.2 구현 항목

```python
# backend/app/core/rbac.py

from enum import Enum
from functools import wraps

class Role(Enum):
    VIEWER = "viewer"
    EDITOR = "editor"
    OPERATOR = "operator"
    ADMIN = "admin"

ROLE_PERMISSIONS = {
    Role.VIEWER: ["workflow:read", "execution:read"],
    Role.EDITOR: ["workflow:read", "workflow:write", "execution:read"],
    Role.OPERATOR: ["workflow:read", "workflow:write", "execution:read",
                    "execution:write", "schedule:write"],
    Role.ADMIN: ["*"],
}

def require_permission(permission: str):
    """권한 체크 데코레이터"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, user: User, **kwargs):
            if not has_permission(user.role, permission):
                raise HTTPException(403, "Permission denied")
            return await func(*args, user=user, **kwargs)
        return wrapper
    return decorator
```

---

### 6.2 A/B 테스트

#### 6.2.1 목표
- 워크플로우 변형 간 성능 비교
- 트래픽 분할 설정
- 결과 통계 대시보드

#### 6.2.2 구현 항목

```python
# backend/app/core/ab_test.py

@dataclass
class ABTest:
    id: str
    name: str
    workflow_a_id: str
    workflow_b_id: str
    traffic_split: float  # 0.0 ~ 1.0 (A의 비율)
    metrics: list[str]  # ["duration", "success_rate", "output_quality"]
    status: str  # "running", "completed"

class ABTestRunner:
    """A/B 테스트 실행기"""

    async def run(self, test: ABTest, input: str) -> str:
        """A/B 테스트 실행 (트래픽 분할)"""
        import random

        if random.random() < test.traffic_split:
            workflow_id = test.workflow_a_id
            variant = "A"
        else:
            workflow_id = test.workflow_b_id
            variant = "B"

        workflow = await self.db.get_workflow(workflow_id)
        execution = await self.executor.run(workflow, input)

        # 결과 기록
        await self._record_result(test.id, variant, execution)

        return execution.id

    async def get_results(self, test_id: str) -> dict:
        """A/B 테스트 결과 통계"""
        return {
            "A": await self._get_variant_stats(test_id, "A"),
            "B": await self._get_variant_stats(test_id, "B"),
        }
```

---

### 6.3 분산 실행

#### 6.3.1 목표
- 다수의 워크플로우 동시 실행
- Worker 스케일링
- 장애 복구

#### 6.3.2 구현 항목

```python
# backend/app/core/distributed.py

from celery import Celery

celery_app = Celery(
    "workflow_engine",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
)

@celery_app.task(bind=True, max_retries=3)
def execute_workflow_task(
    self,
    workflow_id: str,
    input: str,
    mode: str = "full",
):
    """Celery Task로 워크플로우 실행"""
    try:
        executor = WorkflowExecutor(...)
        workflow = get_workflow(workflow_id)

        return asyncio.run(
            executor.run(workflow, input, mode)
        )
    except Exception as e:
        # 재시도
        self.retry(exc=e, countdown=60)
```

---

## 7. 기술 스택

### 7.1 Frontend

| 기술 | 용도 | 버전 |
|------|------|------|
| React | UI 프레임워크 | 18.x |
| TypeScript | 타입 안전성 | 5.x |
| React Flow | 워크플로우 캔버스 | 11.x |
| Zustand | 상태 관리 | 4.x |
| Tailwind CSS | 스타일링 | 3.x |
| shadcn/ui | UI 컴포넌트 | - |

### 7.2 Backend

| 기술 | 용도 | 버전 |
|------|------|------|
| Python | 런타임 | 3.11+ |
| FastAPI | API 프레임워크 | 0.100+ |
| SQLAlchemy | ORM | 2.x |
| APScheduler | 스케줄링 | 3.x |
| mcp | MCP 클라이언트 | 1.x |
| Celery | 분산 실행 (P3) | 5.x |

### 7.3 Storage

| 용도 | MVP | 확장 |
|------|-----|------|
| 메인 DB | SQLite | PostgreSQL |
| 캐시/큐 | - | Redis |
| 파일 저장 | 로컬 | S3 |

---

## 8. 데이터 모델

### 8.1 ERD

```
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│   workflows   │     │  executions   │     │   schedules   │
├───────────────┤     ├───────────────┤     ├───────────────┤
│ id            │────<│ workflow_id   │     │ id            │
│ name          │     │ id            │     │ workflow_id   │>───┐
│ description   │     │ status        │     │ type          │    │
│ nodes (JSON)  │     │ input         │     │ expression    │    │
│ edges (JSON)  │     │ output        │     │ input         │    │
│ created_at    │     │ node_logs     │     │ enabled       │    │
│ updated_at    │     │ started_at    │     │ created_at    │    │
└───────────────┘     │ completed_at  │     └───────────────┘    │
        │             └───────────────┘                          │
        │                                                        │
        └────────────────────────────────────────────────────────┘

┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│    secrets    │     │  mcp_servers  │     │    versions   │
├───────────────┤     ├───────────────┤     ├───────────────┤
│ name (PK)     │     │ id            │     │ id            │
│ value (enc)   │     │ name          │     │ workflow_id   │
│ key_version   │     │ command       │     │ version       │
│ created_at    │     │ args (JSON)   │     │ data (JSON)   │
│ updated_at    │     │ env (JSON)    │     │ message       │
└───────────────┘     │ status        │     │ created_at    │
                      │ last_connected│     └───────────────┘
                      │ tool_count    │
                      └───────────────┘

┌───────────────┐     ┌───────────────┐
│   webhooks    │     │  audit_logs   │
├───────────────┤     ├───────────────┤
│ id            │     │ id            │
│ workflow_id   │>────│ timestamp     │
│ secret        │     │ event_type    │
│ allowed_ips   │     │ user_id       │
│ input_mapping │     │ resource_type │
│ enabled       │     │ resource_id   │
│ created_at    │     │ action        │
│ last_called   │     │ details (JSON)│
└───────────────┘     │ ip_address    │
                      │ success       │
                      └───────────────┘
```

### 10.2 추가된 필드 (리뷰 결과 반영)

| 테이블 | 필드 | 타입 | 설명 |
|--------|------|------|------|
| `workflows` | `status` | enum | draft/published/archived |
| `workflows` | `owner_id` | string | RBAC용 (P3) |
| `executions` | `mode` | enum | full/mock/debug |
| `executions` | `trigger_type` | enum | manual/cron/webhook |
| `executions` | `trigger_id` | string | 스케줄/웹훅 참조 |
| `schedules` | `last_run_at` | datetime | 모니터링용 |
| `schedules` | `next_run_at` | datetime | UI 표시용 |
| `schedules` | `timezone` | string | 사용자 타임존 |
| `secrets` | `key_version` | integer | 키 로테이션용 |
| `mcp_servers` | `last_connected_at` | datetime | 헬스 모니터링 |
| `mcp_servers` | `tool_count` | integer | UI 성능용 캐시 |

---

## 9. API 설계

### 9.1 Workflows API

```
GET    /api/workflows              # 목록 조회
POST   /api/workflows              # 생성
GET    /api/workflows/:id          # 상세 조회
PUT    /api/workflows/:id          # 수정
DELETE /api/workflows/:id          # 삭제
POST   /api/workflows/:id/run      # 실행
GET    /api/workflows/:id/versions # 버전 목록
```

### 9.2 Executions API

```
GET    /api/executions             # 실행 목록
GET    /api/executions/:id         # 실행 상세
POST   /api/executions/:id/stop    # 실행 중단
POST   /api/executions/:id/resume  # 실행 재개
GET    /api/executions/:id/logs    # 로그 조회
WS     /api/executions/:id/stream  # 실시간 스트리밍
```

### 9.3 MCP API

```
GET    /api/mcp/servers            # 연결된 서버 목록
POST   /api/mcp/servers            # 서버 연결
DELETE /api/mcp/servers/:id        # 서버 연결 해제
GET    /api/mcp/servers/:id/tools  # Tool 목록
GET    /api/mcp/catalog            # 카탈로그 (마켓플레이스)
```

### 9.4 Schedules API

```
GET    /api/schedules              # 스케줄 목록
POST   /api/schedules              # 스케줄 생성
PUT    /api/schedules/:id          # 스케줄 수정
DELETE /api/schedules/:id          # 스케줄 삭제
POST   /api/schedules/:id/enable   # 활성화
POST   /api/schedules/:id/disable  # 비활성화
```

### 9.5 Secrets API

```
GET    /api/secrets                # 시크릿 이름 목록 (값 제외)
POST   /api/secrets                # 시크릿 생성
PUT    /api/secrets/:name          # 시크릿 수정
DELETE /api/secrets/:name          # 시크릿 삭제
```

### 11.6 Webhooks API (NEW)

```
GET    /api/webhooks               # Webhook 목록
POST   /api/webhooks               # Webhook 생성
GET    /api/webhooks/:id           # Webhook 상세
PUT    /api/webhooks/:id           # Webhook 수정
DELETE /api/webhooks/:id           # Webhook 삭제
POST   /api/webhooks/:id/rotate    # 시크릿 로테이션
```

### 11.7 Health API (NEW)

```
GET    /health/live                # 프로세스 생존 확인
GET    /health/ready               # 작업 수락 가능 여부 (DB, 스케줄러 상태)
GET    /health/mcp/:id             # 특정 MCP 서버 헬스
GET    /metrics                    # Prometheus 형식 메트릭
```

### 11.8 Validation API (NEW)

```
POST   /api/workflows/:id/validate # 실행 전 검증 (순환, 고아 노드 등)
POST   /api/workflows/import       # JSON 업로드
GET    /api/workflows/:id/export   # JSON 다운로드
```

### 11.9 External Webhook

```
POST   /webhook/:webhook_id        # 외부에서 호출 (HMAC 서명 필수)
```

---

## 12. 보안 고려사항

> 전문가 리뷰 결과 반영 (OWASP Top 10 기준)

### 12.1 시크릿 보안 (CRITICAL)

**필수 구현:**
- [x] 시크릿은 Fernet(AES-256)으로 암호화 저장
- [x] SECRET_KEY 환경변수 필수 (없으면 에러, 자동생성 금지)
- [x] 시크릿 이름 형식 검증: `^[A-Z][A-Z0-9_]{0,63}$`
- [ ] 키 로테이션 지원 (key_version 필드)
- [ ] 로그에 시크릿 값 마스킹 (PII 필터)
- [ ] API 응답에 시크릿 값 미포함

**키 로테이션 구현:**
```python
async def rotate_key(self, new_key: bytes) -> None:
    """모든 시크릿을 새 키로 재암호화"""
    # 기존 시크릿 복호화 → 새 키로 암호화 → key_version 증가
```

### 12.2 MCP 서버 보안 (CRITICAL)

**명령어 인젝션 방지:**
- [x] 명령어 허용목록: `npx`, `node`, `python`, `python3`, `uvx`
- [x] 위험 인자 차단: `--eval`, `-e`, `--exec`, `-c`
- [x] 경로 탐색 차단: `..`, 절대 경로

**SSRF 방지 (MCP Fetch):**
```python
BLOCKED_NETWORKS = [
    "10.0.0.0/8",       # 사설망
    "172.16.0.0/12",    # 사설망
    "192.168.0.0/16",   # 사설망
    "169.254.0.0/16",   # 링크로컬 (AWS 메타데이터)
]
```

**리소스 제한:**
- [ ] CPU 시간: 30초
- [ ] 메모리: 512MB
- [ ] 자식 프로세스: 10개

### 12.3 Webhook 보안 (CRITICAL)

**HMAC 서명 검증 (필수):**
```
X-Webhook-Signature: sha256=<hmac>
X-Webhook-Timestamp: <unix_timestamp>
```

**추가 보호:**
- [ ] IP 허용목록 지원
- [ ] 리플레이 공격 방지 (5분 타임스탬프 윈도우)
- [ ] Rate Limiting (100 req/min)

### 12.4 API 보안 (HIGH)

**인증 (Phase 0부터 구현):**
- [ ] JWT 토큰 검증
- [ ] API Key 지원 (시스템 연동용)
- [ ] 토큰 만료 처리

**Rate Limiting:**
| 엔드포인트 | 제한 |
|------------|------|
| `/webhook/:id` | 100 req/min |
| `/api/workflows/:id/run` | 10 req/min |
| `/api/*` | 1000 req/min |

**입력 검증 (Pydantic):**
- [ ] 모든 API 입력에 스키마 정의
- [ ] 최대 문자열 길이 제한
- [ ] JSON 깊이 제한

### 12.5 데이터 보안 (MEDIUM)

**PII 처리:**
```python
PATTERNS = {
    'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
    'api_key': r'(sk-|api[_-]?key[=:]\s*)[a-zA-Z0-9]{20,}',
}
```

**전송 암호화:**
- [ ] 프로덕션 HTTPS 필수
- [ ] HSTS 헤더 설정

### 12.6 감사 로깅 (MEDIUM)

**기록 대상:**
- [x] 워크플로우 실행 (user_id, workflow_id, status)
- [x] 시크릿 접근 (user_id, secret_name, action)
- [x] 인증 실패 (ip_address, reason)
- [ ] 관리자 작업 (user_id, action, target)

**로그 보관:**
- 기본 30일, 설정 가능 (7-365일)

### 12.7 OWASP Top 10 체크리스트

| 취약점 | 상태 | 대응 |
|--------|------|------|
| A01 접근제어 | ⚠️ HIGH | P0에서 JWT 인증 구현 |
| A02 암호화 실패 | ✅ 대응됨 | Fernet, 키 로테이션 |
| A03 인젝션 | ✅ 대응됨 | 명령어 허용목록, Pydantic |
| A05 보안설정오류 | ⚠️ MEDIUM | MCP 샌드박스 필요 |
| A07 인증 실패 | ⚠️ CRITICAL | Webhook HMAC 구현 |
| A10 SSRF | ⚠️ HIGH | 내부 네트워크 차단 |

---

## 부록 A: 마일스톤 체크리스트

### Phase -1 체크리스트 (Day 1-3) - 아키텍처 스파이크

**CRITICAL 버그 수정:**
- [ ] SecretStore `resolve()` async 버전으로 수정
- [ ] MCPServerConfig 명령어 허용목록 구현
- [ ] Webhook HMAC 서명 검증 추가
- [ ] SECRET_KEY 환경변수 필수화 (자동생성 제거)

**회복탄력성 통합:**
- [ ] 기존 AgentWeave CircuitBreaker 통합
- [ ] 기존 AgentWeave TimeoutManager 통합
- [ ] 기존 AgentWeave RetryPolicy 통합

**기반 설계:**
- [ ] ExecutionStatus enum 확장 (PAUSED, QUEUED, RETRYING, TIMED_OUT)
- [ ] WorkflowService 레이어 추가
- [ ] ExecutionRequest DTO 정의 (Celery 직렬화 대비)
- [ ] 노드 실행 전 체크포인트 저장 로직

### Phase 0 체크리스트 (Week 1-2)

**Backend:**
- [ ] FastAPI 프로젝트 셋업 (Alembic 마이그레이션 포함)
- [ ] SQLAlchemy ORM 모델 정의 (raw SQL 금지)
- [ ] MCP Manager 구현 (CircuitBreaker 통합)
- [ ] Workflow Executor 구현 (타임아웃 통합)
- [ ] Secret Store 구현 (async resolve)
- [ ] Execution Log 저장
- [ ] Health Check 엔드포인트 (`/health/live`, `/health/ready`)
- [ ] JWT 인증 미들웨어

**Frontend:**
- [ ] MCP Hub UI
- [ ] Run Dialog
- [ ] Execution Panel
- [ ] 에러 토스트 표시

**테스트:**
- [ ] API 통합 테스트
- [ ] CircuitBreaker 동작 테스트

### Phase 1 체크리스트 (Week 3-4)

**Backend:**
- [ ] APScheduler 통합 (타임존 지원)
- [ ] Cron 스케줄 API
- [ ] Webhook 엔드포인트 (HMAC 검증 포함)
- [ ] Mock 모드 구현
- [ ] State Store 구현 + Executor 통합
- [ ] Webhooks 테이블 마이그레이션

**Frontend:**
- [ ] Trigger Block
- [ ] Schedule 관리 UI (다음 실행 시간 표시)
- [ ] Cron 표현식 미리보기

**테스트:**
- [ ] 스케줄 실행 테스트
- [ ] 상태 재개 테스트

### Phase 2 체크리스트 (Week 5-6)

**Backend:**
- [ ] MCP 카탈로그 데이터 (20-30개 서버)
- [ ] Debug Executor 구현 (10분 비활동 타임아웃)
- [ ] WebSocket 스트리밍
- [ ] Version Store 구현

**Frontend:**
- [ ] MCP Marketplace UI
- [ ] Debug Controls
- [ ] Version History
- [ ] 워크플로우 내보내기/가져오기

**테스트:**
- [ ] E2E 테스트
- [ ] 동시 실행 테스트

### Phase 3 체크리스트 (Week 7+)

**Backend:**
- [ ] RBAC 구현
- [ ] Audit Logs 테이블 및 로깅
- [ ] A/B Test Runner (CSV 내보내기만)
- [ ] Celery 통합 (ExecutionRequest DTO 사용)
- [ ] Redis 설정
- [ ] PII 필터링 로거

**Frontend:**
- [ ] 사용자 관리 UI
- [ ] A/B 결과 조회 (기본)
- [ ] 감사 로그 조회

**테스트:**
- [ ] 성능 테스트 (20 동시 실행)
- [ ] 보안 테스트 (OWASP ZAP)

**문서:**
- [ ] API 문서 (OpenAPI)
- [ ] 운영 런북
- [ ] 복구 절차서

---

## 13. 시스템 제한값 (가드레일)

### 13.1 워크플로우 제한

| 항목 | 제한값 | 설명 |
|------|--------|------|
| 워크플로우당 최대 노드 | 100개 | 복잡도 및 UI 성능 |
| 최대 병렬 깊이 | 3단계 | 중첩된 병렬 블록 |
| 최대 시스템 프롬프트 길이 | 50,000자 | LLM 컨텍스트 윈도우 |
| 사용자당 최대 동시 실행 | 10개 | 리소스 보호 |

### 13.2 실행 제한

| 항목 | 제한값 | 설명 |
|------|--------|------|
| 워크플로우 총 실행 시간 | 5분 | 기본값, 설정 가능 |
| 노드당 실행 시간 | 60초 (Agent), 30초 (Tool) | 타입별 다름 |
| MCP Tool 호출 시간 | 30초 | 타임아웃 |
| 노드 출력 최대 크기 | 1MB | 메모리 보호 |

### 13.3 API 제한

| 엔드포인트 | Rate Limit | 설명 |
|------------|------------|------|
| `/api/workflows/:id/run` | 10 req/min | 실행 제한 |
| `/webhook/:id` | 100 req/min | 외부 호출 |
| `/api/*` (기타) | 1000 req/min | 일반 API |

### 13.4 저장소 제한

| 항목 | 제한값 | 설명 |
|------|--------|------|
| 시크릿 값 최대 크기 | 10KB | 암호화 효율 |
| 프로젝트당 최대 시크릿 | 100개 | 관리 용이성 |
| Webhook 페이로드 크기 | 10MB | 요청 본문 |
| 실행 로그 보관 기간 | 30일 | 기본값, 7-365일 설정 가능 |

---

## 14. 에러 코드 정의

### 14.1 표준 에러 응답 형식

```json
{
  "error": {
    "code": "WORKFLOW_NOT_FOUND",
    "message": "ID 'abc123'인 워크플로우를 찾을 수 없습니다",
    "details": { "workflow_id": "abc123" }
  }
}
```

### 14.2 워크플로우 에러

| 코드 | HTTP | 설명 |
|------|------|------|
| `WORKFLOW_NOT_FOUND` | 404 | 워크플로우 없음 |
| `WORKFLOW_VALIDATION_FAILED` | 400 | 검증 실패 (순환, 고아 노드 등) |
| `WORKFLOW_NODE_LIMIT_EXCEEDED` | 400 | 노드 100개 초과 |

### 14.3 실행 에러

| 코드 | HTTP | 설명 |
|------|------|------|
| `EXECUTION_NOT_FOUND` | 404 | 실행 기록 없음 |
| `EXECUTION_ALREADY_COMPLETED` | 400 | 이미 완료된 실행 재개 시도 |
| `EXECUTION_TIMEOUT` | 408 | 실행 시간 초과 |
| `EXECUTION_CANCELLED` | 499 | 사용자에 의해 취소됨 |

### 14.4 MCP 에러

| 코드 | HTTP | 설명 |
|------|------|------|
| `MCP_SERVER_NOT_CONNECTED` | 503 | MCP 서버 미연결 |
| `MCP_TOOL_NOT_FOUND` | 404 | Tool 없음 |
| `MCP_TOOL_EXECUTION_FAILED` | 500 | Tool 실행 실패 |
| `MCP_CIRCUIT_OPEN` | 503 | Circuit Breaker 열림 |
| `MCP_COMMAND_NOT_ALLOWED` | 403 | 허용 안된 명령어 |

### 14.5 시크릿 에러

| 코드 | HTTP | 설명 |
|------|------|------|
| `SECRET_NOT_FOUND` | 404 | 시크릿 없음 |
| `SECRET_NAME_INVALID` | 400 | 잘못된 시크릿 이름 형식 |
| `SECRET_ACCESS_DENIED` | 403 | 시크릿 접근 권한 없음 |

### 14.6 인증/인가 에러

| 코드 | HTTP | 설명 |
|------|------|------|
| `UNAUTHORIZED` | 401 | 인증 필요 |
| `FORBIDDEN` | 403 | 권한 부족 |
| `RATE_LIMIT_EXCEEDED` | 429 | 요청 제한 초과 |
| `WEBHOOK_SIGNATURE_INVALID` | 401 | Webhook 서명 검증 실패 |

### 14.7 스케줄 에러

| 코드 | HTTP | 설명 |
|------|------|------|
| `SCHEDULE_NOT_FOUND` | 404 | 스케줄 없음 |
| `SCHEDULE_INVALID_CRON` | 400 | 잘못된 Cron 표현식 |
| `SCHEDULE_CONFLICT` | 409 | 중복 스케줄 |

---

## 부록 B: 수락 기준 (Acceptance Criteria)

### B.1 Phase 0 수락 기준

1. **MCP 서버 연결**
   - 사용자가 `@anthropic/mcp-fetch`에 연결하면 5초 내에 `fetch` Tool이 사이드바에 표시됨
   - 연결 실패 시 에러 토스트와 재시도 버튼 표시

2. **워크플로우 실행**
   - 3개 노드 순차 워크플로우(Agent → MCP Tool → Agent)가 완료됨
   - 각 노드의 소요 시간과 상태 아이콘이 Execution Panel에 표시됨

3. **시크릿 관리**
   - 사용자가 `API_KEY` 시크릿 생성 후, MCP Tool 속성에서 `${API_KEY}` 선택 가능
   - 실행 시 값이 치환되며 평문 로깅 안됨

### B.2 Phase 1 수락 기준

4. **Cron 스케줄**
   - `0 9 * * *` 설정 시 UI에 다음 실행 시간 표시
   - 예약 시간 1분 이내에 워크플로우 실행됨

5. **Mock 모드**
   - Mock 모드 실행 시 네트워크 요청 없음 (브라우저 DevTools로 확인)
   - 모든 노드에 'mock' 배지 표시, 미리 정의된 값 반환

6. **상태 재개**
   - 5개 노드 워크플로우에서 노드 3에서 Stop 클릭
   - Resume 클릭 시 노드 3부터 이전 컨텍스트로 실행 재개

---

## 부록 C: 감사 로깅 스키마

```sql
CREATE TABLE audit_logs (
    id TEXT PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT NOT NULL,  -- workflow_execute, secret_access, etc.
    user_id TEXT,
    resource_type TEXT,        -- workflow, secret, schedule
    resource_id TEXT,
    action TEXT,
    details JSON,              -- 추가 컨텍스트 (PII 제거됨)
    ip_address TEXT,
    user_agent TEXT,
    success BOOLEAN
);

CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_event ON audit_logs(event_type);
```

---

## 부록 D: Webhooks 테이블 스키마

```sql
CREATE TABLE webhooks (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL REFERENCES workflows(id),
    secret TEXT NOT NULL,      -- HMAC 서명용 시크릿
    allowed_ips TEXT,          -- 쉼표로 구분된 IP 목록 (NULL = 모두 허용)
    input_mapping JSON,        -- 요청 데이터를 워크플로우 입력으로 매핑
    enabled BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_called_at DATETIME
);

CREATE INDEX idx_webhooks_workflow ON webhooks(workflow_id);
```

---

*최종 업데이트: 2025-02-05 (전문가 패널 리뷰 반영)*
