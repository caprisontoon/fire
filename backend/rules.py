"""세법·건강보험 기준값 상수 (2025년 기준).

제도가 바뀌면 이 파일의 숫자만 수정한다. 각 값의 의미와 근거는
docs/02_세무건보_규칙.md 1장의 표와 1:1로 대응한다.
"""

# ── 금융소득 ──────────────────────────────────────────────
FIN_TAX_THRESHOLD = 20_000_000        # 금융소득종합과세 기준선 (연)
FIN_WITHHOLDING_RATE = 0.14           # 이자·배당 원천징수세율 (지방세 제외)
LOCAL_TAX_RATE = 0.10                 # 지방소득세 (산출 소득세의 10%)
FOREIGN_CG_DEDUCTION = 2_500_000      # 해외주식 양도소득 기본공제 (연)
FOREIGN_CG_RATE = 0.22                # 해외주식 양도소득세율 (지방세 포함)

# ── 종합소득세 누진세율표: (과세표준 상한, 세율, 누진공제) ──
TAX_BRACKETS = [
    (14_000_000, 0.06, 0),
    (50_000_000, 0.15, 1_260_000),
    (88_000_000, 0.24, 5_760_000),
    (150_000_000, 0.35, 15_440_000),
    (300_000_000, 0.38, 19_940_000),
    (500_000_000, 0.40, 25_940_000),
    (1_000_000_000, 0.42, 35_940_000),
    (None, 0.45, 65_940_000),         # 최고 구간
]

# ── 소득공제 (단순화 모델) ────────────────────────────────
EARNED_INCOME_DEDUCTION_RATE = 0.25   # 근로소득공제: 총급여의 25%
EARNED_INCOME_DEDUCTION_MAX = 12_000_000
BASIC_DEDUCTION_PER_PERSON = 1_500_000  # 기본공제 (본인/배우자 각각)

# ── 연금 ──────────────────────────────────────────────────
PRIVATE_PENSION_SEP_LIMIT = 15_000_000   # 사적연금 저율 분리과세 한도 (연)
PRIVATE_PENSION_RATE_UNDER70 = 0.055     # 연금소득세율: 70세 미만 (지방세 포함)
PRIVATE_PENSION_RATE_70S = 0.044         # 70~79세
PRIVATE_PENSION_RATE_80UP = 0.033        # 80세 이상
PRIVATE_PENSION_EXCESS_SEP_RATE = 0.165  # 한도 초과 시 분리과세 세율 (지방세 포함)
PUBLIC_PENSION_TAXABLE_RATIO = 0.80      # 공적연금 중 과세대상 비율 (단순화 S3)
PENSION_INCOME_DEDUCTION_RATE = 0.40     # 연금소득공제율 (단순화 S3)
PENSION_INCOME_DEDUCTION_MAX = 9_000_000

# ── 건강보험 ──────────────────────────────────────────────
HI_RATE = 0.0709                      # 건강보험료율
HI_EMPLOYEE_RATE = HI_RATE / 2        # 직장가입자 본인부담분
LTC_RATE_ON_HI = 0.1295               # 장기요양보험료 = 건보료 × 12.95%
HI_EMPLOYEE_EXTRA_THRESHOLD = 20_000_000  # 직장인 보수 외 소득 추가보험료 기준선
HI_FIN_INCOME_MIN = 10_000_000        # 금융소득: 초과 시 전액 부과소득에 반영
HI_PUBLIC_PENSION_RATIO = 0.50        # 공적연금의 부과소득 반영 비율
HI_PROPERTY_DEDUCTION = 100_000_000   # 지역가입자 재산 과표 기본공제
HI_PROPERTY_RATE_SIMPLE = 0.0024      # 재산분 단순 부과율 (연, 단순화 S7)
HI_REGIONAL_MIN_MONTHLY = 19_780      # 지역가입자 월 최저보험료

# ── 피부양자 판정 ─────────────────────────────────────────
DEP_INCOME_LIMIT = 20_000_000             # 합산소득 한도 (연금 100%·금융 전액 반영)
DEP_PROPERTY_LIMIT_1 = 540_000_000        # 재산 과표 1차 기준 (5.4억)
DEP_PROPERTY_LIMIT_2 = 900_000_000        # 재산 과표 2차 기준 (9억)
DEP_INCOME_LIMIT_MID_PROPERTY = 10_000_000  # 재산 5.4억~9억 구간의 소득 한도

# ── 시뮬레이션 가정 ───────────────────────────────────────
ASSET_RETURN_RATE = 0.04              # 금융자산 명목 수익률 (연)
SIM_END_AGE = 90                      # 시뮬레이션 종료 나이
SCENARIO_B_CAP = 20_000_000           # 시나리오 B: 금융소득 관리 한도
SCENARIO_C_CAP = 10_000_000           # 시나리오 C: 금융소득 관리 한도
