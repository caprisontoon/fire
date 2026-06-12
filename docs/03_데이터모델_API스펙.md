# [3차 산출물] 백엔드 개발자 — 데이터 모델·API 스펙 + 구현 안내

> 작성 역할: 백엔드 개발자 에이전트
> 상태: **구현 완료** — `backend/` 폴더에 동작하는 코드와 테스트 포함
> 근거 문서: `docs/01_PM_아키텍트_설계초안.md`(아키텍처), `docs/02_세무건보_규칙.md`(계산 규칙)

---

## 1) 요약

- 단일 엔드포인트 **`POST /api/simulate`** 하나로 모든 계산(판정·세금·건보·연령별 시뮬레이션·시나리오 A/B/C)을 수행합니다.
- 입력은 5개 그룹(`basic` / `income` / `financial` / `pension` / `property`) 30개 미만의 필드, 전부 수동 입력.
- 서버는 아무것도 저장하지 않습니다 (DB 없음).
- 설계 문서(02) 대비 **추가된 입력 2개**: ① `annual_living_expense`(연간 생활비 — 자산 소진 나이 계산에 필수),
  ② `public_pension_start_age`(공적연금 수령 개시 나이, 기본 65세). PM 승인 필요 변경으로 기록함.

---

## 2) 입력 데이터 모델 (요청 JSON)

모든 금액은 **원(KRW) 단위, 연간·세전** 기준. 모든 금액 필드는 0 이상이어야 하며, 생략하면 0으로 처리.

### 2-1. `basic` — 기본 정보

| 필드 | 타입 | 필수 | 기본값 | 의미 |
|------|------|:---:|--------|------|
| `current_age` | int (19~89) | ✅ | — | 현재 나이 |
| `retire_age` | int | ✅ | — | 은퇴(예정) 나이. 현재 나이보다 작으면 "이미 은퇴"로 처리 |
| `married` | bool | | false | 혼인 여부 (배우자 기본공제 반영) |
| `insurance_status` | "직장"/"지역"/"피부양자" | ✅ | — | 현재 건강보험 자격 |
| `public_pension_start_age` | int | | 65 | 공적연금 수령 개시 나이 |
| `annual_living_expense` | int | | 0 | 연간 생활비(지출). 자산 소진 계산에 사용. 0이면 소진 계산 생략 |

### 2-2. `income` — 근로/사업/기타소득 (연간)

| 필드 | 의미 |
|------|------|
| `earned` | 근로소득 총급여 (은퇴 전까지만 반영) |
| `business` | 사업소득 (은퇴 후에도 계속된다고 가정) |
| `other` | 기타소득 |

### 2-3. `financial` — 금융소득 (연간·세전)

| 필드 | 의미 | 종합과세 합산 |
|------|------|:---:|
| `interest` | 이자소득 (예·적금, 채권 이자) | ✅ |
| `dividend_domestic` | 국내 상장주식 배당금 | ✅ |
| `dividend_foreign` | 해외 상장주식 배당금 (원화 환산) | ✅ |
| `etf_domestic_equity_dist` | 국내 주식형 ETF 분배금 | ✅ |
| `etf_domestic_other_dist_and_gain` | 기타 국내 ETF 분배금 + 과세 대상 매매차익 | ✅ |
| `etf_foreign_dist` | 해외 상장 ETF 분배금 | ✅ |
| `capital_gain_foreign` | 해외 상장 주식/ETF 양도차익 | ❌ (양도소득세 별도) |

### 2-4. `pension` — 연금

| 필드 | 의미 |
|------|------|
| `public_annual` | 공적연금 연간 수령액 (개시 나이부터 반영) |
| `private_annual` | 사적연금(연금저축+IRP) 연간 수령액 (은퇴 나이부터 반영) |
| `tax_free_annual` | 비과세 연금 연간 수령액 (은퇴 나이부터 반영) |
| `housing_monthly` | 주택연금 월 수령액 (은퇴 나이부터 반영) |

### 2-5. `property` — 재산/임대

| 필드 | 의미 |
|------|------|
| `real_estate_tax_base` | 부동산 재산세 과세표준 (단순 입력) |
| `rent_monthly` | 임대 월세 수입 (월) |
| `financial_assets` | 금융자산 총액 (시뮬레이션 초기값) |

### 2-6. 요청 JSON 전체 예시

```json
{
  "basic": { "current_age": 52, "retire_age": 55, "married": true,
             "insurance_status": "직장", "public_pension_start_age": 65,
             "annual_living_expense": 36000000 },
  "income": { "earned": 60000000, "business": 0, "other": 0 },
  "financial": { "interest": 3000000, "dividend_domestic": 5000000,
                 "dividend_foreign": 4000000, "etf_domestic_equity_dist": 1000000,
                 "etf_domestic_other_dist_and_gain": 6000000,
                 "etf_foreign_dist": 2000000, "capital_gain_foreign": 10000000 },
  "pension": { "public_annual": 18000000, "private_annual": 12000000,
               "tax_free_annual": 0, "housing_monthly": 0 },
  "property": { "real_estate_tax_base": 300000000, "rent_monthly": 500000,
                "financial_assets": 800000000 }
}
```

---

## 3) 출력 데이터 모델 (응답 JSON)

최상위 판정·세금·건보 값은 **"현재 나이 기준 1년치 스냅샷"**(시나리오 A)이다.
연령별 변화는 `scenarios.*.cashflow_by_age`에서 확인한다.

```json
{
  "aggregate_financial_tax": {
    "subject": true,
    "total": 21000000,
    "threshold": 20000000,
    "margin": -1000000
  },
  "income_tax": {
    "aggregate_income_tax": 7387600,
    "private_pension_tax": 0,
    "foreign_capital_gain_tax": 1650000,
    "financial_withholding_tax": 0,
    "total_tax": 9037600,
    "tax_base": 48200000
  },
  "health_insurance": {
    "status_applied": "직장",
    "monthly_premium": 247000,
    "annual_premium": 2964000,
    "dependent_eligible": false,
    "dependent_fail_reasons": ["합산소득 2,000만 원 초과"]
  },
  "scenarios": {
    "A": {
      "label": "현재 입력 그대로",
      "financial_income_total": 21000000,
      "aggregate_subject": true,
      "cashflow_by_age": [
        { "age": 52, "status": "직장", "income": 95000000, "tax": 9037600,
          "insurance": 2964000, "net": 82998400, "remaining_assets": 879000000 }
      ],
      "asset_depletion_age": null,
      "retire_year_snapshot": { "...": "은퇴 첫해의 세금·건보 요약" }
    },
    "B": { "label": "금융소득 연 2,000만 원 이하 관리", "...": "동일 구조" },
    "C": { "label": "금융소득 연 1,000만 원 이하 관리", "...": "동일 구조" }
  },
  "disclaimers": ["본 결과는 단순화된 모델에 따른 참고용 추정치입니다. ..."]
}
```

### `cashflow_by_age` 행의 의미

| 필드 | 의미 |
|------|------|
| `age` | 나이 |
| `status` | 해당 연도에 적용된 건보 자격 (은퇴 후에는 피부양자 판정 → 탈락 시 지역) |
| `income` | 연간 총 현금 수입 (근로+사업+기타+임대+금융+양도차익+모든 연금) |
| `tax` | 연간 총 세부담 (종합소득세+연금소득세+양도세+원천징수) |
| `insurance` | 연간 건강보험료 (장기요양 포함) |
| `net` | `income − tax − insurance` = 순 현금흐름 |
| `remaining_assets` | 연말 기준 금융자산 잔액 (생활비 차감 후) |

### `asset_depletion_age`

`annual_living_expense > 0`일 때, 금융자산 잔액이 처음 0 미만이 되는 나이. 90세까지 버티면 `null`.
자산 변화식 (이중계산 방지를 위해 금융소득은 자산 수익의 일부로 간주):

```
다음해 자산 = 자산 × (1 + 4%) − (금융소득 + 해외양도차익)   ← 자산에서 빠져나간 현금
            + (순 현금흐름 − 연간 생활비)                     ← 쓰고 남은(모자란) 현금
```

---

## 4) API 스펙

| 항목 | 내용 |
|------|------|
| 엔드포인트 | `POST /api/simulate` |
| 요청 본문 | 2-6 예시 JSON (`Content-Type: application/json`) |
| 응답 | 3장 구조의 JSON, HTTP 200 |
| 검증 오류 | HTTP 422 + 필드별 오류 메시지 (Pydantic 자동) |
| 저장 | 없음 (무상태) |
| 문서 | 서버 실행 후 `http://localhost:8000/docs` 에서 자동 생성 API 문서 확인 가능 |

---

## 5) 코드 구조 (구현 완료)

```
backend/
├── main.py               # FastAPI 앱, POST /api/simulate, 프론트 정적 파일 서빙
├── models.py             # 입력/출력 Pydantic 모델 (이 문서 2~3장과 1:1)
├── rules.py              # 기준값 상수 전부 (docs/02 1장과 1:1)
├── tax.py                # 모듈 1~4: 금융소득 합산·종합과세 판정·연금 분류·소득세
├── health_insurance.py   # 모듈 5: 건보료·피부양자 판정
├── simulation.py         # 연령별 현금흐름·시나리오 A/B/C
└── tests/
    └── test_cases.py     # docs/02 8장의 대표 케이스 3종 + 세율표 검증
```

함수명과 계산 순서는 `docs/02_세무건보_규칙.md`의 모듈 번호와 1:1로 대응한다.
시나리오 B/C는 금융소득 6개 필드를 **같은 비율로 축소**해 합계가 한도(2,000만/1,000만)에 맞도록 조정한다
(해외 양도차익은 금융소득이 아니므로 조정하지 않음).

---

## 6) 실행 방법 (비개발자용)

```bash
# 1. 프로젝트 폴더에서 의존 패키지 설치 (최초 1회)
pip install -r requirements.txt

# 2. 서버 실행
uvicorn backend.main:app --reload

# 3. 브라우저에서 열기
#    http://localhost:8000        ← 화면 (프론트엔드 완성 후)
#    http://localhost:8000/docs   ← API 테스트 화면 (지금도 사용 가능)
```

테스트 실행: `python -m pytest backend/tests/ -v`

---

## 7) 다음 단계

- **4단계(병행 가능):** 데이터/시뮬레이션 에이전트가 `docs/05`에서 시나리오 로직 검증·보강
  (기본 구현은 본 단계에 포함했으므로, 가정값 검토 중심)
- **5단계:** 프론트엔드 에이전트가 본 문서 2~3장의 JSON 스펙으로 `frontend/` 구현
