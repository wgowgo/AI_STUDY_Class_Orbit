# Class Orbit Frontend (Vite + React)

Full setup: **[`../README.md`](../README.md)** · Backend API: **[`../backend/README.md`](../backend/README.md)**

---

## English

### Run

```bash
cd web
npm install
npm run dev
```

Default URL: `http://localhost:5173`

### Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Development server with HMR |
| `npm run build` | Typecheck + production build → `dist/` |
| `npm run preview` | Preview production build |
| `npm run lint` | ESLint |

### API proxy (local)

`vite.config.ts` proxies **`/api` → `http://localhost:8000`**. Start the backend first, then the frontend.

### Environment (`.env`)

Copy `.env.example` → `.env` when needed:

| Variable | When to set |
|----------|-------------|
| `VITE_API_BASE_URL` | Only if the API is on another host in production |
| `VITE_INTERNAL_API_KEY` | When backend `INTERNAL_API_KEY` is set (chat, STT, NLQ) |

**Local:** leave both empty — `/api` goes through the Vite proxy.

**Production:** if the API is on a different domain, set `VITE_API_BASE_URL` and ensure backend `CORS_ORIGINS` includes your frontend URL.

### UI structure

| Path / area | Description |
|-------------|-------------|
| Landing tour | Scroll-driven intro (Intro, Features, Flow, Contact) |
| AI Workspace | Analysis tabs: class, risk, schedule, twin, NLQ, pathway, etc. |
| `src/services/` | API clients (`aiClient`, `sttClient`, `pipelineClient`) |

---

## 한국어

### 실행

```bash
cd web
npm install
npm run dev
```

기본 주소: `http://localhost:5173`

### 스크립트

| 명령 | 설명 |
|------|------|
| `npm run dev` | 개발 서버 (HMR) |
| `npm run build` | 타입체크 + 프로덕션 빌드 → `dist/` |
| `npm run preview` | 빌드 결과 미리보기 |
| `npm run lint` | ESLint |

### API 프록시 (로컬)

`vite.config.ts`가 **`/api` → `http://localhost:8000`** 으로 프록시합니다. 백엔드를 먼저 띄운 뒤 프론트를 실행하세요.

### 환경 변수 (`.env`)

필요할 때 `.env.example` → `.env` 복사:

| 변수 | 설정 시점 |
|------|-----------|
| `VITE_API_BASE_URL` | 프로덕션에서 API가 다른 호스트일 때만 |
| `VITE_INTERNAL_API_KEY` | 백엔드 `INTERNAL_API_KEY` 설정 시 (채팅, STT, NLQ) |

**로컬:** 둘 다 비워 두면 `/api`가 Vite 프록시를 타고 백엔드로 갑니다.

**프로덕션:** API 도메인이 다르면 `VITE_API_BASE_URL`을 설정하고, 백엔드 `CORS_ORIGINS`에 프론트 URL을 넣으세요.

### UI 구조

| 영역 | 설명 |
|------|------|
| 랜딩 투어 | 스크롤 기반 소개 (Intro, Features, Flow, Contact) |
| AI Workspace | 수업·위험·시간표·트윈·NLQ·경로 등 분석 탭 |
| `src/services/` | API 클라이언트 (`aiClient`, `sttClient`, `pipelineClient`) |
