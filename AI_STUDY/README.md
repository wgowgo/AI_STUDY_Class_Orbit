# Class Orbit (데모 → 실서비스)

프론트(Vite + React)와 백엔드(FastAPI)가 나뉘어 있습니다. 로컬에서는 Vite가 `/api`를 백엔드로 넘깁니다.

## 요구 사항

- Node 20+ (권장), Python 3.9+

## 백엔드

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # 키는 여기만 채우고 Git에는 올리지 않기
uvicorn app.main:app --reload --port 8000
```

- 헬스: `GET http://localhost:8000/api/health` (JSON, 연동 여부 요약)
- 환경 변수 설명: `backend/.env.example` 참고

## 프론트엔드

```bash
cd web
npm install
npm run dev
```

기본 주소는 `http://localhost:5173` 입니다. `vite.config.ts`에서 **`/api` → `http://localhost:8000`** 프록시가 잡혀 있어, 브라우저는 같은 출처로 `/api/...`만 호출하면 됩니다.

### `VITE_API_BASE_URL`

- **비워 두기(권장, 로컬)**: 빈 문자열이면 요청이 `http://localhost:5173/api/...` 로 가고, Vite 프록시가 백엔드로 넘깁니다.
- **프로덕션에서 프론트, API 도메인이 다를 때**: 예) `VITE_API_BASE_URL=https://api.example.com` 처럼 API 베이스만 지정합니다. 그때는 해당 API 서버에 **CORS**(`CORS_ORIGINS`)를 맞춰야 합니다.

## 한 화면에서 붙이는 방법 (로컬)

1. 터미널 A: 백엔드 `uvicorn` (포트 8000)
2. 터미널 B: 프론트 `npm run dev` (포트 5173)
3. 브라우저에서 앱 열기 → AI Workspace 등에서 `/api` 호출이 프록시를 통해 백엔드로 전달됨

## 데모와 실서비스 사이 (현재 설계)

| 구분 | 상태 |
|------|------|
| NEIS | `NEIS_API_KEY` + 학교 코드가 있으면 실호출, 없으면 샘플. 짧은 TTL 캐시로 호출 완화 |
| KESS / 학교알리미 | 응답에 `integration: sample_only` 등 메타. 실 API 스펙 확정 시 같은 엔드포인트에서 교체 |
| sklearn / SB3 / SHAP | **시뮬레이션**(휴리스틱). 학습 아티팩트 연동 전까지 엔드포인트 형태만 고정 |
| 채팅 / STT | `OPENAI_API_KEY` 필요. 선택적으로 `INTERNAL_API_KEY`로 내부 전용 보호 |

보안 관련 환경 변수: `CORS_ORIGINS`, `RATE_LIMIT_PER_MINUTE`, `INTERNAL_API_KEY` 는 `backend/.env.example` 참고.

`INTERNAL_API_KEY`는 **브라우저 번들에 넣지 마세요**(노출됨). 서버 간 호출, BFF, 또는 프록시가 헤더를 붙이는 경우에만 사용하세요. 로컬 데모에서는 비워 두면 채팅, STT는 키 없이 동작합니다.

## 테스트 (스모크)

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```
