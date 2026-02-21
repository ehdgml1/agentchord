# AgentChord Visual Builder

AI 에이전트 파이프라인을 시각적으로 설계, 실행, 모니터링하는 워크플로우 자동화 플랫폼. 드래그&드롭 기반의 노드 편집기와 실시간 실행 추적을 제공합니다.

## 주요 기능

- **시각적 워크플로우 편집기**: 드래그&드롭으로 노드를 배치하고 연결. 자동 레이아웃, Undo/Redo 지원
- **6종 노드 타입**: Agent, MultiAgent, MCP, RAG, FeedbackLoop, Trigger
- **멀티 LLM 지원**: OpenAI, Anthropic, Gemini, Ollama — 사용자별 API 키 관리
- **MCP 마켓플레이스**: 15+ MCP 서버 카탈로그, 원클릭 설치 및 API 키 설정
- **멀티에이전트 전략**: Coordinator, Round Robin, Debate, Map-Reduce 4가지 팀 전략
- **RAG 노드**: 문서 업로드, 임베딩 모델 선택 (OpenAI/Gemini/Ollama), 벡터 검색
- **피드백 루프**: 조건부 반복 실행, ConditionBuilder UI로 종료 조건 시각적 설정
- **실행 엔진**: 위상 정렬 기반 실행, SSE 실시간 스트리밍, 백그라운드 실행 관리
- **Playground**: 멀티턴 대화, 자동 입력 체이닝, 워크플로우 단계별 결과 확인
- **스케줄러**: Cron 표현식 기반 워크플로우 자동 실행
- **보안**: JWT 인증, RBAC 권한 관리, Rate Limiting, IDOR 방어, 감사 로그
- **인프라**: Docker Compose, Nginx 리버스 프록시, Alembic DB 마이그레이션, GitHub Actions CI/CD

## 기술 스택

| 영역 | 기술 |
|------|------|
| **프론트엔드** | React 19, TypeScript, Vite, @xyflow/react, Zustand, Radix UI, Tailwind CSS |
| **백엔드** | FastAPI, SQLAlchemy (aiosqlite/asyncpg), Pydantic Settings, PyJWT |
| **데이터베이스** | SQLite (개발) / PostgreSQL (프로덕션) |
| **인프라** | Docker Compose, Nginx, Alembic, GitHub Actions |

## 빠른 시작

### 사전 요구사항

- Node.js 18+
- Python 3.11+
- Docker (프로덕션 배포 시)

### Docker로 실행 (권장)

```bash
cp .env.example .env        # 환경 변수 설정
docker compose up -d        # http://localhost:80
```

### 로컬 개발 환경

**프론트엔드**

```bash
npm install
npm run dev                 # http://localhost:5173
```

**백엔드**

```bash
cd backend
pip install -r requirements.txt
cp ../.env.example .env     # API 키 설정
uvicorn app.main:app --reload   # http://localhost:8000
```

## 프로젝트 구조

```
visual-builder/
├── src/                        # 프론트엔드 (React + TypeScript)
│   ├── components/             # UI 컴포넌트
│   │   ├── blocks/             # 노드 타입별 컴포넌트 (Agent, MCP, RAG 등)
│   │   ├── canvas/             # 워크플로우 편집기 캔버스
│   │   ├── properties/         # 노드 속성 패널
│   │   ├── playground/         # 실행 및 결과 확인
│   │   └── layout/             # 앱 레이아웃, 사이드바
│   ├── stores/                 # Zustand 상태 관리
│   ├── services/               # API 클라이언트
│   ├── types/                  # TypeScript 타입 정의
│   └── data/                   # 모델 카탈로그, MCP 카탈로그, 팀 템플릿
├── backend/                    # 백엔드 (FastAPI)
│   ├── app/
│   │   ├── api/                # API 엔드포인트 (56개 라우트)
│   │   ├── core/               # 실행 엔진, MCP 관리자, 스케줄러
│   │   ├── models/             # SQLAlchemy ORM 모델
│   │   ├── dtos/               # Pydantic 데이터 전송 객체
│   │   ├── services/           # 비즈니스 로직
│   │   └── repositories/       # 데이터 액세스 레이어
│   ├── tests/                  # pytest 테스트 (590+ 케이스)
│   └── alembic/                # DB 마이그레이션
├── nginx/                      # 리버스 프록시 설정
└── docker-compose.yml          # 프로덕션 배포
```

## 환경 변수 설정

`.env.example`을 복사하여 `.env`로 저장 후 아래 항목을 설정합니다.

```env
# 데이터베이스
DATABASE_URL=sqlite+aiosqlite:///./agentchord.db   # 개발용 SQLite
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost/agentchord  # 프로덕션

# 인증
JWT_SECRET=your-jwt-secret-key
SECRET_KEY=your-encryption-key

# LLM 프로바이더 (사용자별 키 관리 기능으로 대체 가능)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...

# 웹 검색 (Tavily, 선택 사항)
TAVILY_API_KEY=...

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:80
```

## API 엔드포인트

백엔드 실행 후 아래 URL에서 전체 API 문서를 확인할 수 있습니다.

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

주요 API 그룹:

| 그룹 | 경로 | 설명 |
|------|------|------|
| 인증 | `/api/auth/*` | 로그인, 토큰 갱신, 사용자 관리 |
| 워크플로우 | `/api/workflows/*` | CRUD, 실행, 스케줄 설정 |
| 실행 | `/api/executions/*` | 실행 이력, SSE 스트림 |
| MCP | `/api/mcp/*` | 서버 연결, 도구 목록 |
| 문서 | `/api/documents/*` | RAG용 파일 업로드/관리 |
| LLM 키 | `/api/llm/keys/*` | 사용자별 API 키 관리 |
| 감사 로그 | `/api/audit/*` | 보안 이벤트 기록 조회 |

## 개발 가이드

### 테스트 실행

```bash
# 프론트엔드 (1,100+ 테스트, 85%+ 커버리지)
npm test
npm run test:coverage

# 백엔드 (590+ 테스트)
cd backend && python -m pytest

# 백엔드 커버리지
cd backend && python -m pytest --cov=app --cov-report=html
```

### 코드 품질

```bash
# 프론트엔드 린트
npm run lint

# 백엔드 린트 / 타입 체크
cd backend && ruff check .
cd backend && mypy app/
```

### DB 마이그레이션

```bash
cd backend
alembic upgrade head                        # 마이그레이션 적용
alembic revision --autogenerate -m "설명"   # 새 마이그레이션 생성
```

## 라이선스

MIT
