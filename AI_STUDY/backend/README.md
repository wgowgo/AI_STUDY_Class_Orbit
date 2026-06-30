# Class Orbit Backend (FastAPI)

Full setup and env reference: **[`../README.md`](../README.md)**

---

## English

### Run

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

### Environment

Copy `.env.example` → `.env` and fill values locally. See inline comments in `.env.example` for every key.

**Production checklist** (when OpenAI is enabled and the server is public):

1. Set **`INTERNAL_API_KEY`**; mirror it in `web/.env` as **`VITE_INTERNAL_API_KEY`**.
2. Set **`CORS_ORIGINS`** to your frontend origin(s), not `*`.
3. Set **`APP_ENV=production`** — startup aborts if security settings are incomplete.
4. Adjust **`RATE_LIMIT_PER_MINUTE`** as needed.

In development (`APP_ENV=development`), insecure settings only emit log warnings.

### API summary

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/health` | Integration + security status |
| POST | `/api/analysis/class-from-text` | Class analytics from transcript |
| POST | `/api/pipeline/run` | Full analysis pipeline |
| GET | `/api/public/summary` | School summary (NEIS or sample) |
| GET | `/api/public/schools` | School search |
| GET | `/api/public/timetable` | Timetable |
| POST | `/api/public/kess` | KESS-style stats (sample) |
| POST | `/api/public/alimi` | School environment (sample) |
| POST | `/api/models/risk/predict-sklearn` | Risk prediction (simulation) |
| POST | `/api/rl/schedule/optimize-sb3` | Schedule optimization (simulation) |
| POST | `/api/xai/shap` | SHAP-style explanation (simulation) |
| POST | `/api/pathway/recommend` | Learning pathway |
| POST | `/api/warning/check` | Early warning |
| POST | `/api/equity/index` | Equity index |
| POST | `/api/resources/match` | Resource matching |
| POST | `/api/nlq/query` | Natural-language query (OpenAI or simulation) |
| POST | `/api/ai/chat` | Chat (**requires `INTERNAL_API_KEY` if set**) |
| POST | `/api/stt/transcribe` | Speech-to-text (**same**) |

Protected routes accept `X-Internal-Key` or `Authorization: Bearer <key>`.

### Tests

```bash
pytest -q
```

---

## 한국어

### 실행

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

### 환경 변수

`.env.example`을 `.env`로 복사한 뒤 로컬에서 값을 채웁니다. 각 키 설명은 `.env.example` 주석을 참고하세요.

**공개 배포 체크리스트** (OpenAI 사용 + 인터넷 공개 시):

1. **`INTERNAL_API_KEY`** 설정, `web/.env`의 **`VITE_INTERNAL_API_KEY`** 와 동일하게
2. **`CORS_ORIGINS`** 를 프론트 출처로 제한 (`*` 금지)
3. **`APP_ENV=production`** — 보안 미설정 시 기동 실패
4. **`RATE_LIMIT_PER_MINUTE`** 필요 시 조정

개발 모드(`APP_ENV=development`)에서는 경고 로그만 남기고 기동은 계속됩니다.

### API 요약

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/health` | 연동·보안 상태 |
| POST | `/api/analysis/class-from-text` | 수업 텍스트 분석 |
| POST | `/api/pipeline/run` | 전체 파이프라인 |
| GET | `/api/public/summary` | 학교 요약 (NEIS 또는 샘플) |
| GET | `/api/public/schools` | 학교 검색 |
| GET | `/api/public/timetable` | 시간표 |
| POST | `/api/public/kess` | KESS형 통계 (샘플) |
| POST | `/api/public/alimi` | 학교 환경 (샘플) |
| POST | `/api/models/risk/predict-sklearn` | 위험 예측 (시뮬레이션) |
| POST | `/api/rl/schedule/optimize-sb3` | 시간표 최적화 (시뮬레이션) |
| POST | `/api/xai/shap` | SHAP형 설명 (시뮬레이션) |
| POST | `/api/pathway/recommend` | 학습 경로 추천 |
| POST | `/api/warning/check` | 조기 경보 |
| POST | `/api/equity/index` | 형평성 지수 |
| POST | `/api/resources/match` | 자원 매칭 |
| POST | `/api/nlq/query` | 자연어 질의 (OpenAI 또는 시뮬레이션) |
| POST | `/api/ai/chat` | 채팅 (**`INTERNAL_API_KEY` 설정 시 필요**) |
| POST | `/api/stt/transcribe` | STT (**동일**) |

보호 엔드포인트는 `X-Internal-Key` 또는 `Authorization: Bearer <키>` 를 받습니다.

### 테스트

```bash
pytest -q
```
