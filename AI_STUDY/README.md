# Class Orbit

Public-education data and AI in one demo stack: a **Vite + React** landing tour and an **AI Workspace**, backed by a **FastAPI** API.

---

## English

### Overview

Class Orbit connects classroom analytics, risk prediction, scheduling, explainability, and natural-language queries. Locally, the frontend proxies `/api` to the backend on port 8000.

**Stack**

| Layer | Tech |
|-------|------|
| Frontend | React 19, TypeScript, Vite, Framer Motion |
| Backend | FastAPI, httpx, Pydantic |
| AI (optional) | OpenAI Chat + Whisper via env vars |
| Public data (optional) | NEIS Open API |

### Requirements

- Node.js 20+ (recommended)
- Python 3.9+

### Quick start

**Terminal A — backend**

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in locally; never commit .env
uvicorn app.main:app --reload --port 8000
```

Health check: `GET http://localhost:8000/api/health`

**Terminal B — frontend**

```bash
cd web
npm install
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` → `http://localhost:8000`.

### Environment variables

See `backend/.env.example` and `web/.env.example`. Secrets stay in `.env` files only (gitignored).

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | Chat, STT, NLQ (simulation if empty) |
| `NEIS_API_KEY` + school codes | Live NEIS data (sample if missing) |
| `INTERNAL_API_KEY` | Protects paid AI endpoints |
| `VITE_INTERNAL_API_KEY` | Same value for the frontend (see security note) |
| `CORS_ORIGINS` | Allowed browser origins |
| `APP_ENV` | `production` enforces deployment security checks |

**`VITE_API_BASE_URL`**

- **Local (recommended):** leave empty — requests go to `/api` on the dev server and are proxied.
- **Production (separate API host):** set up to `https://api.example.com` and align backend `CORS_ORIGINS`.

### Demo vs live integrations

| Area | Behavior |
|------|----------|
| NEIS | Live when key + school codes are set; otherwise sample data + short TTL cache |
| KESS / School Alimi | Sample responses (`integration: sample_only`) until real APIs are wired |
| sklearn / SB3 / SHAP | Heuristic simulation; endpoints kept stable for future models |
| Chat / STT / NLQ | Needs `OPENAI_API_KEY`; optional `INTERNAL_API_KEY` for abuse protection |

### Production checklist

Before exposing the server with OpenAI enabled:

1. Set **`INTERNAL_API_KEY`** and match **`VITE_INTERNAL_API_KEY`** in `web/.env`.
2. Restrict **`CORS_ORIGINS`** to your frontend URL (avoid `*`).
3. Set **`APP_ENV=production`** — startup fails if the above are missing.
4. Tune **`RATE_LIMIT_PER_MINUTE`** if needed.

Do **not** rely on `VITE_INTERNAL_API_KEY` alone for strong security — it is embedded in the client bundle. Prefer a same-origin proxy or server-side header injection for production.

### Tests

```bash
cd backend
pytest -q
```

### Project layout

```
AI_STUDY/
├── backend/     FastAPI app, tests, .env.example
├── web/         React UI, Vite config, .env.example
└── README.md
```

Local fix scripts under `scripts/` are gitignored and not part of the published repo.

---

## 한국어

### 개요

Class Orbit는 공공 교육 데이터와 AI 기능을 묶은 데모 프로젝트입니다. **Vite + React** 랜딩/투어 UI와 **AI Workspace**, **FastAPI** 백엔드로 구성됩니다. 로컬에서는 프론트가 `/api`를 8000번 포트 백엔드로 프록시합니다.

**기술 스택**

| 구분 | 기술 |
|------|------|
| 프론트 | React 19, TypeScript, Vite, Framer Motion |
| 백엔드 | FastAPI, httpx, Pydantic |
| AI (선택) | OpenAI Chat + Whisper (환경 변수) |
| 공공 데이터 (선택) | NEIS Open API |

### 요구 사항

- Node.js 20+ (권장)
- Python 3.9+

### 빠른 시작

**터미널 A — 백엔드**

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 로컬에서만 채우기, .env는 커밋 금지
uvicorn app.main:app --reload --port 8000
```

헬스 체크: `GET http://localhost:8000/api/health`

**터미널 B — 프론트**

```bash
cd web
npm install
npm run dev
```

브라우저에서 `http://localhost:5173` 접속. Vite가 `/api` → `http://localhost:8000` 으로 프록시합니다.

### 환경 변수

`backend/.env.example`, `web/.env.example` 참고. 비밀 값은 `.env`에만 두세요 (gitignore 처리됨).

| 변수 | 용도 |
|------|------|
| `OPENAI_API_KEY` | 채팅, STT, NLQ (없으면 시뮬레이션) |
| `NEIS_API_KEY` + 학교 코드 | NEIS 실호출 (없으면 샘플) |
| `INTERNAL_API_KEY` | 유료 AI 엔드포인트 보호 |
| `VITE_INTERNAL_API_KEY` | 프론트용 동일 값 (보안 주의) |
| `CORS_ORIGINS` | 허용할 브라우저 출처 |
| `APP_ENV` | `production` 시 배포 보안 검사 강제 |

**`VITE_API_BASE_URL`**

- **로컬(권장):** 비워 두기 — `/api` 요청이 dev 서버를 거쳐 백엔드로 프록시됩니다.
- **프로덕션(API 분리):** 예) `https://api.example.com` — 백엔드 `CORS_ORIGINS`와 맞춥니다.

### 데모 vs 실연동

| 구분 | 동작 |
|------|------|
| NEIS | 키 + 학교 코드 있으면 실호출, 없으면 샘플 + 짧은 TTL 캐시 |
| KESS / 학교알리미 | 샘플 응답 (`integration: sample_only`) |
| sklearn / SB3 / SHAP | 휴리스틱 시뮬레이션 |
| 채팅 / STT / NLQ | `OPENAI_API_KEY` 필요, `INTERNAL_API_KEY`로 남용 방지 가능 |

### 공개 배포 체크리스트

OpenAI를 켠 채 인터넷에 올리기 전:

1. **`INTERNAL_API_KEY`** 설정, `web/.env`의 **`VITE_INTERNAL_API_KEY`** 와 동일하게 맞추기
2. **`CORS_ORIGINS`** 를 프론트 URL로 제한 (`*` 지양)
3. **`APP_ENV=production`** — 위 설정 누락 시 서버 기동 실패
4. 필요 시 **`RATE_LIMIT_PER_MINUTE`** 조정

`VITE_INTERNAL_API_KEY`만으로는 강한 보안이 되지 않습니다(클라이언트 번들에 포함될 수 있음). 프로덕션에서는 같은 출처 프록시나 서버에서 헤더를 붙이는 방식을 권장합니다.

### 테스트

```bash
cd backend
pytest -q
```

### 디렉터리 구조

```
AI_STUDY/
├── backend/     FastAPI, 테스트, .env.example
├── web/         React UI, Vite 설정, .env.example
└── README.md
```

로컬 수정용 `scripts/` 폴더는 gitignore 되어 저장소에 포함되지 않습니다.
