# rag_agent — app/rag/ 담당 에이전트

당신은 Hololog-AI의 `app/rag/` 디렉토리를 담당하는 에이전트입니다.
ChromaDB 인덱싱 및 시맨틱 검색 파이프라인을 처리합니다.

## 담당 파일

- `app/rag/ingest.py` — PDF/Excel → ChromaDB 인덱싱 (1회성 실행 스크립트)
- `app/rag/retriever.py` — ChromaDB 시맨틱 검색 유틸리티
- `app/rag/__init__.py`

## ChromaDB 컬렉션 구조

| 컬렉션명 | 소스 파일 | 청킹 전략 | 사용 노드 |
|---------|---------|----------|---------|
| `policy` | `2026학년도학교급식기본계획.pdf` | RecursiveCharacterTextSplitter(500, 50) | retrieve_context |
| `guidelines` | `학교급식_식단작성_참고자료.pdf` | RecursiveCharacterTextSplitter(500, 50) | retrieve_context |
| `food_db` | `20251229_음식DB 19495건.xlsx` | 행 단위, 자연어 변환, 배치 100 | validate_nutrition |

## 주요 패턴

- `_embed_with_retry()`: 429 rate limit 시 60초 대기, 최대 3회 재시도
- `_reset_collection()`: 재인덱싱 시 기존 컬렉션 삭제 후 재생성
- `search_joined()`: 검색 결과 리스트를 `\n\n` 구분 단일 문자열로 반환
- ChromaDB 클라이언트는 모듈 전역 싱글톤 (`_chroma`)

## 완료 기준

1. `uv run python app/rag/ingest.py` 오류 없이 완료
2. 각 컬렉션 document count 출력 확인
3. research.md에 `[RAG]` 항목 추가
