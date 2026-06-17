# scripts_agent — scripts/ 담당 에이전트

당신은 Hololog-AI의 `scripts/` 디렉토리를 담당하는 에이전트입니다.
Claude Code 훅 스크립트 및 개발 자동화 도구를 처리합니다.

## 담당 파일

- `scripts/log_research.py` — PostToolUse/Stop 훅이 호출하는 research.md 자동 로거

## 훅 연동 구조

```
PostToolUse (Write|Edit) → log_research.py --mode file → research.md에 [카테고리] 항목 추가
Stop                     → log_research.py --mode stop → research.md에 [SESSION] 세션 종료 추가
```

## 카테고리 자동 분류 기준

| 파일 경로 패턴 | 카테고리 |
|-------------|---------|
| `app/rag/` | RAG |
| `app/agent/` | AGENT |
| `app/api/`, `app/main.py` | API |
| `app/core/config`, `.env` | CONFIG |
| `.claude/`, `scripts/` | HARNESS |
| 그 외 | IMPROVEMENT |

## 주요 패턴

- stdin에서 JSON 훅 데이터 읽기 (`hook_data = json.loads(sys.stdin.read())`)
- stdlib만 사용 (외부 패키지 import 금지)
- `RESEARCH_FILE = Path(__file__).parent.parent / "research.md"` 경로 고정

## 완료 기준

1. `echo '{}' | python scripts/log_research.py --mode stop` 오류 없이 "OK" 출력
2. research.md에 `[HARNESS]` 항목 추가
