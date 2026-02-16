## Skills

커스텀 검증 및 유지보수 스킬은 `.claude/skills/`에 정의되어 있습니다.

| Skill | Purpose |
|-------|---------|
| `verify-implementation` | 프로젝트의 모든 verify 스킬을 순차 실행하여 통합 검증 보고서를 생성합니다 |
| `manage-skills` | 세션 변경사항을 분석하고, 검증 스킬을 생성/업데이트하며, CLAUDE.md를 관리합니다 |
| `verify-providers` | LLM provider가 BaseLLMProvider 계약을 준수하는지 검증합니다 |
| `verify-exports` | __init__.py의 __all__ 일관성과 public API 노출을 검증합니다 |
| `verify-tests` | 테스트 네이밍, docstring, 마커, 타입 힌트 등 규칙 준수를 검증합니다 |
| `verify-project` | pyproject.toml, CI/CD, ruff/mypy 설정의 일관성을 검증합니다 |
