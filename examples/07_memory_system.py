#!/usr/bin/env python3
"""Memory System Example.

이 예제는 AgentChord의 메모리 시스템 사용법을 보여줍니다.

실행:
    python examples/07_memory_system.py
"""

from agentchord.memory import (
    MemoryEntry,
    ConversationMemory,
    SemanticMemory,
    WorkingMemory,
)


def demo_conversation_memory() -> None:
    """ConversationMemory 데모."""
    print("=" * 60)
    print("1. Conversation Memory Demo")
    print("=" * 60)

    # 대화 기록 저장
    memory = ConversationMemory(max_entries=100)

    # 대화 추가
    memory.add(MemoryEntry(content="안녕하세요!", role="user"))
    memory.add(MemoryEntry(content="안녕하세요! 무엇을 도와드릴까요?", role="assistant"))
    memory.add(MemoryEntry(content="Python에 대해 알려주세요", role="user"))
    memory.add(MemoryEntry(content="Python은 범용 프로그래밍 언어입니다.", role="assistant"))

    print(f"\n저장된 메시지 수: {len(memory)}")

    # 최근 대화 조회
    print("\n[최근 2개 메시지]")
    for entry in memory.get_recent(limit=2):
        print(f"  {entry.role}: {entry.content}")

    # 검색
    print("\n[검색: 'Python']")
    results = memory.search("Python")
    for entry in results:
        print(f"  {entry.role}: {entry.content}")

    # LLM 메시지 형식으로 변환
    print("\n[LLM 메시지 형식]")
    messages = memory.to_messages()
    for msg in messages[:2]:
        print(f"  {msg}")


def demo_semantic_memory() -> None:
    """SemanticMemory 데모 (간단한 임베딩 사용)."""
    print("\n" + "=" * 60)
    print("2. Semantic Memory Demo")
    print("=" * 60)

    # 간단한 임베딩 함수 (실제로는 OpenAI/Sentence-Transformers 사용)
    def simple_embed(text: str) -> list[float]:
        """단순 문자 기반 임베딩 (데모용)."""
        vec = [0.0] * 26
        for c in text.lower():
            if 'a' <= c <= 'z':
                vec[ord(c) - ord('a')] += 1
        magnitude = sum(x*x for x in vec) ** 0.5
        if magnitude > 0:
            vec = [x / magnitude for x in vec]
        return vec

    memory = SemanticMemory(
        embedding_func=simple_embed,
        similarity_threshold=0.3,
    )

    # 지식 추가
    facts = [
        "Python is a programming language",
        "JavaScript runs in browsers",
        "Machine learning uses neural networks",
        "Databases store structured data",
    ]

    for fact in facts:
        memory.add(MemoryEntry(content=fact))

    print(f"\n저장된 지식: {len(memory)}개")

    # 의미 검색
    print("\n[검색: 'coding languages']")
    results = memory.search("coding languages", limit=2)
    for entry in results:
        print(f"  - {entry.content}")

    print("\n[검색: 'data storage']")
    results = memory.search("data storage", limit=2)
    for entry in results:
        print(f"  - {entry.content}")


def demo_working_memory() -> None:
    """WorkingMemory 데모."""
    print("\n" + "=" * 60)
    print("3. Working Memory Demo")
    print("=" * 60)

    # 작업 컨텍스트 저장
    memory = WorkingMemory(default_ttl=300, max_items=50)  # 5분 TTL

    # 작업 상태 저장
    memory.set("current_task", "code_review")
    memory.set("file_path", "/src/main.py")
    memory.set("step", 1)
    memory.set("errors_found", 0, priority=1)  # 높은 우선순위

    print(f"\n저장된 항목 수: {len(memory)}")

    # 값 조회
    print(f"\n현재 작업: {memory.get_value('current_task')}")
    print(f"파일 경로: {memory.get_value('file_path')}")

    # 값 증가
    memory.increment("step")
    memory.increment("errors_found", 3)

    print(f"\n현재 단계: {memory.get_value('step')}")
    print(f"발견된 오류: {memory.get_value('errors_found')}")

    # 모든 키-값 출력
    print("\n[전체 작업 컨텍스트]")
    for key, value in memory.items():
        print(f"  {key}: {value}")


def main() -> None:
    """메인 함수."""
    print("\n" + "=" * 60)
    print("AgentChord Memory System Examples")
    print("=" * 60)

    demo_conversation_memory()
    demo_semantic_memory()
    demo_working_memory()

    print("\n" + "=" * 60)
    print("Memory System Demo Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
