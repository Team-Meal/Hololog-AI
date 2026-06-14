# /validate-plan — 생성 식단 영양 검증

생성된 월간 식단의 영양 기준 충족 여부를 검증합니다.

## 검증 기준 (2026 학교급식 기본계획 기준)
| 항목 | 기준 (점심) |
|------|------------|
| 에너지 | 일일 권장량의 1/3 |
| 단백질 | 총 에너지의 7~20% |
| 지방 | 총 에너지의 15~30% |
| 나트륨 | 1,000mg 이하 |

## 실행 명령

```bash
uv run python app/agent/validate.py --month <YYYY-MM>
```

## 출력 형식

```
검증 결과: YYYY-MM
통과: XX일 / 30일
미달 항목:
  - YYYY-MM-DD LUNCH: 나트륨 초과 (1,234mg)
  - YYYY-MM-DD BREAKFAST: 단백질 미달 (4%)
```

## 완료 후
- research.md에 `[VALIDATE]` 항목 추가
- 30일치 대량 검증 시 `plan-validator` 서브 에이전트 background 스폰
  (`.claude/agents/plan-validator.md` 참조)
