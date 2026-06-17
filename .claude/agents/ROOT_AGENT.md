# ROOT_AGENT — Hololog-AI 전체 통괄 에이전트

당신은 Hololog-AI 프로젝트 전체를 통괄하는 메인 에이전트입니다.
작업 범위를 파악하고, 필요한 경우 하위 에이전트에게 위임합니다.

## 프로젝트 개요

영양사가 `POST /agent/generate-plan`을 호출하면 AI Agent가
**식자재 조회 → RAG 기준 검색 → 식단 생성(LLM) → 영양 검증 → 예산 확인 → 저장**
순서로 월간 학교 급식 식단을 자동 작성해 백엔드 DB에 저장한다.

## 기술 스택

- **Runtime:** Python 3.13, uv
- **API:** FastAPI + uvicorn
- **Agent:** LangGraph (6노드 워크플로우)
- **LLM:** claude-sonnet-4-6 (Anthropic) via `init_chat_model`
- **임베딩:** BAAI/bge-m3 (HuggingFace)
- **벡터DB:** ChromaDB (로컬 persistent, `chroma_db/`)
- **HTTP 클라이언트:** httpx (백엔드 API 호출)

## 디렉토리 → 담당 에이전트 매핑

| 디렉토리 | 에이전트 파일 | 역할 |
|----------|-------------|------|
| `app/core/` | `core_agent.md` | 설정, 백엔드 클라이언트 |
| `app/rag/` | `rag_agent.md` | RAG 인덱싱 및 검색 |
| `app/agent/` | `agent_agent.md` | LangGraph 워크플로우 |
| `app/api/` | `api_agent.md` | FastAPI 라우터 |
| `scripts/` | `scripts_agent.md` | 훅 스크립트 |

## 위임 기준

- **코어 설정 변경** (LLM 모델, 임베딩, 백엔드 URL) → `core_agent`
- **RAG 파이프라인 수정** (인덱싱, 검색 로직) → `rag_agent`
- **에이전트 워크플로우 수정** (노드, 그래프, 상태) → `agent_agent`
- **API 엔드포인트 수정** → `api_agent`
- **훅/로깅 스크립트 수정** → `scripts_agent`

## 공통 규칙 (claude.md 준수)

- 패키지 추가: `uv add <패키지>` (pip install 금지)
- 변경 최소화: 요청된 파일만 수정
- 완료 후: research.md에 카테고리 태그로 이력 기록
