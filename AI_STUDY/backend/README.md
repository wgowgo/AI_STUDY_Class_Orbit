# Class Orbit Backend (FastAPI)

프론트와 함께 쓰는 방법, 환경 변수 전체 설명은 저장소 루트의 **[`../README.md`](../README.md)** 를 보세요.

## Run

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Environment

`cp .env.example .env` 후 값을 채웁니다. 자세한 키 설명은 `.env.example` 주석 참고.

## API (요약)

- `GET /api/health` — 연동, 보안 설정 요약 JSON
- `POST /api/analysis/class-from-text`
- `POST /api/pipeline/run`
- `GET /api/public/summary` / `GET /api/public/schools` / `GET /api/public/timetable`
- `POST /api/public/kess` / `POST /api/public/alimi`
- `POST /api/models/risk/predict-sklearn` / `POST /api/rl/schedule/optimize-sb3` / `POST /api/xai/shap`
- `POST /api/ai/chat` / `POST /api/stt/transcribe`

## Tests

```bash
pytest -q
```
