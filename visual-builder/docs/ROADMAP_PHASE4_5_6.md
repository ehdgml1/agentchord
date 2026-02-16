# AgentWeave Visual Builder - Phase 4/5/6 구현 로드맵

## 현재 상태 요약

**Phase 0-3 완료 상황:**
- 56개 API 엔드포인트 구현 (대부분 스텁 상태)
- 193+ 테스트 작성
- 핵심 데이터 모델 및 Repository 계층 완성
- WorkflowExecutor, MCPManager, SecretStore 등 core 모듈 구현

**현재 주요 문제 (Critical Blockers):**
1. `PlaceholderExecutor()` 사용 중 (`backend/app/main.py` line 53) - WorkflowExecutor 미연결
2. MCP 세션 수명 관리 버그 (`backend/app/core/mcp_manager.py` line 238) - context manager 조기 종료
3. Workflow CRUD API 전부 미구현 (`backend/app/api/workflows.py` - 501/404 반환)
4. eval() 사용으로 보안 취약점 (`backend/app/core/executor.py` line 518)

**수행해야 할 작업:**
- Phase 4: 실행 엔진 완성 (ExecutorEngine, MCP 연결, API 구현)
- Phase 5: 프론트엔드 UI 완성 (Properties, 시각화, 템플릿)
- Phase 6: 프로덕션 인프라 (Docker, PostgreSQL, CI/CD, 모니터링)

---

## Phase 4: 실행 엔진 완성 (Critical Path)

### 4.1 PlaceholderExecutor → WorkflowExecutor 교체

**파일**: `backend/app/main.py`
**우선순위**: **P0** (모든 다른 작업의 선행조건)
**예상 작업량**: 중

#### 현재 상태
```python
# backend/app/main.py line 53 - BROKEN
executor = PlaceholderExecutor()
```

WorkflowExecutor는 이미 `backend/app/core/executor.py`에 완전히 구현되어 있으나, 실제로 main.py에서 인스턴스화되지 않음.

#### 구현 내용

1. **MCPManager 싱글턴 초기화**
   - `from app.core.mcp_manager import MCPManager`
   - `app.state.mcp_manager = MCPManager()`

2. **SecretStore 초기화**
   - `from app.core.secret_store import SecretStore`
   - 개발 모드에서는 메모리 기반, 프로덕션에서는 암호화된 스토리지
   - `SECRET_KEY` 환경변수 폴백 사용

3. **ExecutionStateStore 초기화**
   - `from app.core.executor import ExecutionStateStore`
   - SQLAlchemy 어댑터 작성 (SQLite/PostgreSQL 지원)
   - `app.state.state_store = ExecutionStateStore(db_session_factory)`

4. **WorkflowExecutor 생성**
   ```python
   from app.core.executor import WorkflowExecutor

   executor = WorkflowExecutor(
       mcp_manager=app.state.mcp_manager,
       secret_store=secret_store,
       state_store=app.state.state_store,
   )
   app.state.executor = executor
   ```

5. **executions.py 수정**
   - `from fastapi import request` 사용 → `request.app.state.executor`로 교체
   - 또는 FastAPI Depends 패턴으로 get_executor() 의존성 생성

#### 예상 결과
- `/api/executions` POST 호출 시 실제 WorkflowExecutor 사용
- MCP 도구 실행, 재시도, 타임아웃 등 실제 동작 가능

---

### 4.2 MCP 세션 수명 관리 수정

**파일**: `backend/app/core/mcp_manager.py`
**우선순위**: **P0**
**예상 작업량**: 소

#### 현재 버그

```python
# backend/app/core/mcp_manager.py line 238 - BUG
async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        # ... tools 로드 ...
        self._sessions[config.id] = session  # ← context manager 종료 후 세션이 닫힘!
```

**문제점**:
- `async with` context manager가 블록을 빠져나가면서 session이 자동으로 닫힘
- 닫힌 세션을 `self._sessions`에 저장하여 재사용 불가능
- 이후 `execute_tool()` 호출 시 "Client not connected" 에러 발생

#### 수정 방향

1. **Context Manager 래핑**
   ```python
   @dataclass
   class SessionContext:
       """MCP 세션 래퍼."""
       server_id: str
       read: Any
       write: Any
       session: ClientSession
       _client_context: Any  # stdio_client context
       _session_context: Any  # ClientSession context
   ```

2. **수동 Lifecycle 관리**
   ```python
   async def connect(self, config: MCPServerConfig) -> None:
       from mcp import ClientSession, StdioServerParameters
       from mcp.client.stdio import stdio_client

       server_params = StdioServerParameters(...)

       # __aenter__() 호출 (context 진입)
       client_context = stdio_client(server_params)
       read, write = await client_context.__aenter__()

       # SessionContext 생성
       session_context = ClientSession(read, write)
       session = await session_context.__aenter__()

       await session.initialize()

       # Context 저장 (나중에 disconnect() 호출 시 __aexit__())
       self._contexts[config.id] = {
           "client": client_context,
           "read": read,
           "write": write,
           "session": session_context,
       }
       self._sessions[config.id] = session
   ```

3. **Disconnect 메서드 구현**
   ```python
   async def disconnect(self, server_id: str) -> None:
       """MCP 서버 연결 해제."""
       if server_id not in self._contexts:
           return

       ctx = self._contexts[server_id]
       try:
           # Context manager 정리 (역순)
           await ctx["session"].__aexit__(None, None, None)
           await ctx["client"].__aexit__(None, None, None)
       finally:
           del self._sessions[server_id]
           del self._contexts[server_id]
   ```

4. **종료 시 정리**
   - main.py lifespan의 shutdown 블록에서 모든 세션 disconnect
   ```python
   # Shutdown: Cleanup MCP sessions
   if hasattr(app.state, "mcp_manager"):
       for server_id in list(app.state.mcp_manager._sessions.keys()):
           await app.state.mcp_manager.disconnect(server_id)
   ```

#### 검증
- MCP 서버 연결 후 도구 호출이 정상 작동
- 여러 MCP 서버 동시 연결 가능
- 서버 재연결 시 이전 세션이 정리됨

---

### 4.3 Workflow CRUD API 연결

**파일**: `backend/app/api/workflows.py`
**우선순위**: **P0** (Phase 4.1 이후)
**예상 작업량**: 대

#### 현재 상태
모든 엔드포인트가 TODO 스텁:
- `list_workflows()` → 빈 배열 반환
- `create_workflow()` → 501 NOT_IMPLEMENTED
- `get_workflow()` → 404 NOT_FOUND
- 등등

WorkflowRepository, WorkflowService는 구현 완료. Model(SQLAlchemy) ↔ DTO(dataclass) 변환만 필요.

#### 구현 내용

**1. 의존성 주입 설정**
```python
from fastapi import Depends
from app.db.database import get_session
from app.repositories.workflow_repo import WorkflowRepository
from app.services.workflow_service import WorkflowService

async def get_workflow_service(session = Depends(get_session)):
    return WorkflowService(WorkflowRepository(session))
```

**2. list_workflows() - 워크플로우 목록 조회**
```python
@router.get("", response_model=WorkflowListResponse)
async def list_workflows(
    user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    service: WorkflowService = Depends(get_workflow_service),
):
    # Repository에서 사용자의 워크플로우 조회
    workflows, total = await service.list_workflows(
        user_id=user.id,
        limit=limit,
        offset=offset,
    )

    # SQLAlchemy Model → DTO 변환
    return WorkflowListResponse(
        workflows=[workflow_model_to_dto(w) for w in workflows],
        total=total,
        limit=limit,
        offset=offset,
    )
```

**3. create_workflow() - 새 워크플로우 생성**
```python
@router.post("", response_model=WorkflowResponse, status_code=201)
async def create_workflow(
    workflow: WorkflowCreate,
    user: Annotated[User, Depends(get_current_user)],
    service: WorkflowService = Depends(get_workflow_service),
):
    import json

    # DTO → Model 변환
    model = WorkflowModel(
        id=generate_id(),
        user_id=user.id,
        name=workflow.name,
        description=workflow.description or "",
        nodes=json.dumps(workflow.nodes),  # JSON 직렬화
        edges=json.dumps(workflow.edges),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    # Repository에 저장
    created = await service.create_workflow(model)

    return workflow_model_to_dto(created)
```

**4. get_workflow() - 단일 워크플로우 조회**
```python
@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str,
    user: Annotated[User, Depends(get_current_user)],
    service: WorkflowService = Depends(get_workflow_service),
):
    workflow = await service.get_workflow(workflow_id, user.id)

    if not workflow:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "NOT_FOUND",
                    "message": f"Workflow '{workflow_id}' not found",
                }
            },
        )

    return workflow_model_to_dto(workflow)
```

**5. update_workflow() - 워크플로우 업데이트**
```python
@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: str,
    workflow_update: WorkflowUpdate,
    user: Annotated[User, Depends(get_current_user)],
    service: WorkflowService = Depends(get_workflow_service),
):
    import json

    # 접근 권한 확인
    existing = await service.get_workflow(workflow_id, user.id)
    if not existing:
        raise HTTPException(status_code=404)

    # 부분 업데이트
    if workflow_update.name is not None:
        existing.name = workflow_update.name
    if workflow_update.description is not None:
        existing.description = workflow_update.description
    if workflow_update.nodes is not None:
        existing.nodes = json.dumps(workflow_update.nodes)
    if workflow_update.edges is not None:
        existing.edges = json.dumps(workflow_update.edges)

    existing.updated_at = datetime.now()

    updated = await service.update_workflow(existing)
    return workflow_model_to_dto(updated)
```

**6. delete_workflow() - 워크플로우 삭제**
```python
@router.delete("/{workflow_id}", status_code=204)
async def delete_workflow(
    workflow_id: str,
    user: Annotated[User, Depends(get_current_user)],
    service: WorkflowService = Depends(get_workflow_service),
):
    workflow = await service.get_workflow(workflow_id, user.id)
    if not workflow:
        raise HTTPException(status_code=404)

    # 관련 executions/schedules도 cascade 삭제 고려
    await service.delete_workflow(workflow_id)
```

**7. run_workflow() - 워크플로우 실행**
```python
@router.post("/{workflow_id}/run", response_model=WorkflowRunResponse)
async def run_workflow(
    workflow_id: str,
    run_request: WorkflowRunRequest,
    user: Annotated[User, Depends(get_current_user)],
    executor: WorkflowExecutor = Depends(get_executor),
    service: WorkflowService = Depends(get_workflow_service),
):
    import json

    # 워크플로우 조회
    workflow_model = await service.get_workflow(workflow_id, user.id)
    if not workflow_model:
        raise HTTPException(status_code=404)

    # Model → dataclass 변환
    workflow = model_to_dataclass_workflow(workflow_model)

    # WorkflowExecutor 실행
    execution = await executor.run(
        workflow=workflow,
        input=run_request.input,
        mode=run_request.mode or "full",
        trigger_type="manual",
    )

    # 실행 결과 저장
    execution_model = ExecutionModel(
        id=execution.id,
        workflow_id=workflow_id,
        user_id=user.id,
        status=execution.status.value,
        mode=execution.mode,
        input=execution.input,
        output=json.dumps(execution.output),
        error=execution.error,
        started_at=execution.started_at,
        completed_at=execution.completed_at,
    )
    await service.save_execution(execution_model)

    return WorkflowRunResponse(
        execution_id=execution.id,
        status=execution.status.value,
        output=execution.output,
    )
```

**8. validate_workflow() - 워크플로우 검증**
```python
@router.post("/{workflow_id}/validate", response_model=WorkflowValidateResponse)
async def validate_workflow(
    workflow_id: str,
    user: Annotated[User, Depends(get_current_user)],
    executor: WorkflowExecutor = Depends(get_executor),
    service: WorkflowService = Depends(get_workflow_service),
):
    workflow_model = await service.get_workflow(workflow_id, user.id)
    if not workflow_model:
        raise HTTPException(status_code=404)

    workflow = model_to_dataclass_workflow(workflow_model)

    try:
        executor._validate_workflow(workflow)
        return WorkflowValidateResponse(
            valid=True,
            errors=[],
        )
    except Exception as e:
        return WorkflowValidateResponse(
            valid=False,
            errors=[str(e)],
        )
```

#### 변환 유틸리티 함수

**Model → DTO 변환**
```python
def workflow_model_to_dto(model: WorkflowModel) -> WorkflowResponse:
    """SQLAlchemy Model을 Response DTO로 변환."""
    import json

    return WorkflowResponse(
        id=model.id,
        name=model.name,
        description=model.description,
        nodes=json.loads(model.nodes),
        edges=json.loads(model.edges),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
```

**Model → dataclass 변환**
```python
def model_to_dataclass_workflow(model: WorkflowModel) -> Workflow:
    """SQLAlchemy Model을 executor용 dataclass로 변환."""
    import json
    from app.core.executor import Workflow, WorkflowNode, WorkflowEdge

    nodes_data = json.loads(model.nodes)
    edges_data = json.loads(model.edges)

    nodes = [
        WorkflowNode(
            id=n["id"],
            type=n["type"],
            data=n.get("data", {}),
            position=n.get("position"),
        )
        for n in nodes_data
    ]

    edges = [
        WorkflowEdge(
            id=e["id"],
            source=e["source"],
            target=e["target"],
            source_handle=e.get("sourceHandle"),
            target_handle=e.get("targetHandle"),
        )
        for e in edges_data
    ]

    return Workflow(
        id=model.id,
        name=model.name,
        nodes=nodes,
        edges=edges,
        description=model.description,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
```

#### 검증
- `POST /api/workflows` - 새 워크플로우 생성
- `GET /api/workflows` - 목록 조회
- `GET /api/workflows/{id}` - 단일 조회
- `PUT /api/workflows/{id}` - 업데이트
- `DELETE /api/workflows/{id}` - 삭제
- `POST /api/workflows/{id}/run` - 실행
- `POST /api/workflows/{id}/validate` - 검증

---

### 4.4 병렬 실행 엔진

**파일**: `backend/app/core/executor.py`
**우선순위**: **P1** (Phase 4.1 이후)
**예상 작업량**: 대

#### 현재 상태
- `run()` 메서드가 순차 for 루프로만 실행 (line 290)
- parallel 노드 타입이 `_execute_node`에서 None 반환 (미구현)

#### 구현 내용

**1. parallel 노드 타입 감지**
```python
async def _execute_node(
    self,
    node: WorkflowNode,
    context: dict[str, Any],
    mode: str,
) -> Any:
    """노드 실행 (타입별 분기)."""

    if node.type == "parallel":
        return await self._execute_parallel(node, context, mode)
    elif node.type == "condition":
        return await self._execute_condition(node, context, mode)
    # ... 기타 타입 ...
```

**2. 병렬 브랜치 식별 알고리즘**
```python
def _find_parallel_branches(
    self,
    workflow: Workflow,
    parallel_node_id: str,
) -> list[list[WorkflowNode]]:
    """병렬 노드의 아웃고잉 엣지로 시작하는 브랜치들을 식별."""

    branches = []

    # 병렬 노드의 아웃고잉 엣지 찾기
    outgoing_edges = [
        e for e in workflow.edges
        if e.source == parallel_node_id
    ]

    # 각 엣지별로 브랜치 추적
    for edge in outgoing_edges:
        branch = []
        current_node_id = edge.target
        visited = set()

        # 다음 공통 노드까지 브랜치 내 노드들 수집
        while current_node_id and current_node_id not in visited:
            visited.add(current_node_id)

            # 노드 찾기
            node = next(
                (n for n in workflow.nodes if n.id == current_node_id),
                None
            )
            if not node:
                break

            branch.append(node)

            # 다음 노드로 이동
            next_edges = [
                e for e in workflow.edges
                if e.source == current_node_id
                and len([e2 for e2 in workflow.edges if e2.target == e.target]) == 1
            ]

            if not next_edges:
                break

            current_node_id = next_edges[0].target

        if branch:
            branches.append(branch)

    return branches
```

**3. 병렬 실행 구현**
```python
async def _execute_parallel(
    self,
    node: WorkflowNode,
    context: dict[str, Any],
    mode: str,
) -> dict[str, Any]:
    """병렬 노드 실행.

    여러 브랜치를 동시에 실행하고 결과를 병합.
    """

    # 병렬 브랜치 식별 (추후 구현)
    # branches = self._find_parallel_branches(workflow, node.id)

    # 임시: node.data["branches"]에서 브랜치 정보 읽음
    branches_config = node.data.get("branches", [])

    parallel_tasks = []

    for branch_config in branches_config:
        # 각 브랜치별 context 복사
        branch_context = context.copy()

        # 브랜치 실행 (코루틴)
        async def execute_branch(config, ctx):
            # config는 {"nodeIds": ["node1", "node2"]} 형태
            results = {}
            for node_id in config.get("nodeIds", []):
                # 해당 노드 실행
                node = next((n for n in workflow.nodes if n.id == node_id), None)
                if node:
                    result = await self._execute_node(node, ctx, mode)
                    results[node_id] = result
                    ctx[node_id] = result
            return results

        task = execute_branch(branch_config, branch_context)
        parallel_tasks.append(task)

    # asyncio.gather()로 모든 브랜치 동시 실행
    try:
        branch_results = await asyncio.gather(*parallel_tasks)
    except asyncio.CancelledError:
        # 한 브랜치 취소 시 다른 브랜치도 취소
        for task in parallel_tasks:
            task.cancel()
        raise
    except Exception as e:
        # 에러 발생 시 다른 브랜치 취소 (옵션)
        for task in parallel_tasks:
            task.cancel()
        raise

    # 모든 브랜치 결과를 context에 병합
    merged_context = context.copy()
    for i, results in enumerate(branch_results):
        for node_id, result in results.items():
            merged_context[f"branch_{i}_{node_id}"] = result

    return {
        "branch_results": branch_results,
        "merged_context": merged_context,
    }
```

**4. 브랜치 조인점 처리**
```python
async def _execute_join(
    self,
    node: WorkflowNode,
    context: dict[str, Any],
    mode: str,
) -> Any:
    """Join 노드 실행 - 병렬 브랜치 결과 통합."""

    # Join 전략 (node.data.strategy에서 읽음)
    strategy = node.data.get("strategy", "collect")  # collect, merge, first, last

    # 이전 병렬 브랜치 결과 추출
    branch_results = context.get("parallel_results", [])

    if strategy == "collect":
        # 모든 결과를 배열로 수집
        return branch_results
    elif strategy == "merge":
        # 모든 결과를 단일 딕셔너리로 병합
        merged = {}
        for result in branch_results:
            if isinstance(result, dict):
                merged.update(result)
        return merged
    elif strategy == "first":
        # 첫 번째 결과 반환
        return branch_results[0] if branch_results else None
    elif strategy == "last":
        # 마지막 결과 반환
        return branch_results[-1] if branch_results else None
    else:
        return branch_results
```

#### 검증
- 2개 이상의 병렬 브랜치 동시 실행
- 브랜치 간 데이터 독립성 확인
- 한 브랜치 실패 시 다른 브랜치 취소
- 병렬 실행 성능 개선 측정

---

### 4.5 조건 분기 엔진

**파일**: `backend/app/core/executor.py`
**우선순위**: **P1** (Phase 4.1 이후)
**예상 작업량**: 중

#### 현재 문제

1. **보안 취약점**: `eval()` 사용 (line 518)
   ```python
   return bool(eval(condition, {"__builtins__": {}}, local_vars))
   ```
   - 코드 인젝션 위험 (제한된 __builtins__도 우회 가능)
   - 복잡한 Python 표현식 실행 가능

2. **경로 분기 미지원**
   - true/false 모두 실행됨
   - sourceHandle 기반 라우팅 미구현

#### 구현 내용

**1. simpleeval 라이브러리 설치**
```bash
pip install simpleeval
```

**2. 조건 평가 함수 구현 (보안)**
```python
from simpleeval import simple_eval, EvalWithCompoundTypes, DEFAULT_OPERATORS, DEFAULT_FUNCTIONS

def _evaluate_condition(
    self,
    condition: str,
    context: dict[str, Any],
) -> bool:
    """조건식을 안전하게 평가.

    Args:
        condition: 조건 표현식 (예: "input.length > 5 and status == 'active'")
        context: 변수 맥락

    Returns:
        평가 결과 (True/False)

    Raises:
        ValueError: 평가 오류
    """

    # 안전한 함수 목록 (화이트리스트)
    safe_functions = {
        "len": len,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict,
        "min": min,
        "max": max,
        "sum": sum,
        "abs": abs,
    }

    try:
        evaluator = EvalWithCompoundTypes(
            names=context,
            functions=safe_functions,
            operators=DEFAULT_OPERATORS,
        )
        result = evaluator.eval(condition)
        return bool(result)
    except Exception as e:
        raise ValueError(f"Failed to evaluate condition '{condition}': {e}")
```

**3. 조건 노드 실행 (경로 분기)**
```python
async def _execute_condition(
    self,
    node: WorkflowNode,
    context: dict[str, Any],
    mode: str,
    workflow: Workflow,
) -> Any:
    """조건 노드 실행 - true/false 경로로 분기.

    Returns:
        조건 평가 결과
    """

    condition = node.data.get("condition", "true")

    # 조건 평가
    try:
        result = self._evaluate_condition(condition, context)
    except ValueError as e:
        raise WorkflowValidationError(f"Condition evaluation failed: {e}")

    # 결과 저장 (이후 경로 선택에 사용)
    context[f"{node.id}_result"] = result

    return result
```

**4. 엣지 필터링 (sourceHandle 기반)**
```python
def _get_next_nodes(
    self,
    current_node: WorkflowNode,
    workflow: Workflow,
    context: dict[str, Any],
) -> list[WorkflowNode]:
    """현재 노드의 다음 노드들을 결정.

    조건/parallel 노드의 경우 sourceHandle 기반 필터링.
    """

    next_node_ids = []

    # 현재 노드의 아웃고잉 엣지
    outgoing_edges = [e for e in workflow.edges if e.source == current_node.id]

    for edge in outgoing_edges:
        # 조건 노드인 경우: sourceHandle이 "true" 또는 "false"
        if current_node.type == "condition":
            condition_result = context.get(f"{current_node.id}_result", False)

            # sourceHandle이 조건 결과와 일치하는지 확인
            if edge.source_handle == "true" and condition_result:
                next_node_ids.append(edge.target)
            elif edge.source_handle == "false" and not condition_result:
                next_node_ids.append(edge.target)
        else:
            # 일반 노드: 모든 아웃고잉 엣지
            next_node_ids.append(edge.target)

    # ID로 노드 찾기
    next_nodes = [
        n for n in workflow.nodes if n.id in next_node_ids
    ]

    return next_nodes
```

**5. 메인 실행 루프 수정**
```python
# 기존: 순차 for 루프
# for node in ordered_nodes[start_index:]:

# 새로운: 동적 경로 결정
current_node_id = ordered_nodes[start_index].id if start_index < len(ordered_nodes) else None

while current_node_id:
    current_node = next(
        (n for n in workflow.nodes if n.id == current_node_id),
        None
    )
    if not current_node:
        break

    # 노드 실행
    node_result = await self._execute_node_with_retry(
        execution.id, current_node, ctx, mode
    )
    execution.node_executions.append(node_result)

    # 결과 context에 저장
    ctx[current_node.id] = node_result.output

    if node_result.status != ExecutionStatus.COMPLETED:
        break

    # 다음 노드 결정
    next_nodes = self._get_next_nodes(current_node, workflow, ctx)
    current_node_id = next_nodes[0].id if next_nodes else None
```

#### 검증
- 조건식 평가 (>, <, ==, and, or 등)
- true 경로 선택 시 true 엣지만 실행
- false 경로 선택 시 false 엣지만 실행
- 복잡한 조건식 (변수 참조, 함수 호출)
- 코드 인젝션 방지

---

### 4.6 피드백 루프 지원

**파일**: `backend/app/core/executor.py`
**우선순위**: **P2** (Phase 4.5 이후)
**예상 작업량**: 대

#### 현재 문제
- `_has_cycle()` 메서드가 모든 사이클 거부 (line 569-608)
- `feedback_loop` 노드 타입 미처리

#### 구현 내용

**1. 사이클 검증 수정**
```python
def _has_cycle(
    self,
    workflow: Workflow,
    allow_feedback_loops: bool = True,
) -> bool:
    """워크플로우의 사이클 감지.

    Args:
        workflow: 워크플로우 정의
        allow_feedback_loops: feedback_loop 노드를 통한 사이클 허용 여부

    Returns:
        사이클 있음 여부
    """

    # 각 노드의 상태: 0=unvisited, 1=visiting, 2=visited
    state = {n.id: 0 for n in workflow.nodes}

    def dfs_has_cycle(node_id: str) -> bool:
        """DFS로 사이클 탐지."""
        state[node_id] = 1  # visiting

        # 아웃고잉 엣지
        edges = [e for e in workflow.edges if e.source == node_id]

        for edge in edges:
            target_node = next(
                (n for n in workflow.nodes if n.id == edge.target),
                None
            )
            if not target_node:
                continue

            # feedback_loop을 통한 백엣지는 허용
            if allow_feedback_loops:
                source_node = next(
                    (n for n in workflow.nodes if n.id == node_id),
                    None
                )
                if source_node and source_node.type == "feedback_loop":
                    # feedback_loop → 다음 노드는 OK
                    continue

            if state[edge.target] == 1:
                # 백엣지: 사이클 감지
                return True
            elif state[edge.target] == 0:
                if dfs_has_cycle(edge.target):
                    return True

        state[node_id] = 2  # visited
        return False

    # 모든 시작 노드에서 DFS
    start_nodes = self._get_start_nodes(workflow)
    for node in start_nodes:
        if dfs_has_cycle(node.id):
            return True

    return False
```

**2. feedback_loop 노드 타입 처리**
```python
async def _execute_feedback_loop(
    self,
    node: WorkflowNode,
    context: dict[str, Any],
    mode: str,
    workflow: Workflow,
) -> Any:
    """피드백 루프 노드 실행.

    루프 본문을 반복 실행하고 탈출 조건을 평가.
    """

    # 루프 설정
    max_iterations = node.data.get("maxIterations", 10)
    exit_condition = node.data.get("exitCondition", "false")
    loop_body_nodes = node.data.get("loopBodyNodeIds", [])

    # 반복 카운트 추적
    iteration = 0
    loop_context = context.copy()
    loop_context[f"{node.id}_iteration"] = iteration

    while iteration < max_iterations:
        # 탈출 조건 평가
        try:
            should_exit = self._evaluate_condition(exit_condition, loop_context)
        except ValueError:
            should_exit = False

        if should_exit:
            break

        # 루프 본문 실행
        for loop_node_id in loop_body_nodes:
            loop_node = next(
                (n for n in workflow.nodes if n.id == loop_node_id),
                None
            )
            if not loop_node:
                continue

            result = await self._execute_node_with_retry(
                context.get("execution_id"),
                loop_node,
                loop_context,
                mode,
            )

            loop_context[loop_node_id] = result.output

            if result.status != ExecutionStatus.COMPLETED:
                return {
                    "status": "failed",
                    "error": result.error,
                    "iterations": iteration,
                }

        iteration += 1
        loop_context[f"{node.id}_iteration"] = iteration

    # 루프 종료
    return {
        "status": "completed",
        "iterations": iteration,
        "final_context": loop_context,
    }
```

**3. 루프 상태 추적**
```python
@dataclass
class LoopExecutionState:
    """루프 실행 상태."""
    node_id: str
    iteration: int
    context: dict[str, Any]
    last_execution_time: datetime

    # 저장소에 직렬화 가능
    def to_dict(self) -> dict[str, Any]:
        import json
        return {
            "node_id": self.node_id,
            "iteration": self.iteration,
            "context": json.dumps(self.context),
            "last_execution_time": self.last_execution_time.isoformat(),
        }
```

**4. 루프 체크포인트**
```python
async def _save_loop_checkpoint(
    self,
    execution_id: str,
    loop_state: LoopExecutionState,
) -> None:
    """루프 실행 상태 저장."""
    await self.state_store.save_state(
        execution_id,
        f"loop_{loop_state.node_id}",
        loop_state.to_dict(),
    )
```

#### 검증
- feedback_loop 노드 생성 및 실행
- 탈출 조건 평가 (입력값 기반)
- 최대 반복 횟수 제한
- 루프 컨텍스트 유지
- 중단 및 재개 가능

---

## Phase 5: 프론트엔드 완성

### 5.1 조건/병렬/피드백 Properties UI

**파일**: `src/components/nodes/`, `src/components/Properties/`
**우선순위**: **P1** (Phase 4.4-4.6 이후)
**예상 작업량**: 중

#### 구현 내용

**ConditionNode Properties Panel**
```tsx
// src/components/Properties/ConditionNodeProperties.tsx

interface ConditionNodePropertiesProps {
    node: Node;
    onUpdate: (nodeId: string, data: any) => void;
}

export function ConditionNodeProperties({
    node,
    onUpdate,
}: ConditionNodePropertiesProps) {
    const [condition, setCondition] = useState(node.data.condition || "");

    const handleConditionChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        const newCondition = e.target.value;
        setCondition(newCondition);
        onUpdate(node.id, {
            ...node.data,
            condition: newCondition,
        });
    };

    return (
        <div className="p-4 bg-white rounded shadow">
            <label className="block text-sm font-bold mb-2">조건식</label>
            <textarea
                value={condition}
                onChange={handleConditionChange}
                placeholder="예: input.length > 5 and status == 'active'"
                className="w-full p-2 border rounded font-mono text-xs"
                rows={4}
            />
            <p className="text-xs text-gray-600 mt-2">
                안전한 표현식: 비교연산자, 논리연산자, 함수 (len, str, int 등)
            </p>
        </div>
    );
}
```

**ParallelNode Properties Panel**
```tsx
// src/components/Properties/ParallelNodeProperties.tsx

interface ParallelNodePropertiesProps {
    node: Node;
    onUpdate: (nodeId: string, data: any) => void;
}

export function ParallelNodeProperties({
    node,
    onUpdate,
}: ParallelNodePropertiesProps) {
    const [numBranches, setNumBranches] = useState(
        node.data.branches?.length || 2
    );
    const [joinStrategy, setJoinStrategy] = useState(
        node.data.joinStrategy || "collect"
    );

    const handleNumBranchesChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const n = parseInt(e.target.value, 10);
        setNumBranches(n);

        // 브랜치 배열 초기화
        const branches = Array.from({ length: n }, (_, i) => ({
            id: `branch_${i}`,
            nodeIds: [],
        }));

        onUpdate(node.id, {
            ...node.data,
            branches,
        });
    };

    return (
        <div className="p-4 bg-white rounded shadow">
            <div className="mb-4">
                <label className="block text-sm font-bold mb-2">브랜치 수</label>
                <input
                    type="number"
                    value={numBranches}
                    onChange={handleNumBranchesChange}
                    min="2"
                    max="10"
                    className="w-full p-2 border rounded"
                />
            </div>

            <div>
                <label className="block text-sm font-bold mb-2">병합 전략</label>
                <select
                    value={joinStrategy}
                    onChange={(e) => {
                        setJoinStrategy(e.target.value);
                        onUpdate(node.id, {
                            ...node.data,
                            joinStrategy: e.target.value,
                        });
                    }}
                    className="w-full p-2 border rounded"
                >
                    <option value="collect">수집 (배열)</option>
                    <option value="merge">병합 (딕셔너리)</option>
                    <option value="first">첫 번째</option>
                    <option value="last">마지막</option>
                </select>
            </div>
        </div>
    );
}
```

**FeedbackLoopNode Properties Panel**
```tsx
// src/components/Properties/FeedbackLoopNodeProperties.tsx

interface FeedbackLoopPropertiesProps {
    node: Node;
    onUpdate: (nodeId: string, data: any) => void;
}

export function FeedbackLoopNodeProperties({
    node,
    onUpdate,
}: FeedbackLoopPropertiesProps) {
    const [maxIterations, setMaxIterations] = useState(
        node.data.maxIterations || 10
    );
    const [exitCondition, setExitCondition] = useState(
        node.data.exitCondition || ""
    );

    return (
        <div className="p-4 bg-white rounded shadow">
            <div className="mb-4">
                <label className="block text-sm font-bold mb-2">최대 반복 횟수</label>
                <input
                    type="number"
                    value={maxIterations}
                    onChange={(e) => {
                        const val = parseInt(e.target.value, 10);
                        setMaxIterations(val);
                        onUpdate(node.id, {
                            ...node.data,
                            maxIterations: val,
                        });
                    }}
                    min="1"
                    max="1000"
                    className="w-full p-2 border rounded"
                />
            </div>

            <div>
                <label className="block text-sm font-bold mb-2">탈출 조건</label>
                <textarea
                    value={exitCondition}
                    onChange={(e) => {
                        setExitCondition(e.target.value);
                        onUpdate(node.id, {
                            ...node.data,
                            exitCondition: e.target.value,
                        });
                    }}
                    placeholder="예: iteration > 5 or result == 'done'"
                    className="w-full p-2 border rounded font-mono text-xs"
                    rows={3}
                />
            </div>
        </div>
    );
}
```

#### 검증
- 조건식 입력 및 저장
- 병렬 분기 수 설정
- 피드백 루프 설정
- Properties 변경이 워크플로우 저장

---

### 5.2 MCP Tool 드롭다운 + Secrets 관리 UI

**파일**: `src/components/nodes/`, `src/pages/Secrets/`
**우선순위**: **P1** (Phase 4.1-4.2 이후)
**예상 작업량**: 중

#### 구현 내용

**MCP Tool Node Properties with Dropdown**
```tsx
// src/components/Properties/MCPToolNodeProperties.tsx

interface MCPToolNodePropertiesProps {
    node: Node;
    onUpdate: (nodeId: string, data: any) => void;
}

export function MCPToolNodeProperties({
    node,
    onUpdate,
}: MCPToolNodePropertiesProps) {
    const [mcpServers, setMcpServers] = useState([]);
    const [selectedServer, setSelectedServer] = useState(node.data.serverId);
    const [selectedTool, setSelectedTool] = useState(node.data.toolName);
    const [tools, setTools] = useState([]);
    const [toolSchema, setToolSchema] = useState(null);

    // MCP 서버 목록 로드
    useEffect(() => {
        fetch("/api/mcp/servers")
            .then(r => r.json())
            .then(data => setMcpServers(data.servers))
            .catch(console.error);
    }, []);

    // 서버 선택 시 도구 목록 로드
    const handleServerChange = async (serverId: string) => {
        setSelectedServer(serverId);

        const res = await fetch(`/api/mcp/servers/${serverId}/tools`);
        const data = await res.json();
        setTools(data.tools);

        onUpdate(node.id, {
            ...node.data,
            serverId,
            toolName: "",
            arguments: {},
        });
    };

    // 도구 선택 시 파라미터 폼 생성
    const handleToolChange = async (toolName: string) => {
        setSelectedTool(toolName);

        const res = await fetch(
            `/api/mcp/servers/${selectedServer}/tools/${toolName}`
        );
        const data = await res.json();
        setToolSchema(data.schema);

        onUpdate(node.id, {
            ...node.data,
            toolName,
        });
    };

    return (
        <div className="p-4 bg-white rounded shadow">
            <div className="mb-4">
                <label className="block text-sm font-bold mb-2">MCP 서버</label>
                <select
                    value={selectedServer}
                    onChange={(e) => handleServerChange(e.target.value)}
                    className="w-full p-2 border rounded"
                >
                    <option value="">-- 서버 선택 --</option>
                    {mcpServers.map(s => (
                        <option key={s.id} value={s.id}>{s.name}</option>
                    ))}
                </select>
            </div>

            {selectedServer && (
                <div className="mb-4">
                    <label className="block text-sm font-bold mb-2">도구</label>
                    <select
                        value={selectedTool}
                        onChange={(e) => handleToolChange(e.target.value)}
                        className="w-full p-2 border rounded"
                    >
                        <option value="">-- 도구 선택 --</option>
                        {tools.map(t => (
                            <option key={t.name} value={t.name}>
                                {t.name}
                            </option>
                        ))}
                    </select>
                </div>
            )}

            {toolSchema && (
                <MCPToolParametersForm
                    schema={toolSchema}
                    node={node}
                    onUpdate={onUpdate}
                />
            )}
        </div>
    );
}
```

**MCP Tool Parameters Form**
```tsx
// src/components/Properties/MCPToolParametersForm.tsx

interface MCPToolParametersFormProps {
    schema: any;
    node: Node;
    onUpdate: (nodeId: string, data: any) => void;
}

export function MCPToolParametersForm({
    schema,
    node,
    onUpdate,
}: MCPToolParametersFormProps) {
    const properties = schema.properties || {};
    const required = schema.required || [];

    const handleParameterChange = (paramName: string, value: any) => {
        const args = node.data.arguments || {};

        onUpdate(node.id, {
            ...node.data,
            arguments: {
                ...args,
                [paramName]: value,
            },
        });
    };

    return (
        <div className="border-t pt-4">
            <h4 className="font-bold mb-3">파라미터</h4>
            {Object.entries(properties).map(([paramName, paramSchema]: any) => (
                <div key={paramName} className="mb-3">
                    <label className="block text-sm font-bold mb-1">
                        {paramName}
                        {required.includes(paramName) && (
                            <span className="text-red-500">*</span>
                        )}
                    </label>

                    {paramSchema.type === "string" && (
                        <ParameterStringInput
                            paramName={paramName}
                            schema={paramSchema}
                            value={node.data.arguments?.[paramName] || ""}
                            onChange={handleParameterChange}
                        />
                    )}

                    {paramSchema.type === "number" && (
                        <input
                            type="number"
                            value={node.data.arguments?.[paramName] || ""}
                            onChange={(e) =>
                                handleParameterChange(paramName, parseFloat(e.target.value))
                            }
                            className="w-full p-2 border rounded"
                        />
                    )}

                    {paramSchema.type === "boolean" && (
                        <input
                            type="checkbox"
                            checked={node.data.arguments?.[paramName] || false}
                            onChange={(e) =>
                                handleParameterChange(paramName, e.target.checked)
                            }
                            className="w-4 h-4"
                        />
                    )}

                    {paramSchema.enum && (
                        <select
                            value={node.data.arguments?.[paramName] || ""}
                            onChange={(e) =>
                                handleParameterChange(paramName, e.target.value)
                            }
                            className="w-full p-2 border rounded"
                        >
                            <option value="">-- 선택 --</option>
                            {paramSchema.enum.map(opt => (
                                <option key={opt} value={opt}>{opt}</option>
                            ))}
                        </select>
                    )}

                    {paramSchema.description && (
                        <p className="text-xs text-gray-600 mt-1">
                            {paramSchema.description}
                        </p>
                    )}
                </div>
            ))}
        </div>
    );
}
```

**Parameter String Input (Secret 참조 지원)**
```tsx
// src/components/Properties/ParameterStringInput.tsx

interface ParameterStringInputProps {
    paramName: string;
    schema: any;
    value: string;
    onChange: (paramName: string, value: string) => void;
}

export function ParameterStringInput({
    paramName,
    schema,
    value,
    onChange,
}: ParameterStringInputProps) {
    const [secrets, setSecrets] = useState([]);
    const [showSecretDropdown, setShowSecretDropdown] = useState(false);

    useEffect(() => {
        fetch("/api/secrets")
            .then(r => r.json())
            .then(data => setSecrets(data.secrets || []))
            .catch(console.error);
    }, []);

    const insertSecretRef = (secretName: string) => {
        onChange(paramName, `${value}$\{SECRET_${secretName}}`);
        setShowSecretDropdown(false);
    };

    return (
        <div className="relative">
            <input
                type="text"
                value={value}
                onChange={(e) => onChange(paramName, e.target.value)}
                placeholder={schema.description}
                className="w-full p-2 border rounded"
            />

            {schema.type === "string" && (
                <button
                    onClick={() => setShowSecretDropdown(!showSecretDropdown)}
                    className="absolute right-2 top-2 text-sm text-blue-600"
                >
                    비밀
                </button>
            )}

            {showSecretDropdown && (
                <div className="absolute right-0 top-10 bg-white border rounded shadow-lg z-10">
                    {secrets.map(s => (
                        <button
                            key={s.id}
                            onClick={() => insertSecretRef(s.name)}
                            className="block w-full text-left px-3 py-2 hover:bg-gray-100 text-sm"
                        >
                            ${s.name}
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}
```

**Secrets 관리 페이지**
```tsx
// src/pages/Secrets/SecretsPage.tsx

export function SecretsPage() {
    const [secrets, setSecrets] = useState([]);
    const [showForm, setShowForm] = useState(false);
    const [formData, setFormData] = useState({ name: "", value: "" });

    // 비밀 목록 로드
    useEffect(() => {
        loadSecrets();
    }, []);

    const loadSecrets = async () => {
        const res = await fetch("/api/secrets");
        const data = await res.json();
        setSecrets(data.secrets || []);
    };

    const handleCreateSecret = async () => {
        const res = await fetch("/api/secrets", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(formData),
        });

        if (res.ok) {
            loadSecrets();
            setShowForm(false);
            setFormData({ name: "", value: "" });
        }
    };

    const handleDeleteSecret = async (secretId: string) => {
        const res = await fetch(`/api/secrets/${secretId}`, { method: "DELETE" });
        if (res.ok) {
            loadSecrets();
        }
    };

    return (
        <div className="p-6">
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-2xl font-bold">비밀 관리</h1>
                <button
                    onClick={() => setShowForm(true)}
                    className="px-4 py-2 bg-blue-600 text-white rounded"
                >
                    새 비밀 추가
                </button>
            </div>

            {showForm && (
                <div className="mb-6 p-4 bg-white rounded border">
                    <input
                        type="text"
                        placeholder="비밀 이름"
                        value={formData.name}
                        onChange={(e) =>
                            setFormData({ ...formData, name: e.target.value })
                        }
                        className="w-full p-2 border rounded mb-2"
                    />
                    <input
                        type="password"
                        placeholder="값"
                        value={formData.value}
                        onChange={(e) =>
                            setFormData({ ...formData, value: e.target.value })
                        }
                        className="w-full p-2 border rounded mb-2"
                    />
                    <div className="flex gap-2">
                        <button
                            onClick={handleCreateSecret}
                            className="px-4 py-2 bg-green-600 text-white rounded"
                        >
                            저장
                        </button>
                        <button
                            onClick={() => setShowForm(false)}
                            className="px-4 py-2 bg-gray-400 text-white rounded"
                        >
                            취소
                        </button>
                    </div>
                </div>
            )}

            <div className="space-y-3">
                {secrets.map(secret => (
                    <div
                        key={secret.id}
                        className="p-4 bg-white rounded border flex justify-between items-center"
                    >
                        <div>
                            <strong>{secret.name}</strong>
                            <p className="text-xs text-gray-600">
                                생성: {new Date(secret.created_at).toLocaleDateString()}
                            </p>
                        </div>
                        <button
                            onClick={() => handleDeleteSecret(secret.id)}
                            className="px-3 py-1 bg-red-600 text-white rounded text-sm"
                        >
                            삭제
                        </button>
                    </div>
                ))}
            </div>
        </div>
    );
}
```

#### 검증
- MCP 서버 드롭다운 로드
- 도구 선택 시 파라미터 폼 자동 생성
- 시크릿 참조 문법 (${SECRET_NAME})
- 시크릿 CRUD 작동

---

### 5.3 실행 시각화

**파일**: `src/components/Canvas/`, `src/pages/Execution/`
**우선순위**: **P1** (Phase 4.3 이후)
**예상 작업량**: 중

#### 구현 내용

**실행 상태 오버레이**
```tsx
// src/components/Canvas/ExecutionOverlay.tsx

interface ExecutionOverlayProps {
    execution: WorkflowExecution;
    onNodeClick: (nodeId: string) => void;
}

export function ExecutionOverlay({
    execution,
    onNodeClick,
}: ExecutionOverlayProps) {
    const getNodeStatus = (nodeId: string) => {
        const nodeExec = execution.node_executions.find(
            n => n.node_id === nodeId
        );
        return nodeExec?.status || "pending";
    };

    const getStatusColor = (status: string) => {
        const colors: Record<string, string> = {
            pending: "bg-gray-200",
            running: "bg-blue-400 animate-pulse",
            completed: "bg-green-500",
            failed: "bg-red-500",
            timed_out: "bg-orange-500",
        };
        return colors[status] || "bg-gray-200";
    };

    return (
        <>
            {execution.node_executions.map(nodeExec => (
                <div
                    key={nodeExec.node_id}
                    className={`absolute top-0 right-0 px-2 py-1 text-xs text-white rounded
                        ${getStatusColor(nodeExec.status)}`}
                    onClick={() => onNodeClick(nodeExec.node_id)}
                >
                    {nodeExec.status === "completed" && (
                        <span className="text-xs">✓ {nodeExec.duration_ms}ms</span>
                    )}
                    {nodeExec.status === "failed" && (
                        <span className="text-xs">✗ 실패</span>
                    )}
                </div>
            ))}
        </>
    );
}
```

**노드 결과 팝업**
```tsx
// src/components/Execution/NodeResultPopup.tsx

interface NodeResultPopupProps {
    nodeExecution: NodeExecution;
    onClose: () => void;
}

export function NodeResultPopup({
    nodeExecution,
    onClose,
}: NodeResultPopupProps) {
    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded shadow-lg max-w-2xl w-full mx-4 max-h-96 overflow-auto">
                <div className="p-6">
                    <div className="flex justify-between items-start mb-4">
                        <div>
                            <h2 className="text-lg font-bold">노드: {nodeExecution.node_id}</h2>
                            <p className={`text-sm font-bold ${
                                nodeExecution.status === "completed"
                                    ? "text-green-600"
                                    : "text-red-600"
                            }`}>
                                상태: {nodeExecution.status}
                            </p>
                        </div>
                        <button
                            onClick={onClose}
                            className="text-gray-400 hover:text-gray-600"
                        >
                            ✕
                        </button>
                    </div>

                    <div className="space-y-4">
                        <div>
                            <h3 className="font-bold text-sm mb-2">입력</h3>
                            <pre className="bg-gray-100 p-3 rounded text-xs overflow-auto">
                                {JSON.stringify(nodeExecution.input, null, 2)}
                            </pre>
                        </div>

                        {nodeExecution.status === "completed" && (
                            <div>
                                <h3 className="font-bold text-sm mb-2">출력</h3>
                                <pre className="bg-gray-100 p-3 rounded text-xs overflow-auto">
                                    {JSON.stringify(nodeExecution.output, null, 2)}
                                </pre>
                            </div>
                        )}

                        {nodeExecution.error && (
                            <div>
                                <h3 className="font-bold text-sm text-red-600 mb-2">에러</h3>
                                <pre className="bg-red-50 p-3 rounded text-xs">
                                    {nodeExecution.error}
                                </pre>
                            </div>
                        )}

                        <div className="text-xs text-gray-600">
                            <p>실행 시간: {nodeExecution.duration_ms}ms</p>
                            <p>재시도: {nodeExecution.retry_count}회</p>
                            <p>시작: {new Date(nodeExecution.started_at).toLocaleTimeString()}</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
```

**실행 진행률 표시**
```tsx
// src/components/Execution/ExecutionProgress.tsx

interface ExecutionProgressProps {
    execution: WorkflowExecution;
}

export function ExecutionProgress({
    execution,
}: ExecutionProgressProps) {
    const totalNodes = execution.node_executions.length;
    const completedNodes = execution.node_executions.filter(
        n => n.status === "completed"
    ).length;

    const progress = totalNodes > 0 ? (completedNodes / totalNodes) * 100 : 0;

    return (
        <div className="p-4 bg-white rounded border">
            <div className="flex justify-between items-center mb-2">
                <span className="font-bold">진행률</span>
                <span className="text-sm text-gray-600">
                    {completedNodes}/{totalNodes} 노드 완료
                </span>
            </div>

            <div className="w-full bg-gray-200 rounded h-2">
                <div
                    className="bg-blue-600 h-2 rounded transition-all"
                    style={{ width: `${progress}%` }}
                />
            </div>

            <div className="mt-4 space-y-2">
                {execution.node_executions.map(nodeExec => (
                    <div key={nodeExec.node_id} className="text-sm flex items-center">
                        {nodeExec.status === "completed" && (
                            <span className="text-green-600 mr-2">✓</span>
                        )}
                        {nodeExec.status === "running" && (
                            <span className="text-blue-600 mr-2">⟳</span>
                        )}
                        {nodeExec.status === "failed" && (
                            <span className="text-red-600 mr-2">✗</span>
                        )}
                        {["pending", "queued"].includes(nodeExec.status) && (
                            <span className="text-gray-400 mr-2">○</span>
                        )}

                        <span className="flex-1">{nodeExec.node_id}</span>
                        {nodeExec.duration_ms && (
                            <span className="text-gray-600">{nodeExec.duration_ms}ms</span>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}
```

**WebSocket 실시간 업데이트**
```tsx
// src/hooks/useExecutionUpdates.ts

export function useExecutionUpdates(executionId: string) {
    const [execution, setExecution] = useState<WorkflowExecution | null>(null);

    useEffect(() => {
        // WebSocket 연결
        const ws = new WebSocket(
            `ws://localhost:8000/api/executions/${executionId}/ws`
        );

        ws.onmessage = (event) => {
            const update = JSON.parse(event.data);

            if (update.type === "execution_update") {
                setExecution(update.execution);
            } else if (update.type === "node_completed") {
                setExecution(prev => {
                    if (!prev) return prev;
                    return {
                        ...prev,
                        node_executions: prev.node_executions.map(n =>
                            n.node_id === update.node_id
                                ? { ...n, status: update.status, output: update.output }
                                : n
                        ),
                    };
                });
            }
        };

        ws.onerror = console.error;

        return () => ws.close();
    }, [executionId]);

    return execution;
}
```

#### 검증
- 실행 진행상황 표시
- 노드 상태 색상 코딩
- 클릭 시 상세 정보 표시
- WebSocket 실시간 업데이트

---

### 5.4 워크플로우 템플릿 갤러리

**파일**: `src/components/Templates/`, `src/pages/TemplatesGallery/`
**우선순위**: **P2**
**예상 작업량**: 중

#### 구현 내용

**템플릿 갤러리 페이지**
```tsx
// src/pages/TemplatesGallery/TemplatesGallery.tsx

interface WorkflowTemplate {
    id: string;
    name: string;
    description: string;
    category: string;
    thumbnail?: string;
    workflow: {
        nodes: any[];
        edges: any[];
    };
}

const TEMPLATES: WorkflowTemplate[] = [
    {
        id: "news_scraper",
        name: "뉴스 크롤러",
        description: "주기적으로 뉴스를 수집하고 분석",
        category: "데이터",
        workflow: {
            nodes: [
                {
                    id: "fetch_news",
                    type: "mcp_tool",
                    data: {
                        serverId: "web-scraper",
                        toolName: "fetch_news",
                    },
                },
                {
                    id: "analyze",
                    type: "agent",
                    data: {
                        agentType: "text_analyzer",
                    },
                },
            ],
            edges: [
                {
                    id: "e1",
                    source: "fetch_news",
                    target: "analyze",
                },
            ],
        },
    },
    {
        id: "email_alert",
        name: "이메일 알림",
        description: "조건 기반 이메일 알림 발송",
        category: "알림",
        workflow: {
            nodes: [
                {
                    id: "check_condition",
                    type: "condition",
                    data: {
                        condition: "status == 'alert'",
                    },
                },
                {
                    id: "send_email",
                    type: "mcp_tool",
                    data: {
                        serverId: "email",
                        toolName: "send_email",
                    },
                },
            ],
            edges: [
                {
                    id: "e1",
                    source: "check_condition",
                    sourceHandle: "true",
                    target: "send_email",
                },
            ],
        },
    },
];

export function TemplatesGallery() {
    const navigate = useNavigate();
    const [selectedCategory, setSelectedCategory] = useState("all");

    const categories = [
        "all",
        ...new Set(TEMPLATES.map(t => t.category)),
    ];

    const filtered = selectedCategory === "all"
        ? TEMPLATES
        : TEMPLATES.filter(t => t.category === selectedCategory);

    const handleApplyTemplate = (template: WorkflowTemplate) => {
        // 새 워크플로우 생성 후 템플릿 적용
        navigate("/editor", {
            state: {
                initialWorkflow: {
                    name: `${template.name} - ${new Date().toLocaleDateString()}`,
                    description: template.description,
                    ...template.workflow,
                },
            },
        });
    };

    return (
        <div className="p-6">
            <h1 className="text-2xl font-bold mb-6">워크플로우 템플릿</h1>

            <div className="flex gap-2 mb-6">
                {categories.map(cat => (
                    <button
                        key={cat}
                        onClick={() => setSelectedCategory(cat)}
                        className={`px-4 py-2 rounded transition ${
                            selectedCategory === cat
                                ? "bg-blue-600 text-white"
                                : "bg-gray-200 text-gray-800 hover:bg-gray-300"
                        }`}
                    >
                        {cat === "all" ? "모두" : cat}
                    </button>
                ))}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filtered.map(template => (
                    <div
                        key={template.id}
                        className="p-4 bg-white rounded border shadow hover:shadow-lg transition"
                    >
                        {template.thumbnail && (
                            <img
                                src={template.thumbnail}
                                alt={template.name}
                                className="w-full h-40 object-cover rounded mb-4"
                            />
                        )}

                        <h3 className="font-bold text-lg mb-2">{template.name}</h3>
                        <p className="text-sm text-gray-600 mb-4">
                            {template.description}
                        </p>

                        <button
                            onClick={() => handleApplyTemplate(template)}
                            className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                        >
                            사용
                        </button>
                    </div>
                ))}
            </div>
        </div>
    );
}
```

#### 검증
- 템플릿 목록 표시
- 카테고리별 필터링
- 원클릭 적용 (캔버스에 로드)

---

### 5.5 데이터 흐름/변수 매핑 UI

**파일**: `src/components/DataFlow/`
**우선순위**: **P2**
**예상 작업량**: 중

#### 구현 내용

**데이터 흐름 시각화**
```tsx
// src/components/DataFlow/DataFlowVisualization.tsx

interface DataFlowProps {
    workflow: Workflow;
    execution?: WorkflowExecution;
}

export function DataFlowVisualization({
    workflow,
    execution,
}: DataFlowProps) {
    const [selectedEdge, setSelectedEdge] = useState<any>(null);
    const [dataFlowMap, setDataFlowMap] = useState<Map<string, any>>(new Map());

    // 실행 완료 후 데이터 흐름 계산
    useEffect(() => {
        if (execution) {
            const map = new Map();

            execution.node_executions.forEach(nodeExec => {
                workflow.edges.forEach(edge => {
                    if (edge.source === nodeExec.node_id) {
                        map.set(`${edge.id}`, {
                            from: nodeExec.node_id,
                            to: edge.target,
                            data: nodeExec.output,
                        });
                    }
                });
            });

            setDataFlowMap(map);
        }
    }, [execution, workflow]);

    return (
        <div className="p-4 bg-white rounded border">
            <h3 className="font-bold mb-4">데이터 흐름</h3>

            {selectedEdge && (
                <div className="mb-4 p-3 bg-blue-50 rounded">
                    <h4 className="font-bold text-sm mb-2">
                        {selectedEdge.from} → {selectedEdge.to}
                    </h4>
                    <pre className="bg-gray-100 p-2 rounded text-xs overflow-auto">
                        {JSON.stringify(selectedEdge.data, null, 2)}
                    </pre>
                </div>
            )}

            <div className="space-y-2">
                {Array.from(dataFlowMap.entries()).map(([edgeId, flow]) => (
                    <button
                        key={edgeId}
                        onClick={() => setSelectedEdge(flow)}
                        className={`w-full p-2 text-left rounded border transition ${
                            selectedEdge && selectedEdge.from === flow.from
                                ? "bg-blue-100 border-blue-600"
                                : "bg-gray-50 hover:bg-gray-100"
                        }`}
                    >
                        <span className="font-mono text-xs">
                            {flow.from} → {flow.to}
                        </span>
                    </button>
                ))}
            </div>
        </div>
    );
}
```

**변수 매핑 인터페이스**
```tsx
// src/components/DataFlow/VariableMappingPanel.tsx

interface VariableMappingPanelProps {
    node: Node;
    previousNodes: Node[];
    onUpdate: (nodeId: string, mapping: any) => void;
}

export function VariableMappingPanel({
    node,
    previousNodes,
    onUpdate,
}: VariableMappingPanelProps) {
    const [mappings, setMappings] = useState(node.data.variableMappings || {});

    const handleAddMapping = () => {
        const newMapping = {
            ...mappings,
            [`input_${Object.keys(mappings).length}`]: {
                source: previousNodes[0]?.id || "",
                path: "",
            },
        };

        setMappings(newMapping);
        onUpdate(node.id, { variableMappings: newMapping });
    };

    const handleRemoveMapping = (key: string) => {
        const updated = { ...mappings };
        delete updated[key];
        setMappings(updated);
        onUpdate(node.id, { variableMappings: updated });
    };

    const handleChangeMapping = (
        key: string,
        field: "source" | "path",
        value: string
    ) => {
        const updated = {
            ...mappings,
            [key]: {
                ...mappings[key],
                [field]: value,
            },
        };

        setMappings(updated);
        onUpdate(node.id, { variableMappings: updated });
    };

    return (
        <div className="p-4 bg-white rounded border">
            <div className="flex justify-between items-center mb-4">
                <h3 className="font-bold">변수 매핑</h3>
                <button
                    onClick={handleAddMapping}
                    className="text-sm px-3 py-1 bg-blue-600 text-white rounded"
                >
                    + 추가
                </button>
            </div>

            <div className="space-y-3">
                {Object.entries(mappings).map(([key, mapping]: any) => (
                    <div key={key} className="p-3 bg-gray-50 rounded border">
                        <div className="flex justify-between items-start mb-2">
                            <span className="font-mono text-sm">{key}</span>
                            <button
                                onClick={() => handleRemoveMapping(key)}
                                className="text-red-600 hover:text-red-700 text-sm"
                            >
                                삭제
                            </button>
                        </div>

                        <div className="space-y-2">
                            <div>
                                <label className="text-xs text-gray-600">출처 노드</label>
                                <select
                                    value={mapping.source}
                                    onChange={(e) =>
                                        handleChangeMapping(key, "source", e.target.value)
                                    }
                                    className="w-full p-2 border rounded text-sm"
                                >
                                    <option value="">-- 선택 --</option>
                                    {previousNodes.map(n => (
                                        <option key={n.id} value={n.id}>
                                            {n.id}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            <div>
                                <label className="text-xs text-gray-600">
                                    JSON Path (예: data.items[0].name)
                                </label>
                                <input
                                    type="text"
                                    value={mapping.path}
                                    onChange={(e) =>
                                        handleChangeMapping(key, "path", e.target.value)
                                    }
                                    placeholder="$.data.items[0]"
                                    className="w-full p-2 border rounded text-sm"
                                />
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
```

#### 검증
- 노드 간 데이터 전달 시각화
- 변수 매핑 인터페이스
- JSON Path 선택기

---

## Phase 6: 프로덕션 인프라

### 6.1 Docker + docker-compose

**파일**: `Dockerfile`, `docker-compose.yml`, `.dockerignore`
**우선순위**: **P1** (Phase 4 전체 완료 후)
**예상 작업량**: 중

#### 구현 내용

**Dockerfile (멀티스테이지)**
```dockerfile
# Stage 1: Frontend build
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# Stage 2: Backend + Frontend serve
FROM python:3.11-slim

WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 백엔드 코드
COPY backend/ ./

# 프론트엔드 빌드 결과 복사
COPY --from=frontend-builder /app/frontend/dist ./static

# 헬스 체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

# 환경 변수
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=postgresql://user:password@db:5432/agentweave

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**docker-compose.yml**
```yaml
version: "3.8"

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${DB_USER:-agentweave}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-changeme}
      POSTGRES_DB: ${DB_NAME:-agentweave}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "${DB_PORT:-5432}:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-agentweave}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "${REDIS_PORT:-6379}:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  app:
    build: .
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://${DB_USER:-agentweave}:${DB_PASSWORD:-changeme}@db:5432/${DB_NAME:-agentweave}
      REDIS_URL: redis://redis:6379/0
      SECRET_KEY: ${SECRET_KEY:-change-me-in-production}
      ENVIRONMENT: ${ENVIRONMENT:-development}
      CORS_ORIGINS: ${CORS_ORIGINS:-http://localhost:3000}
    ports:
      - "${APP_PORT:-8000}:8000"
    volumes:
      - ./backend:/app  # 개발 모드에서만 사용
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/live"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
  redis_data:
```

**.dockerignore**
```
node_modules
__pycache__
.git
.gitignore
.env
.env.*.local
.venv
venv
*.pyc
*.pyo
.pytest_cache
.mypy_cache
.DS_Store
dist
build
*.egg-info
.vscode
.idea
```

**.env.example**
```bash
# Database
DB_USER=agentweave
DB_PASSWORD=changeme
DB_NAME=agentweave
DB_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0
REDIS_PORT=6379

# App
SECRET_KEY=change-me-in-production
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:3000

# MCP
MCP_TIMEOUT=30

# Logging
LOG_LEVEL=INFO
```

#### 검증
- `docker-compose up` 명령으로 전체 스택 실행
- 헬스 체크 통과
- 데이터베이스 마이그레이션 자동 실행
- 프론트엔드 정적 파일 제공

---

### 6.2 PostgreSQL 마이그레이션 (Alembic)

**파일**: `backend/alembic/`
**우선순위**: **P1** (6.1과 동시)
**예상 작업량**: 중

#### 구현 내용

**Alembic 초기화**
```bash
cd backend
alembic init alembic
```

**alembic.ini 수정**
```ini
sqlalchemy.url = postgresql://agentweave:changeme@localhost/agentweave
```

**alembic/env.py 수정**
```python
from app.db.database import Base
from app.models import (
    WorkflowModel,
    ExecutionModel,
    ScheduleModel,
    SecretModel,
    MCPServerModel,
    WebhookModel,
    VersionModel,
    AuditLogModel,
)

target_metadata = Base.metadata
```

**마이그레이션 스크립트 자동 생성**
```bash
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

**수동 마이그레이션 예시**
```python
# alembic/versions/001_initial_schema.py

def upgrade():
    """초기 스키마 마이그레이션."""
    op.create_table(
        'workflows',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('nodes', sa.JSON, nullable=False),
        sa.Column('edges', sa.JSON, nullable=False),
        sa.Column('created_at', sa.DateTime, default=datetime.now),
        sa.Column('updated_at', sa.DateTime, default=datetime.now, onupdate=datetime.now),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )

    op.create_index('ix_workflows_user_id', 'workflows', ['user_id'])
    op.create_index('ix_workflows_created_at', 'workflows', ['created_at'])

def downgrade():
    """마이그레이션 롤백."""
    op.drop_table('workflows')
```

**마이그레이션 자동 실행 스크립트**
```python
# backend/app/db/init_db.py

import asyncio
from sqlalchemy import text
from alembic.config import Config
from alembic.command import upgrade

async def init_db():
    """데이터베이스 초기화 및 마이그레이션."""

    # SQLite → PostgreSQL 마이그레이션 (필요 시)
    await migrate_from_sqlite()

    # Alembic 마이그레이션 실행
    alembic_cfg = Config("alembic.ini")
    upgrade(alembic_cfg, "head")

    print("Database initialization complete")

async def migrate_from_sqlite():
    """SQLite에서 PostgreSQL로 데이터 마이그레이션."""
    # 개발 → 프로덕션 전환 시 필요
    pass
```

#### 검증
- 마이그레이션 스크립트 생성
- 전체 테이블 생성
- 인덱스 생성
- 롤백 가능

---

### 6.3 환경 변수 관리

**파일**: `backend/app/config.py`
**우선순위**: **P1** (6.1-6.2와 동시)
**예상 작업량**: 소

#### 구현 내용

**pydantic-settings 기반 설정**
```python
# backend/app/config.py

from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache

class Settings(BaseSettings):
    """애플리케이션 설정."""

    # Database
    DATABASE_URL: str = Field(
        default="sqlite:///./agentweave.db",
        description="Database connection URL"
    )

    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )

    # Security
    SECRET_KEY: str = Field(
        default="change-me-in-production",
        description="Secret key for JWT signing"
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    # Environment
    ENVIRONMENT: str = Field(
        default="development",
        description="Environment (development, staging, production)"
    )
    DEBUG: bool = Field(default=True)

    # CORS
    CORS_ORIGINS: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        description="Comma-separated CORS origins"
    )

    # MCP
    MCP_TIMEOUT: int = Field(default=30, description="MCP tool execution timeout")
    MCP_MAX_RETRIES: int = Field(default=3)

    # Logging
    LOG_LEVEL: str = Field(default="INFO")

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD: int = 60

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

@lru_cache()
def get_settings() -> Settings:
    """싱글턴 설정 객체 반환."""
    return Settings()
```

**환경별 설정 파일**
```bash
# .env.development
ENVIRONMENT=development
DEBUG=true
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
DATABASE_URL=sqlite:///./agentweave.db

# .env.staging
ENVIRONMENT=staging
DEBUG=false
CORS_ORIGINS=https://staging.example.com
DATABASE_URL=postgresql://user:pass@staging-db:5432/agentweave

# .env.production
ENVIRONMENT=production
DEBUG=false
CORS_ORIGINS=https://example.com
DATABASE_URL=postgresql://user:pass@prod-db:5432/agentweave
SECRET_KEY=${SECRET_KEY}  # 환경변수에서 로드
```

**main.py에서 사용**
```python
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Tool Hub API",
    debug=settings.DEBUG,
    # ...
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    # ...
)
```

#### 검증
- `.env` 파일 로드
- 환경별 설정 분리
- 필수 설정값 검증

---

### 6.4 CI/CD (GitHub Actions)

**파일**: `.github/workflows/`
**우선순위**: **P2**
**예상 작업량**: 중

#### 구현 내용

**PR 체크 워크플로우**
```yaml
# .github/workflows/ci.yml

name: CI

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main, develop]

jobs:
  frontend-lint-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-node@v3
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: 'frontend/package-lock.json'

      - run: cd frontend && npm ci

      - run: cd frontend && npm run lint

      - run: cd frontend && npm run type-check

      - run: cd frontend && npm run build

      - uses: actions/upload-artifact@v3
        with:
          name: frontend-build
          path: frontend/dist

  backend-test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'

      - run: pip install -r backend/requirements.txt

      - run: cd backend && python -m pytest tests/ -v --cov=app --cov-report=xml
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/test

      - uses: codecov/codecov-action@v3
        with:
          files: ./backend/coverage.xml

      - run: cd backend && python -m mypy app --strict

      - run: cd backend && python -m pylint app

  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'

      - uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'
```

**배포 워크플로우**
```yaml
# .github/workflows/deploy.yml

name: Deploy

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      packages: write
      contents: read

    steps:
      - uses: actions/checkout@v3

      - uses: docker/setup-buildx-action@v2

      - uses: docker/login-action@v2
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: |
            ghcr.io/${{ github.repository }}:latest
            ghcr.io/${{ github.repository }}:${{ github.sha }}
          cache-from: type=registry,ref=ghcr.io/${{ github.repository }}:buildcache
          cache-to: type=registry,ref=ghcr.io/${{ github.repository }}:buildcache,mode=max

  deploy-staging:
    needs: build-and-push
    runs-on: ubuntu-latest
    environment: staging

    steps:
      - name: Deploy to staging
        run: |
          # kubectl 또는 deploy 스크립트 호출
          echo "Deploying to staging..."

  deploy-production:
    needs: build-and-push
    runs-on: ubuntu-latest
    environment: production

    steps:
      - name: Deploy to production
        run: |
          # kubectl 또는 deploy 스크립트 호출
          echo "Deploying to production..."
```

#### 검증
- PR 체크 실행
- 테스트 커버리지 추적
- Docker 이미지 빌드 및 푸시
- 배포 자동화

---

### 6.5 모니터링 + Rate Limiting

**파일**: `backend/app/middleware/`
**우선순위**: **P2**
**예상 작업량**: 중

#### 구현 내용

**Rate Limiting (slowapi)**
```python
# backend/app/middleware/rate_limit.py

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException

limiter = Limiter(key_func=get_remote_address)

# 엔드포인트별 제한
RATE_LIMITS = {
    "/api/workflows": "10/minute",           # 워크플로우 조작
    "/api/workflows/*/run": "5/minute",       # 실행
    "/api/webhooks/": "100/minute",           # 웹훅 (외부)
    "/api/": "1000/minute",                   # 일반 API
    "/health/": None,                         # 헬스 체크 (무제한)
}

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return HTTPException(
        status_code=429,
        detail={
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests",
            }
        },
    )

# 라우트에 적용
from slowapi.depends import RateLimitKeyFn

@app.post("/api/workflows/{workflow_id}/run")
@limiter.limit("5/minute")
async def run_workflow(...):
    pass
```

**Prometheus 메트릭**
```python
# backend/app/middleware/metrics.py

from prometheus_client import Counter, Histogram, Gauge
import time

# 메트릭 정의
request_count = Counter(
    "fastapi_request_total",
    "Total requests",
    ["method", "endpoint", "status"],
)

request_duration = Histogram(
    "fastapi_request_duration_seconds",
    "Request duration",
    ["method", "endpoint"],
)

active_requests = Gauge(
    "fastapi_active_requests",
    "Active requests",
)

# 미들웨어
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    active_requests.inc()
    start_time = time.time()

    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as exc:
        status_code = 500
        raise
    finally:
        duration = time.time() - start_time

        # 메트릭 기록
        request_count.labels(
            method=request.method,
            endpoint=request.url.path,
            status=status_code,
        ).inc()

        request_duration.labels(
            method=request.method,
            endpoint=request.url.path,
        ).observe(duration)

        active_requests.dec()

    return response

# Prometheus 엔드포인트
from prometheus_client import generate_latest

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

**구조화된 로깅 (structlog)**
```python
# backend/app/middleware/logging.py

import structlog
from app.config import get_settings

settings = get_settings()

# structlog 설정
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# 로거 생성
logger = structlog.get_logger()

# 미들웨어
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start_time = time.time()

    logger.info(
        "request_start",
        method=request.method,
        path=request.url.path,
        client_ip=request.client.host,
    )

    try:
        response = await call_next(request)
    except Exception as exc:
        duration = time.time() - start_time
        logger.error(
            "request_error",
            method=request.method,
            path=request.url.path,
            duration_ms=int(duration * 1000),
            error=str(exc),
        )
        raise

    duration = time.time() - start_time
    logger.info(
        "request_complete",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=int(duration * 1000),
    )

    return response
```

**Execution 모니터링**
```python
# backend/app/middleware/execution_metrics.py

from prometheus_client import Counter, Histogram

execution_total = Counter(
    "workflow_execution_total",
    "Total workflow executions",
    ["workflow_id", "status", "mode"],
)

execution_duration = Histogram(
    "workflow_execution_duration_seconds",
    "Workflow execution duration",
    ["workflow_id"],
    buckets=(10, 30, 60, 300, 600),
)

node_execution_duration = Histogram(
    "node_execution_duration_seconds",
    "Node execution duration",
    ["node_type"],
)

# 사용
def track_execution(workflow_id: str, status: str, mode: str, duration: float):
    execution_total.labels(
        workflow_id=workflow_id,
        status=status,
        mode=mode,
    ).inc()

    execution_duration.labels(
        workflow_id=workflow_id,
    ).observe(duration)
```

#### 검증
- Rate limiting 작동
- Prometheus 메트릭 수집
- 구조화된 로그 출력
- 모니터링 대시보드 접근

---

## 타임라인 요약

| Phase | 작업 | 우선순위 | 의존성 | 예상 주 |
|-------|------|---------|--------|--------|
| 4.1 | PlaceholderExecutor 교체 | P0 | 없음 | 1주 |
| 4.2 | MCP 세션 수정 | P0 | 없음 | 1주 |
| 4.3 | Workflow CRUD API | P0 | 4.1 | 2주 |
| 4.4 | 병렬 실행 엔진 | P1 | 4.1 | 2주 |
| 4.5 | 조건 분기 엔진 | P1 | 4.1 | 2주 |
| 4.6 | 피드백 루프 | P2 | 4.5 | 2주 |
| 5.1 | Properties UI | P1 | 4.4, 4.5, 4.6 | 2주 |
| 5.2 | MCP/Secrets UI | P1 | 4.2 | 2주 |
| 5.3 | 실행 시각화 | P1 | 4.3 | 2주 |
| 5.4 | 템플릿 갤러리 | P2 | 5.1 | 1주 |
| 5.5 | 데이터 흐름 UI | P2 | 5.3 | 1주 |
| 6.1 | Docker | P1 | Phase 4 | 1주 |
| 6.2 | PostgreSQL | P1 | 6.1 | 1주 |
| 6.3 | 환경 변수 | P1 | 없음 | 1주 |
| 6.4 | CI/CD | P2 | 6.1 | 2주 |
| 6.5 | 모니터링 | P2 | 6.1 | 1주 |

**총 예상 기간**:
- **Phase 4 (Execution Engine)**: 5-6주
- **Phase 5 (Frontend)**: 6-7주
- **Phase 6 (Infrastructure)**: 4-5주
- **전체**: 15-18주 (약 4-5개월)

**Critical Path**:
1. 4.1, 4.2 → 4.3 (1주)
2. 4.3 → 5.3 → 5.5 (2주)
3. Phase 4 완료 → 6.1 → 6.2 (1주)

---

## 성공 지표 (Definition of Done)

### Phase 4 완료
- [ ] 모든 Workflow CRUD API 엔드포인트 작동
- [ ] 실행 시간 < 100ms (평균)
- [ ] 병렬 브랜치 3개 이상 동시 실행 확인
- [ ] 조건 분기 true/false 경로 정확히 선택
- [ ] 피드백 루프 최대 반복 횟수 제한
- [ ] 재시도 정책 자동 작동
- [ ] 테스트 커버리지 > 85%

### Phase 5 완료
- [ ] 모든 노드 타입 Properties Panel 구현
- [ ] MCP 드롭다운에서 50+ 도구 로드
- [ ] Secrets 암호화 저장 및 마스킹 표시
- [ ] 실행 시각화 실시간 업데이트 (< 500ms 지연)
- [ ] 10+ 템플릿 제공
- [ ] 데이터 흐름 JSON Path 지원

### Phase 6 완료
- [ ] Docker 이미지 빌드 < 5분
- [ ] docker-compose up으로 전체 스택 실행
- [ ] Alembic 마이그레이션 자동화
- [ ] PostgreSQL에서 10,000+ 워크플로우 저장 및 조회 (< 100ms)
- [ ] Rate limiting 작동 (429 반환)
- [ ] 모든 PR에 CI/CD 파이프라인 실행
- [ ] Prometheus 메트릭 수집
- [ ] 프로덕션 배포 자동화

---

## 리스크 및 완화 전략

| 리스크 | 영향 | 확률 | 완화 전략 |
|--------|------|------|----------|
| MCP 서버 연결 불안정 | Phase 4 진행 어려움 | 중 | Circuit breaker, timeout 강화 |
| 병렬 실행 deadlock | Phase 4.4 반복 필요 | 낮음 | 엄격한 테스트, 타임아웃 설정 |
| 조건식 인젝션 취약점 | 보안 문제 | 낮음 | simpleeval 화이트리스트 철저히 |
| PostgreSQL 성능 | Phase 6 배포 어려움 | 중 | 인덱스 전략, 쿼리 최적화 |
| 프론트엔드 복잡도 | Phase 5 일정 초과 | 중 | 컴포넌트 재사용, UI 라이브러리 활용 |

---

## 추가 고려사항

### 보안
- JWT 토큰 만료 정책
- API Key 관리
- 감사 로깅
- SQL injection 방지 (ORM 사용)
- CORS 정책 검토

### 성능
- 데이터베이스 인덱싱 전략
- 캐싱 (Redis)
- 배치 처리 (Celery)
- GraphQL 고려 (대량 데이터 조회)

### 운영
- 로그 집계 (ELK Stack)
- 알림 (PagerDuty, Slack)
- Backup/Disaster Recovery
- 배포 전략 (Blue-Green, Canary)

---

이 로드맵은 상황에 따라 조정될 수 있습니다. 각 Phase 시작 전에 진행 상황을 검토하고 필요시 일정을 재조정하세요.
