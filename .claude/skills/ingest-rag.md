# /ingest-rag — 문서 → ChromaDB 인덱싱

RAG 소스 파일을 처리하여 ChromaDB 3개 컬렉션에 저장합니다.

## 소스 파일 및 컬렉션

| 파일 | 컬렉션명 | 청킹 전략 |
|------|---------|----------|
| `2026학년도학교급식기본계획.pdf` | `policy` | chunk_size=500, overlap=50 |
| `학교급식_식단작성_참고자료.pdf` | `guidelines` | chunk_size=500, overlap=50 |
| `20251229_음식DB 19495건.xlsx` | `food_db` | 행 단위, 배치 100 |

임베딩 모델: `text-embedding-3-small` (OpenAI)
저장 경로: `chroma_db/` (프로젝트 루트)

## 실행 명령

```bash
uv run python app/rag/ingest.py
```

## 완료 후 확인
- 각 컬렉션별 문서 수 출력
- 소요 시간 출력
- research.md에 `[RAG]` 항목 자동 추가

## 재인덱싱 시
`chroma_db/` 디렉토리 삭제 후 재실행 → 전체 재인덱싱

## 진행 상황
복잡한 분기가 필요할 때는 `rag-builder` 서브 에이전트를 background로 스폰
(`.claude/agents/rag-builder.md` 참조)
