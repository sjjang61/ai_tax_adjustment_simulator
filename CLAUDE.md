# CLAUDE.md

이 파일은 Claude Code가 이 저장소에서 작업할 때 따라야 할 프로젝트 맥락과 규칙을 정의한다.

## 1. 프로젝트 개요

**연말정산 시뮬레이터**: 근로소득자가 예상 총급여와 공제 항목을 입력하면 최종 결정세액을 계산하고,
기납부세액과 비교해 **환급 / 추가 납부** 여부와 금액을 보여주는 웹 서비스.
**종합소득세 시뮬레이터**: 저장된 연말정산 결과(근로소득)에 사업소득·기타소득을 더해 종합소득세 납부(환급)액을 계산한다.
상단 메뉴에서 두 시뮬레이터를 구분한다.

핵심 사용자 흐름:

0. 입력 방식 선택: 개인 / 맞벌이 부부 (맞벌이는 부부 각자 입력 후 부양가족·의료비·교육비 최적 배분을 엔진이 계산하고 AI가 설명)
1. 귀속연도 선택 → 예상 총급여, 비과세 소득, 기납부세액(원천징수액) 입력
2. 기본공제(인적공제: 본인·배우자·부양가족) 및 추가공제(경로우대, 장애인, 부녀자, 한부모) 입력
3. 추가 소득공제 입력: 연금보험료, 건강·고용보험료, 주택자금, 신용카드 등 사용액, 벤처투자 등
4. 세액공제 입력: 자녀, 연금계좌(연금저축·IRP), 보험료, 의료비, 교육비, 기부금, 월세 등
5. 결과 확인: 단계별 계산 내역(과세표준 → 산출세액 → 결정세액) + 환급/추가납부액(지방소득세 포함)
6. **작년 데이터 불러오기**: 저장해 둔 전년도 시뮬레이션(또는 JSON 파일)을 불러와 올해 값의 초안으로 사용

## 2. 기술 스택

| 영역 | 스택 |
|---|---|
| Backend | Python 3.12+, FastAPI, Pydantic v2, pydantic-settings, SQLAlchemy 2.x + MySQL(PyMySQL, localhost:3306) |
| Frontend | React 18 + Vite + TypeScript, React Router, TanStack Query, React Hook Form + Zod |
| 패키지 관리 | Python: **uv** / Frontend: npm |
| 테스트 | Backend: pytest, pytest-cov, httpx(TestClient) / Frontend: Vitest, React Testing Library, MSW |
| 품질 도구 | Backend: ruff(lint+format), mypy / Frontend: ESLint, Prettier, `tsc --noEmit` |

## 3. 디렉터리 구조

```
.
├── .env                  # 실제 환경변수 (git 제외)
├── .env.example          # 환경변수 템플릿 (git 포함, 새 변수 추가 시 반드시 갱신)
├── CLAUDE.md
├── backend/
│   ├── pyproject.toml    # uv로 관리
│   ├── uv.lock
│   ├── app/
│   │   ├── main.py               # FastAPI 앱 생성, 라우터 등록, CORS
│   │   ├── core/config.py        # pydantic-settings (루트 .env 로드)
│   │   ├── api/v1/               # 라우터 (simulations, rules, import_export)
│   │   ├── schemas/              # Pydantic 요청/응답 모델
│   │   ├── models/               # SQLAlchemy ORM 모델
│   │   ├── repositories/         # DB 접근 계층
│   │   ├── services/             # 유스케이스 (저장, 불러오기, 연도 이월)
│   │   └── tax/                  # ★ 세금 계산 엔진 (순수 함수, I/O 없음)
│   │       ├── engine.py         # 전체 계산 파이프라인
│   │       ├── deductions/       # 소득공제 모듈 (personal, card, venture, ...)
│   │       ├── credits/          # 세액공제 모듈 (pension, donation, medical, ...)
│   │       └── rules/            # 귀속연도별 세법 수치 (예: y2025.py, y2026.py)
│   └── tests/
│       ├── unit/tax/             # 공제·세액공제 항목별 단위 테스트
│       ├── golden/               # 검증된 실제 사례 기반 end-to-end 계산 테스트
│       └── api/                  # API 통합 테스트
└── frontend/
    ├── package.json
    ├── vite.config.ts            # envDir: '..' (루트 .env 사용)
    └── src/
        ├── api/                  # API 클라이언트, 타입
        ├── features/simulation/  # 입력 위저드 단계별 컴포넌트
        ├── features/result/      # 결과·계산 내역 화면
        ├── features/import/      # 작년 데이터 불러오기
        ├── components/           # 공통 UI
        └── lib/                  # 금액 포맷터 등 유틸
```

## 4. 환경변수

- **환경변수 파일은 루트의 `.env` 하나만 사용**하며 backend와 frontend가 공유한다. 하위 디렉터리에 `.env`를 만들지 않는다.
- Backend: `app/core/config.py`에서 pydantic-settings가 **프로젝트 루트 기준 절대 경로**로 `.env`를 읽는다.
  실행 위치(cwd)에 의존하지 않도록 `Path(__file__).resolve().parents[N] / ".env"` 형태로 지정한다.
- Frontend: `vite.config.ts`에 `envDir: path.resolve(__dirname, '..')`를 설정한다.
  **`VITE_` 접두사가 붙은 변수만 브라우저 번들에 노출**되므로, 비밀값(DB 비밀번호, 시크릿 키 등)에는 절대 `VITE_`를 붙이지 않는다.
- 새 변수를 추가하면 `.env.example`에 설명 주석과 함께 반드시 추가한다.

```dotenv
# .env.example
APP_ENV=local                       # local | test | production
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8100
DB_HOST=localhost                   # MySQL 접속 정보 (연결 URL은 백엔드가 조립)
DB_PORT=3306
DB_USER=tax_simulator
DB_PASSWORD=change-me
DB_NAME=tax_simulator
OPENAI_API_KEY=                     # AI 추천용 (비밀값, VITE_ 금지)
OPENAI_MODEL=gpt-5.6-luna
OPENAI_TIMEOUT_SECONDS=60
CORS_ORIGINS=http://localhost:5173
DEFAULT_TAX_YEAR=2025               # 기본 귀속연도
VITE_API_BASE_URL=http://localhost:8100/api/v1
```

## 5. 개발 명령어

```bash
# Backend (backend/ 디렉터리 기준)
uv sync                                         # 의존성 설치
uv add <pkg> / uv add --dev <pkg>               # 패키지 추가 (pip 직접 사용 금지)
uv run python -m app                            # 개발 서버 (.env의 BACKEND_HOST/PORT, --reload)
uv run python -m app --port 8101                # 포트 지정 실행 (VITE_API_BASE_URL 포트도 맞출 것)
uv run pytest                                   # 전체 테스트
uv run pytest tests/unit/tax -q                 # 계산 엔진만
uv run pytest --cov=app/tax --cov-report=term-missing
uv run ruff check . && uv run ruff format .
uv run mypy app

# Frontend (frontend/ 디렉터리 기준)
npm install
npm run dev                                     # http://localhost:5173
npm run test                                    # Vitest
npm run lint && npm run typecheck
npm run build
```

## 6. 세금 계산 도메인

### 6.1 계산 파이프라인 (근로소득 기준)

```
총급여 (= 연간 근로소득 − 비과세소득)
 − 근로소득공제
 = 근로소득금액
 − 소득공제
     · 인적공제 (기본공제 + 추가공제)
     · 연금보험료공제 (국민연금 등)
     · 특별소득공제 (건강·고용보험료, 주택임차차입금, 장기주택저당차입금)
     · 그 밖의 소득공제 (주택청약종합저축, 신용카드 등 사용액, 벤처투자 등)
     · ※ 소득공제 종합한도 적용 대상 항목 처리
 = 과세표준
 × 기본세율 (누진세율표)
 = 산출세액
 − 세액감면
 − 세액공제
     · 근로소득세액공제, 자녀세액공제, 연금계좌세액공제
     · 특별세액공제 (보험료, 의료비, 교육비, 기부금) 또는 표준세액공제
     · 월세세액공제 등
 = 결정세액 (음수 불가, 0원 하한)
 − 기납부세액 (원천징수 + 종전근무지)
 = 차감징수세액  → 음수면 환급, 양수면 추가 납부
 + 지방소득세 (결정세액 기준 10%)
```

### 6.2 구현 원칙 (반드시 준수)

- **계산 엔진(`app/tax/`)은 순수 함수**로 작성한다. DB, HTTP, 파일 I/O, 현재 시각 참조 금지. 입력은 Pydantic 모델, 출력은 불변 결과 객체.
- **금액은 `int`(원 단위) 또는 `Decimal`만 사용**한다. `float` 사용 금지. 비율은 `Decimal("0.15")`처럼 문자열로 생성한다.
- **원 단위 절사·반올림 규칙은 각 단계마다 명시적으로** 적용하고, 어떤 규칙인지 주석으로 근거를 남긴다. 임의의 `round()` 사용 금지.
- **세법 수치를 코드에 하드코딩하지 않는다.** 세율표, 공제율, 한도, 구간 경계값은 모두 `app/tax/rules/y{연도}.py`의 규칙 객체에 정의하고, 계산 로직은 규칙 객체를 주입받는다.
- 각 규칙 값에는 **근거 출처**(소득세법·조세특례제한법 조문, 국세청 연말정산 안내 자료 등)를 주석으로 단다.
- 새 귀속연도를 추가할 때는 이전 연도 파일을 복사한 뒤 **개정 사항만 수정**하고, 변경 내역을 파일 상단 docstring에 요약한다.
- 각 공제 모듈은 `(적용 금액, 공제액, 한도 적용 여부, 설명)`을 담은 **계산 내역(breakdown)**을 반환한다. 프론트엔드는 이것으로 "왜 이 금액인지"를 보여준다.
- **세금 계산 로직은 백엔드에만 둔다.** 프론트엔드는 입력 검증(형식·범위)만 하고 세액을 자체 계산하지 않는다 (단일 진실 공급원).
- 공제 대상 요건 판정(부양가족 나이·소득 요건, 중복공제 불가 등)은 계산과 분리된 검증 함수로 두고, 위반 시 오류가 아닌 **경고(warning)**로 결과에 포함한다.

### 6.3 규칙 값 참고 (검증 필수)

아래는 설계 이해를 돕기 위한 참고값이다. **구현 시 반드시 해당 귀속연도의 국세청 고시·법령으로 재확인**하고, 다르면 공식 자료를 따른다.

- 근로소득공제: 총급여 구간별(500만 / 1,500만 / 4,500만 / 1억) 누진 공제율, 공제 한도 2,000만 원
- 기본세율: 과세표준 1,400만 이하 6% ~ 10억 초과 45%의 8단계 누진세율 (누진공제액 방식으로 구현)
- 인적공제: 기본공제 1인당 150만 원 / 경로우대 100만, 장애인 200만, 부녀자 50만, 한부모 100만
- 신용카드 등: 총급여의 25% 초과 사용분부터 공제, 결제수단별 공제율 상이, 총급여 구간별 기본한도 + 항목별 추가한도
- 벤처투자: 투자금액 구간별 차등 공제율, 종합소득금액 기준 한도
- 연금계좌: 총급여 구간에 따라 공제율 차등, 연금저축 단독 한도와 IRP 합산 한도 별도
- 의료비: 총급여 3% 초과분부터 공제, 본인·65세 이상·장애인 등은 한도 없음, 난임·미숙아 공제율 별도
- 기부금: 기부금 종류별(정치자금·고향사랑·특례·일반 등) 공제율과 한도 상이
- 특별세액공제를 신청하지 않으면 표준세액공제 적용 (둘 중 유리한 쪽을 엔진이 자동 비교해 표시)

## 7. 작년 데이터 불러오기

- 시뮬레이션은 `tax_year`, `schema_version`, `input`(JSON), `result_snapshot`과 함께 DB에 저장한다.
- 불러오기 경로는 두 가지:
  1. **저장된 시뮬레이션에서 불러오기**: 목록에서 전년도 건을 선택
  2. **JSON 파일 가져오기/내보내기**: `GET /simulations/{id}/export`, `POST /simulations/import`
- 전년도 데이터를 올해로 가져올 때는 `services/carry_over.py`에서 **연도 이월 변환**을 수행한다.
  - 부양가족 나이 +1 재계산 → 경로우대(70세)·자녀세액공제 연령 요건 재판정
  - 올해 규칙에서 사라지거나 새로 생긴 항목은 매핑 테이블로 처리하고, 매핑 불가 항목은 경고로 반환
  - 선택적으로 "급여 인상률 x%" 같은 일괄 보정 옵션 제공
  - 원본 데이터는 변경하지 않고 **새 시뮬레이션 초안**을 생성한다
- 가져오는 JSON은 `schema_version`을 검사하고, 구버전은 마이그레이션 함수 체인으로 변환한다. 알 수 없는 필드는 거부한다.

## 8. API 설계

- 모든 엔드포인트는 `/api/v1` 접두사를 사용한다.
- 주요 엔드포인트:
  - `POST /simulations/calculate` — 저장 없이 계산만 (입력 변경 시 실시간 미리보기용)
  - `POST /simulations` / `GET /simulations` / `GET /simulations/{id}` / `PUT /simulations/{id}` / `DELETE /simulations/{id}`
  - `POST /simulations/{id}/carry-over?target_year=YYYY` — 작년 데이터로 올해 초안 생성
  - `GET /simulations/{id}/export`, `POST /simulations/import`
  - `GET /rules/{tax_year}` — 해당 연도 한도·공제율 메타데이터 (프론트 입력 안내문·최대값 표시용)
- 요청/응답 스키마는 `app/schemas/`에 정의하고, 프론트엔드 타입은 OpenAPI 스키마에서 생성한다 (`openapi-typescript`). 수동으로 타입을 복제하지 않는다.
- 에러 응답 형식은 `{ "code": str, "message": str, "details": object | null }`로 통일한다.

## 9. 테스트

**테스트는 기능 구현과 함께 작성한다.** 계산 로직 변경 PR은 테스트 없이 완료로 간주하지 않는다.

### Backend
- **단위 테스트** (`tests/unit/tax/`): 공제·세액공제 모듈마다 작성. 반드시 포함할 케이스:
  - 구간 경계값 (경계 바로 아래 / 정확히 경계 / 바로 위)
  - 한도 도달·초과
  - 0원 입력, 최소 사용 기준 미달(예: 신용카드 25% 미만)
  - 결정세액이 0원 아래로 내려가지 않는지
- **골든 테스트** (`tests/golden/`): 국세청 안내 자료의 계산 사례 등 검증된 사례를 `cases/*.json`(입력 + 기대 결과 + 출처)으로 두고 parametrize로 실행한다.
- **속성 기반 테스트** (Hypothesis 권장): 총급여 증가 시 결정세액이 감소하지 않음, 공제 입력 증가 시 결정세액이 증가하지 않음 등 단조성 검증.
- **API 테스트** (`tests/api/`): TestClient 사용, 테스트용 DB는 인메모리 SQLite. `APP_ENV=test`로 실행.
- 커버리지 목표: `app/tax/` 분기 커버리지 95% 이상, 전체 80% 이상.

### Frontend
- Vitest + React Testing Library로 입력 폼 검증, 위저드 단계 이동, 결과 화면 렌더링을 테스트한다.
- API는 MSW로 모킹한다. 세액 숫자 자체를 프론트에서 검증하지 않는다 (백엔드 책임).
- 금액 포맷터(`1,234,567원`, 만원 단위 입력 변환 등) 유틸은 단위 테스트 필수.

## 10. 코딩 컨벤션

- Python: ruff 기본 규칙 + isort, 타입 힌트 필수, mypy strict 지향. 함수·변수명은 영어, 도메인 용어는 아래 용어집을 따른다.
- TypeScript: `strict: true`, `any` 사용 금지, 컴포넌트는 함수형 + named export.
- 금액 입력 UI는 원 단위로 저장하고 표시만 천 단위 콤마로 포맷한다.
- 커밋 메시지: Conventional Commits (`feat:`, `fix:`, `test:`, `refactor:`, `chore:`). 세법 수치 변경은 `feat(rules):` 또는 `fix(rules):`.

### 도메인 용어집

| 한국어 | 코드 식별자 |
|---|---|
| 총급여 | `gross_salary` |
| 비과세소득 | `non_taxable_income` |
| 근로소득공제 | `earned_income_deduction` |
| 근로소득금액 | `earned_income_amount` |
| 소득공제 | `income_deduction` |
| 인적공제 (기본/추가) | `personal_deduction` (`basic` / `additional`) |
| 과세표준 | `tax_base` |
| 산출세액 | `calculated_tax` |
| 세액공제 | `tax_credit` |
| 결정세액 | `determined_tax` |
| 기납부세액 | `prepaid_tax` |
| 차감징수세액 | `balance_due` (음수 = 환급) |
| 지방소득세 | `local_income_tax` |
| 귀속연도 | `tax_year` |

## 11. Claude 작업 규칙

- 세법 수치를 추가·변경할 때는 **출처를 확인할 수 없으면 임의로 값을 채우지 말고** `TODO(verify): ...` 주석과 함께 사용자에게 확인을 요청한다.
- 계산 엔진을 수정할 때는 먼저 실패하는 테스트를 작성하고 구현한다 (TDD).
- 작업 완료 전 `uv run pytest`, `uv run ruff check .`, `npm run test`, `npm run typecheck`를 실행해 통과를 확인한다.
- `.env`는 읽거나 수정하지 않는다. 필요한 변수는 `.env.example`에 추가하고 사용자에게 알린다.
- 의존성은 `uv add` / `npm install <pkg>`로만 추가하고, 추가 이유를 커밋 메시지에 남긴다.
- 규칙 파일(`app/tax/rules/`) 변경 시 골든 테스트 결과가 바뀌면 그 이유를 PR 설명에 적는다.

## 12. 고지

이 서비스는 **참고용 시뮬레이션**이며 실제 연말정산 결과와 다를 수 있다. 결과 화면에는 항상
"정확한 금액은 국세청 홈택스 연말정산 간소화 서비스 및 회사 정산 결과를 확인하세요"라는 고지를 표시한다.