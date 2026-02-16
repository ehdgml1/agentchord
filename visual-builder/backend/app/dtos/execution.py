"""Execution DTOs for serializable data transfer.

Phase -1 아키텍처 스파이크:
- 직렬화 가능한 ExecutionRequest (Celery 호환)
- JSON 직렬화/역직렬화 지원
- Pydantic 통합 준비

Phase 0 MVP:
- Added Pydantic models for API responses
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, UTC
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


@dataclass
class ExecutionRequest:
    """직렬화 가능한 실행 요청 DTO.

    Celery 태스크 큐에서 사용할 수 있도록 완전히 직렬화 가능한 형태.

    Attributes:
        workflow_id: 실행할 워크플로우 ID.
        input: 워크플로우 입력 문자열.
        mode: 실행 모드 ("full", "mock", "debug").
        user_id: 실행 요청 사용자 ID.
        trigger_type: 트리거 유형 ("manual", "cron", "webhook").
        trigger_id: 트리거 ID (스케줄/웹훅).
        start_from_node: 재개 시 시작 노드 ID.
        context: 재개 시 기존 컨텍스트.
        created_at: 요청 생성 시간.

    Example:
        >>> request = ExecutionRequest(
        ...     workflow_id="wf-123",
        ...     input="Hello world",
        ...     mode="full",
        ...     user_id="user-456",
        ... )
        >>> json_str = request.to_json()
        >>> restored = ExecutionRequest.from_json(json_str)
    """
    workflow_id: str
    input: str
    mode: str = "full"
    user_id: str | None = None
    trigger_type: str = "manual"
    trigger_id: str | None = None
    start_from_node: str | None = None
    context: dict[str, Any] | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).replace(tzinfo=None).isoformat())

    def to_json(self) -> str:
        """Serialize to JSON string.

        Returns:
            JSON string representation.
        """
        return json.dumps(asdict(self), ensure_ascii=False)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation.
        """
        return asdict(self)

    @classmethod
    def from_json(cls, data: str) -> ExecutionRequest:
        """Deserialize from JSON string.

        Args:
            data: JSON string.

        Returns:
            ExecutionRequest instance.
        """
        d = json.loads(data)
        return cls(**d)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExecutionRequest:
        """Create from dictionary.

        Args:
            data: Dictionary.

        Returns:
            ExecutionRequest instance.
        """
        return cls(**data)


@dataclass
class NodeExecutionResult:
    """노드 실행 결과 DTO."""
    node_id: str
    status: str
    output: Any | None = None
    error: str | None = None
    duration_ms: int | None = None
    retry_count: int = 0


@dataclass
class ExecutionResponse:
    """실행 응답 DTO.

    API 응답에 사용되는 실행 결과.

    Attributes:
        id: 실행 ID.
        workflow_id: 워크플로우 ID.
        status: 실행 상태.
        mode: 실행 모드.
        trigger_type: 트리거 유형.
        trigger_id: 트리거 ID.
        input: 입력 (선택적, 요청에 따라 포함).
        output: 출력 (선택적, 완료 시).
        error: 에러 메시지 (실패 시).
        node_results: 노드별 실행 결과.
        started_at: 시작 시간.
        completed_at: 완료 시간.
        duration_ms: 총 소요 시간 (ms).

    Example:
        >>> response = ExecutionResponse(
        ...     id="exec-789",
        ...     workflow_id="wf-123",
        ...     status="completed",
        ...     mode="full",
        ...     trigger_type="manual",
        ... )
        >>> json_str = response.to_json()
    """
    id: str
    workflow_id: str
    status: str
    mode: str
    trigger_type: str
    trigger_id: str | None = None
    input: str | None = None
    output: Any | None = None
    error: str | None = None
    node_results: list[NodeExecutionResult] = field(default_factory=list)
    started_at: str | None = None
    completed_at: str | None = None
    duration_ms: int | None = None

    def to_json(self) -> str:
        """Serialize to JSON string.

        Returns:
            JSON string representation.
        """
        return json.dumps(asdict(self), ensure_ascii=False, default=str)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation.
        """
        return asdict(self)

    @classmethod
    def from_json(cls, data: str) -> ExecutionResponse:
        """Deserialize from JSON string.

        Args:
            data: JSON string.

        Returns:
            ExecutionResponse instance.
        """
        d = json.loads(data)
        # Convert node_results back to dataclass instances
        if "node_results" in d and d["node_results"]:
            d["node_results"] = [
                NodeExecutionResult(**nr) for nr in d["node_results"]
            ]
        return cls(**d)


@dataclass
class ExecutionListResponse:
    """실행 목록 응답 DTO."""
    executions: list[ExecutionResponse]
    total: int
    limit: int
    offset: int

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(
            {
                "executions": [e.to_dict() for e in self.executions],
                "total": self.total,
                "limit": self.limit,
                "offset": self.offset,
            },
            ensure_ascii=False,
            default=str,
        )


# === Pydantic Models for API ===


class NodeLogResponse(BaseModel):
    """Node execution log response."""

    node_id: str = Field(..., description="Node ID", alias="nodeId")
    status: str = Field(..., description="Node execution status")
    input: Any = Field(None, description="Node input")
    output: Any = Field(None, description="Node output")
    error: str | None = Field(None, description="Error message if failed")
    started_at: str | None = Field(None, description="Start timestamp", alias="startedAt")
    completed_at: str | None = Field(None, description="Completion timestamp", alias="completedAt")
    duration_ms: int | None = Field(None, description="Duration in milliseconds", alias="durationMs")
    retry_count: int = Field(0, description="Number of retries", alias="retryCount")

    model_config = ConfigDict(populate_by_name=True)


class ExecutionDetailResponse(BaseModel):
    """Detailed execution response with node logs."""

    id: str = Field(..., description="Execution ID")
    workflow_id: str = Field(..., description="Workflow ID", alias="workflowId")
    status: str = Field(..., description="Execution status")
    mode: str = Field(..., description="Execution mode")
    trigger_type: str = Field(..., description="Trigger type", alias="triggerType")
    trigger_id: str | None = Field(None, description="Trigger ID", alias="triggerId")
    input: str | None = Field(None, description="Workflow input")
    output: Any | None = Field(None, description="Workflow output")
    error: str | None = Field(None, description="Error message if failed")
    node_logs: list[NodeLogResponse] = Field(default_factory=list, description="Node execution logs", alias="nodeExecutions")
    started_at: str | None = Field(None, description="Start timestamp", alias="startedAt")
    completed_at: str | None = Field(None, description="Completion timestamp", alias="completedAt")
    duration_ms: int | None = Field(None, description="Total duration in milliseconds", alias="durationMs")
    total_tokens: int | None = Field(None, description="Total tokens used", alias="totalTokens")
    prompt_tokens: int | None = Field(None, description="Prompt tokens used", alias="promptTokens")
    completion_tokens: int | None = Field(None, description="Completion tokens used", alias="completionTokens")
    estimated_cost: float | None = Field(None, description="Estimated cost in USD", alias="estimatedCost")
    model_used: str | None = Field(None, description="LLM model used", alias="modelUsed")

    model_config = ConfigDict(populate_by_name=True)


class ExecutionListItemResponse(BaseModel):
    """Execution list item response (without logs)."""

    id: str = Field(..., description="Execution ID")
    workflow_id: str = Field(..., description="Workflow ID", alias="workflowId")
    status: str = Field(..., description="Execution status")
    mode: str = Field(..., description="Execution mode")
    trigger_type: str = Field(..., description="Trigger type", alias="triggerType")
    started_at: str | None = Field(None, description="Start timestamp", alias="startedAt")
    completed_at: str | None = Field(None, description="Completion timestamp", alias="completedAt")
    duration_ms: int | None = Field(None, description="Total duration in milliseconds", alias="durationMs")
    total_tokens: int | None = Field(None, description="Total tokens used", alias="totalTokens")
    estimated_cost: float | None = Field(None, description="Estimated cost in USD", alias="estimatedCost")

    model_config = ConfigDict(populate_by_name=True)


class ExecutionListResponsePydantic(BaseModel):
    """Execution list response."""

    executions: list[ExecutionListItemResponse] = Field(..., description="List of executions")
    total: int = Field(..., description="Total count")
    limit: int = Field(..., description="Page limit")
    offset: int = Field(..., description="Page offset")
