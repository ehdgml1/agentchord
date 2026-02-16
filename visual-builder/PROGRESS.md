# Tool Hub Visual Builder - 작업 진행 현황

## 📊 현재 상태 (2026-02-06)

| 항목 | 수치 |
|------|------|
| API 엔드포인트 | 56개 |
| 테스트 | 193+ 개 (모두 통과) |
| 프론트엔드 빌드 | ✅ 성공 |
| 백엔드 임포트 | ✅ 성공 |

---

## ✅ 완료된 작업

### Phase -1: 아키텍처 스파이크
- [x] FastAPI 기본 구조
- [x] CORS, 보안 헤더 설정
- [x] 에러 핸들링
- [x] Health check 엔드포인트
- [x] **보안 취약점 7개 수정**
  - HMAC 웹훅 서명 검증
  - 명령어 인젝션 방지
  - Secret Store 비동기 수정

### Phase 0: MVP
- [x] SQLAlchemy 2.0 모델 (Workflow, Execution, Secret, MCPServer, Schedule, Webhook, AuditLog)
- [x] JWT 인증 시스템
- [x] Workflow CRUD API
- [x] Execution API
- [x] MCP 서버 관리 API
- [x] Secret 관리 API
- [x] Webhook API
- [x] Zustand 스토어 (execution, mcp, workflow)

### Phase 1: 핵심 기능
- [x] **APScheduler 통합**
  - `app/core/scheduler.py` - WorkflowScheduler 클래스
  - 타임존 지원 (pytz)
  - 다음 실행 시간 계산
- [x] **Cron 스케줄 API** (6개 엔드포인트)
  - `app/api/schedules.py`
  - GET/POST/DELETE /api/schedules
  - POST /{id}/enable, /{id}/disable
  - GET /{id}/history
- [x] **State Store**
  - `app/core/state_store.py`
  - 실행 상태 저장/복구
- [x] **프론트엔드 컴포넌트**
  - `TriggerNode.tsx` - 트리거 노드
  - `CronInput.tsx` - Cron 표현식 입력
  - `SchedulePanel.tsx` - 스케줄 관리 패널

### Phase 2: 확장 기능
- [x] **MCP 마켓플레이스**
  - `app/data/mcp_catalog.py` - 27개 MCP 서버 카탈로그
  - `MCPMarketplace.tsx` - 마켓플레이스 UI
  - `ServerCard.tsx` - 서버 카드 컴포넌트
- [x] **디버그 모드**
  - `app/api/debug_ws.py` - WebSocket 엔드포인트
  - `debugStore.ts` - 디버그 상태 관리
  - `useDebugWebSocket.ts` - WebSocket 훅
  - 브레이크포인트, 단계별 실행
- [x] **버전 관리**
  - `app/core/version_store.py` - 버전 저장소
  - `app/api/versions.py` - 버전 API
  - 히스토리 조회, 복원 기능
- [x] **워크플로우 내보내기/가져오기**

### Phase 3: 고급 기능
- [x] **RBAC 권한 시스템**
  - `app/core/rbac.py`
  - 4개 역할: Viewer, Editor, Operator, Admin
  - 권한 체크 데코레이터
- [x] **PII 필터링**
  - `app/core/pii_filter.py`
  - 이메일, 전화번호, 카드번호, 비밀번호 마스킹
- [x] **A/B 테스트**
  - `app/core/ab_test_runner.py`
  - `app/api/ab_tests.py` - 6개 엔드포인트
  - 트래픽 분할, 통계, CSV 내보내기
- [x] **Celery 분산 실행**
  - `app/core/celery_app.py`
  - Redis 브로커 설정
- [x] **관리자 UI**
  - `UserManagement.tsx` - 사용자 관리
  - `AuditLogViewer.tsx` - 감사 로그
  - `ABTestDashboard.tsx` - A/B 테스트 대시보드
  - `AdminLayout.tsx` - 관리자 레이아웃
- [x] **운영 문서화**
  - `docs/API_QUICK_REFERENCE.md`
  - `docs/RUNBOOK.md`
  - `docs/DISASTER_RECOVERY.md`

---

## 🔜 향후 작업 (Optional)

### 테스트 강화
- [ ] E2E 테스트 (Playwright/Cypress)
- [ ] 부하 테스트 (Locust)
- [ ] 보안 테스트 (OWASP ZAP)

### 인프라
- [ ] PostgreSQL 마이그레이션 (현재 SQLite)
- [ ] Redis 클러스터 설정
- [ ] Docker Compose 프로덕션 설정
- [ ] Kubernetes 배포 매니페스트

### 모니터링
- [ ] Prometheus 메트릭 추가
- [ ] Grafana 대시보드
- [ ] 알림 설정 (Slack, PagerDuty)
- [ ] 분산 트레이싱 (Jaeger)

### 기능 확장
- [ ] OAuth2 소셜 로그인
- [ ] 워크플로우 템플릿 갤러리
- [ ] 실시간 협업 편집
- [ ] AI 기반 워크플로우 추천

---

## 📁 주요 파일 구조

```
visual-builder/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 앱 (56 엔드포인트)
│   │   ├── api/
│   │   │   ├── workflows.py
│   │   │   ├── executions.py
│   │   │   ├── schedules.py     # Phase 1
│   │   │   ├── versions.py      # Phase 2
│   │   │   ├── debug_ws.py      # Phase 2
│   │   │   ├── ab_tests.py      # Phase 3
│   │   │   ├── audit.py         # Phase 3
│   │   │   └── users.py         # Phase 3
│   │   ├── core/
│   │   │   ├── scheduler.py     # APScheduler
│   │   │   ├── state_store.py
│   │   │   ├── version_store.py
│   │   │   ├── rbac.py          # Phase 3
│   │   │   ├── pii_filter.py    # Phase 3
│   │   │   ├── ab_test_runner.py
│   │   │   └── celery_app.py
│   │   ├── data/
│   │   │   └── mcp_catalog.py   # 27개 MCP 서버
│   │   └── db/
│   │       ├── models.py
│   │       └── database.py
│   └── tests/                   # 193+ 테스트
├── src/
│   ├── components/
│   │   ├── Sidebar/
│   │   │   ├── MCPMarketplace.tsx
│   │   │   └── ServerCard.tsx
│   │   ├── Admin/
│   │   │   ├── UserManagement.tsx
│   │   │   ├── AuditLogViewer.tsx
│   │   │   └── ABTestDashboard.tsx
│   │   └── nodes/
│   │       └── TriggerNode.tsx
│   ├── stores/
│   │   ├── debugStore.ts
│   │   ├── executionStore.ts
│   │   └── mcpStore.ts
│   └── hooks/
│       └── useDebugWebSocket.ts
└── docs/
    ├── API_QUICK_REFERENCE.md
    ├── RUNBOOK.md
    └── DISASTER_RECOVERY.md
```

---

## 🚀 실행 방법

### 백엔드
```bash
cd visual-builder/backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 프론트엔드
```bash
cd visual-builder
npm install
npm run dev
```

### 테스트
```bash
cd visual-builder/backend
pytest -v
```
