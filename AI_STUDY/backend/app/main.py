from __future__ import annotations

import logging
import os
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from starlette.responses import JSONResponse

try:
    # uvicorn[standard]가 python-dotenv를 포함할 때가 많지만,
    # 환경에 따라 없을 수 있으니 import 실패는 조용히 무시합니다.
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass

import httpx
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


class KessStatsRequest(BaseModel):
    region: Optional[str] = None
    year: Optional[int] = None
    grade: Optional[int] = None


class AlimiEnvRequest(BaseModel):
    atpt_code: Optional[str] = None
    school_code: Optional[str] = None
    school_name: Optional[str] = None


class SklearnRiskPredictRequest(BaseModel):
    averageScore: float
    attendanceRate: float
    classQualityScore: float
    schoolEnvironmentScore: float


class RlScheduleRequest(BaseModel):
    koreanLevel: float
    mathLevel: float
    englishLevel: float
    fatigue: float
    studyHours: float
    objective: Optional[str] = None


class ShapExplainRequest(BaseModel):
    averageScore: float
    attendanceRate: float
    classQualityScore: float
    schoolEnvironmentScore: float


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = Field(default_factory=list)


class ClassAnalysisInput(BaseModel):
    transcriptLength: int
    explanationFocus: float
    repetitionCount: int
    questionPromptRate: float
    keywordDensity: float


class RiskInput(BaseModel):
    averageScore: float
    attendanceRate: float
    classQualityScore: float
    schoolEnvironmentScore: float


class ScheduleInput(BaseModel):
    koreanLevel: float
    mathLevel: float
    englishLevel: float
    fatigue: float
    studyHours: float


class TwinInput(BaseModel):
    currentAverage: float
    planQuality: float
    consistency: float
    weeks: float


class CausalInput(BaseModel):
    attendanceImpact: float
    classQualityImpact: float
    selfStudyImpact: float
    environmentImpact: float


class ExplainInput(BaseModel):
    attendance: float
    understanding: float
    fatigue: float
    classQuality: float


class TranscriptRequest(BaseModel):
    transcript: str


class PipelineRunRequest(BaseModel):
    transcript: str
    risk_input: RiskInput
    schedule_input: ScheduleInput
    twin_input: TwinInput
    causal_input: CausalInput
    xai_input: ExplainInput


EXPLAIN_WORDS = ["정리", "핵심", "개념", "이유", "공식", "원리", "따라서", "because", "therefore", "concept"]
CHAT_WORDS = ["농담", "잡담", "딴얘기", "잠깐", "쉬자", "웃음", "ㅋㅋ", "ㅎㅎ"]
QUESTION_WORDS = ["?", "질문", "이해", "왜", "어떻게", "what", "why", "how"]
KEYWORDS = ["학습", "성적", "분석", "피드백", "예측", "복습", "전략", "수업", "위험도", "time", "model"]


def count_matches(text: str, words: list[str]) -> int:
    lower = text.lower()
    return sum(lower.count(w.lower()) for w in words)


def derive_class_input(transcript: str) -> dict[str, Any]:
    clean = transcript.strip()
    sentences = [s.strip() for s in __import__("re").split(r"[.!?\n]+", clean) if s.strip()]
    sentence_count = max(len(sentences), 1)

    question_count = count_matches(clean, QUESTION_WORDS)
    explain_count = count_matches(clean, EXPLAIN_WORDS)
    chat_count = count_matches(clean, CHAT_WORDS)
    keyword_count = count_matches(clean, KEYWORDS)

    normalized = [__import__("re").sub(r"\s+", "  ", s).lower() for s in sentences]
    seen = set()
    repeated = 0
    for s in normalized:
        if s in seen:
            repeated += 1
        seen.add(s)

    explanation_focus = clamp(round(((explain_count + sentence_count * 0.65) / (chat_count + sentence_count)) * 100), 25, 95)
    question_rate = clamp(round((question_count / sentence_count) * 100), 0, 100)
    keyword_density = clamp(round((keyword_count / sentence_count) * 100), 5, 100)

    return {
        "input": ClassAnalysisInput(
            transcriptLength=len(clean),
            explanationFocus=explanation_focus,
            repetitionCount=repeated,
            questionPromptRate=question_rate,
            keywordDensity=keyword_density,
        ),
        "meta": {
            "sentenceCount": sentence_count,
            "questionCount": question_count,
            "repeatedSentenceCount": repeated,
        },
    }


def analyze_class(input_data: ClassAnalysisInput) -> dict[str, Any]:
    explanation_ratio = clamp(input_data.explanationFocus / 100, 0, 1)
    repetition_penalty = clamp(input_data.repetitionCount / 30, 0, 1)
    question_boost = clamp(input_data.questionPromptRate / 100, 0, 1)
    keyword_boost = clamp(input_data.keywordDensity / 100, 0, 1)
    base = explanation_ratio * 0.45 + (1 - repetition_penalty) * 0.2 + question_boost * 0.2 + keyword_boost * 0.15
    volume_penalty = 0.07 if input_data.transcriptLength < 300 else 0
    score = int(clamp(round((base - volume_penalty) * 100), 0, 100))
    feedback = (
        "설명 구조가 안정적입니다. 질문 유도 빈도를 현재 수준 이상 유지하세요."
        if score >= 80
        else "설명 밀도는 양호하지만 반복 구간이 길어집니다. 키워드 중심 정리를 늘려보세요."
        if score >= 60
        else "설명 대비 잡담/반복 비율이 높습니다. 핵심 개념 중심으로 문장 길이를 줄이세요."
    )
    return {"qualityScore": score, "explanationRatio": int(round(explanation_ratio * 100)), "feedback": feedback}


def predict_risk(input_data: RiskInput) -> dict[str, Any]:
    risk_raw = (
        (100 - input_data.averageScore) * 0.4
        + (100 - input_data.attendanceRate) * 0.3
        + (100 - input_data.classQualityScore) * 0.2
        + (100 - input_data.schoolEnvironmentScore) * 0.1
    )
    risk = int(clamp(round(risk_raw), 0, 100))
    dropout = int(clamp(round(risk * 0.72), 0, 100))
    level = "high" if risk >= 70 else "medium" if risk >= 40 else "low"
    return {"subjectRisk": risk, "dropoutProbability": dropout, "level": level}


def optimize_schedule(input_data: ScheduleInput) -> dict[str, Any]:
    weak_k = 100 - input_data.koreanLevel
    weak_m = 100 - input_data.mathLevel
    weak_e = 100 - input_data.englishLevel
    total = max(weak_k + weak_m + weak_e, 1)
    fatigue_factor = clamp(1 - input_data.fatigue / 140, 0.55, 1)
    effective_hours = max(round(input_data.studyHours * fatigue_factor * 10) / 10, 1)
    k = round(((weak_k / total) * effective_hours) * 10) / 10
    m = round(((weak_m / total) * effective_hours) * 10) / 10
    e = round(max(effective_hours - k - m, 0.5) * 10) / 10
    return {
        "effectiveHours": effective_hours,
        "routine": [
            f"국어 {k}h (개념 + 오답)",
            f"수학 {m}h (유형 반복 + 약점 단원)",
            f"영어 {e}h (독해 + 단어 회전)",
            "마감 20분: 오늘 학습 회고 및 내일 계획",
        ],
    }


def simulate_twin(input_data: TwinInput) -> dict[str, Any]:
    gain = input_data.planQuality * 0.12 + input_data.consistency * 0.18 - (100 - input_data.currentAverage) * 0.02
    predicted = int(clamp(round(input_data.currentAverage + gain * (input_data.weeks / 4)), 0, 100))
    delta = predicted - int(round(input_data.currentAverage))
    comment = (
        "현재 전략은 유의미한 상승이 예상됩니다."
        if delta >= 8
        else "완만한 상승이 예상됩니다. 복습 비율을 더 높이면 개선 폭이 커집니다."
        if delta >= 3
        else "상승 폭이 제한적입니다. 시간표 재배분 또는 피로도 관리가 필요합니다."
    )
    return {"predictedAverage": predicted, "delta": delta, "comment": comment}


def analyze_causal(input_data: CausalInput) -> dict[str, Any]:
    items = [
        ("출결", input_data.attendanceImpact),
        ("수업 품질", input_data.classQualityImpact),
        ("자기주도 학습", input_data.selfStudyImpact),
        ("학교 환경", input_data.environmentImpact),
    ]
    ranking = sorted(items, key=lambda x: x[1], reverse=True)
    top, second = ranking[0], ranking[1]
    return {
        "topDriver": top[0],
        "topWeight": top[1],
        "summary": f"{top[0]} 요인이 가장 큰 원인으로 추정됩니다. 다음 영향 요인은 {second[0]}입니다.",
        "ranking": ranking,
    }


def explain_prediction(input_data: ExplainInput) -> dict[str, int]:
    raw = {
        "attendance": 100 - input_data.attendance,
        "understanding": 100 - input_data.understanding,
        "fatigue": input_data.fatigue,
        "classQuality": 100 - input_data.classQuality,
    }
    total = max(sum(raw.values()), 1)
    return {k: int(round(v / total * 100)) for k, v in raw.items()}


_rate_buckets: dict[str, list[float]] = defaultdict(list)


def _rate_limit_exceeded(client_ip: str) -> bool:
    max_per_min = int(os.getenv("RATE_LIMIT_PER_MINUTE", 120))
    if max_per_min <= 0:
        return False
    window = 60.0
    now = time.time()
    cutoff = now - window
    bucket = _rate_buckets[client_ip]
    while bucket and bucket[0] < cutoff:
        bucket.pop(0)
    if len(bucket) >= max_per_min:
        return True
    bucket.append(now)
    return False


class _NeisCache:
    def __init__(self) -> None:
        self._ttl = float(os.getenv("NEIS_CACHE_TTL_SECONDS", 60))
        self._data: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        if self._ttl <= 0:
            return None
        ent = self._data.get("key")
        if not ent:
            return None
        exp, val = ent
        if time.time() > exp:
            del self._data[key]
            return None
        return val

    def set(self, key: str, val: Any) -> None:
        if self._ttl <= 0:
            return
        self._data[key] = (time.time() + self._ttl, val)


_neis_cache = _NeisCache()


def _neis_result_ok(payload: dict[str, Any]) -> None:
    res = payload.get("RESULT")
    if not isinstance(res, dict):
        return
    code = str(res.get("CODE", ""))
    if not code or code.startswith("INFO"):
        return
    msg = res.get("MESSAGE", "NEIS API 오류")
    raise HTTPException(status_code=502, detail=f"NEIS: {msg} ({code})")


async def verify_internal_api_key(request: Request) -> None:
    expected = os.getenv("INTERNAL_API_KEY", "").strip()
    if not expected:
        return
    got = (request.headers.get("X-Internal-Key") or "").strip()
    auth = request.headers.get("Authorization") or ""
    if auth.lower().startswith("bearer "):
        got = auth[7:].strip()
    if got != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing internal API key")


_cors_raw = os.getenv("CORS_ORIGINS", "*").strip()
if _cors_raw == "*":
    _allow_origins = ["*"]
    _allow_credentials = False
else:
    _allow_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()]
    if not _allow_origins:
        _allow_origins = ["*"]
        _allow_credentials = False
    else:
        _allow_credentials = True

logger = logging.getLogger("uvicorn.error")


def _deployment_security_issues() -> list[str]:
    issues: list[str] = []
    openai_ready = bool(os.getenv("OPENAI_API_KEY", "").strip())
    internal_key = bool(os.getenv("INTERNAL_API_KEY", "").strip())
    if openai_ready and not internal_key:
        issues.append(
            "OPENAI_API_KEY가 설정됐지만 INTERNAL_API_KEY가 비어 있습니다. "
            "공개 인터넷에 두면 /api/ai/chat, /api/stt/transcribe, /api/nlq/query가 "
            "무인증으로 OpenAI 비용을 유발할 수 있습니다."
        )
    if _cors_raw == "*" and openai_ready:
        issues.append(
            "CORS_ORIGINS=* 이고 OpenAI가 켜져 있습니다. "
            "프로덕션에서는 https://your-frontend.example 형태로 출처를 제한하세요."
        )
    return issues


app = FastAPI(title="Class Orbit API", version="0.1.0")


@app.on_event("startup")
async def _check_deployment_security() -> None:
    strict = os.getenv("APP_ENV", "").strip().lower() == "production"
    for issue in _deployment_security_issues():
        if strict:
            raise RuntimeError(f"Deployment security: {issue}")
        logger.warning("SECURITY: %s", issue)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path.startswith("/api"):
        ip = request.client.host if request.client else "unknown"
        if _rate_limit_exceeded(ip):
            return JSONResponse({"detail": "Too many requests"}, status_code=429)
    return await call_next(request)


@app.get("/api/health")
def health():
    neis_ready = bool(
        os.getenv("NEIS_API_KEY", "").strip()
        and os.getenv("NEIS_ATPT_OFCDC_SC_CODE", "").strip()
        and os.getenv("NEIS_SD_SCHUL_CODE", "").strip()
    )
    openai_ready = bool(os.getenv("OPENAI_API_KEY", "").strip())
    kess_stub = bool(os.getenv("KESS_API_KEY", "").strip())
    alimi_stub = bool(os.getenv("SCHOOL_ALIMI_API_KEY", "").strip())
    return {
        "ok": True,
        "service": "class-orbit-api",
        "version": "0.1.0",
        "integrations": {
            "neis_configured": neis_ready,
            "openai_configured": openai_ready,
            "kess": "stub_env_ready" if kess_stub else "sample_only",
            "school_alimi": "stub_env_ready" if alimi_stub else "sample_only",
            "risk_rl_shap": "simulation",
        },
        "security": {
            "cors_mode": "any" if _cors_raw == "*" else "allowlist",
            "rate_limit_per_minute": int(os.getenv("RATE_LIMIT_PER_MINUTE", 120)),
            "internal_api_key_required": bool(os.getenv("INTERNAL_API_KEY", "").strip()),
        },
    }


@app.post("/api/analysis/class-from-text")
def class_from_text(req: TranscriptRequest):
    derived = derive_class_input(req.transcript)
    result = analyze_class(derived["input"])
    return {"classInput": derived["input"], "meta": derived["meta"], "classResult": result}


@app.post("/api/pipeline/run")
def run_pipeline(req: PipelineRunRequest):
    derived = derive_class_input(req.transcript)
    class_input = derived["input"]
    class_result = analyze_class(class_input)

    linked_risk = req.risk_input.model_copy(update={"classQualityScore": class_result["qualityScore"]})
    risk_result = predict_risk(linked_risk)

    linked_schedule = req.schedule_input.model_copy(
        update={
            "koreanLevel": clamp(100 - risk_result["subjectRisk"] * 0.45, 35, 95),
            "mathLevel": clamp(100 - risk_result["subjectRisk"] * 0.65, 30, 95),
            "englishLevel": clamp(100 - risk_result["subjectRisk"] * 0.4, 35, 95),
            "fatigue": clamp(round((req.schedule_input.fatigue * 0.7 + (100 - class_result["qualityScore"]) * 0.3) * 10) / 10, 0, 100),
        }
    )
    schedule_result = optimize_schedule(linked_schedule)

    linked_twin = req.twin_input.model_copy(
        update={
            "planQuality": clamp(round(class_result["qualityScore"] * 0.55 + (100 - risk_result["subjectRisk"]) * 0.45), 35, 95),
            "consistency": clamp(round(48 + schedule_result["effectiveHours"] * 8), 35, 95),
        }
    )
    twin_result = simulate_twin(linked_twin)

    linked_causal = req.causal_input.model_copy(
        update={
            "attendanceImpact": clamp(round(25 + (100 - linked_risk.attendanceRate) * 0.8), 5, 60),
            "classQualityImpact": clamp(round((100 - class_result["qualityScore"]) * 0.7), 5, 60),
            "selfStudyImpact": clamp(round(18 + (100 - linked_twin.consistency) * 0.4), 5, 60),
            "environmentImpact": clamp(round(100 - linked_risk.schoolEnvironmentScore), 5, 40),
        }
    )
    causal_result = analyze_causal(linked_causal)

    linked_xai = req.xai_input.model_copy(
        update={
            "attendance": linked_risk.attendanceRate,
            "understanding": round((linked_schedule.koreanLevel + linked_schedule.mathLevel) / 2),
            "fatigue": linked_schedule.fatigue,
            "classQuality": class_result["qualityScore"],
        }
    )
    xai_result = explain_prediction(linked_xai)

    return {
        "classInput": class_input,
        "analysisMeta": derived["meta"],
        "classResult": class_result,
        "riskInput": linked_risk,
        "riskResult": risk_result,
        "scheduleInput": linked_schedule,
        "scheduleResult": schedule_result,
        "twinInput": linked_twin,
        "twinResult": twin_result,
        "causalInput": linked_causal,
        "causalResult": causal_result,
        "xaiInput": linked_xai,
        "xaiResult": xai_result,
    }


@app.get("/api/public/summary")
async def public_summary(
    atpt_code: Optional[str] = None,
    school_code: Optional[str] = None,
):
    key = os.getenv("NEIS_API_KEY")
    atpt = atpt_code or os.getenv("NEIS_ATPT_OFCDC_SC_CODE")
    school = school_code or os.getenv("NEIS_SD_SCHUL_CODE")
    if not (key and atpt and school):
        return {
            "source": "sample",
            "message": "NEIS 키/학교코드가 없어 샘플 데이터 반환",
            "schoolInfo": {"SCHUL_NM": "샘플고", "ATPT_OFCDC_SC_NM": "서울특별시교육청"},
            "scheduleCount": 5,
        }

    cache_key = f"summary|{atpt}|{school}"
    cached = _neis_cache.get(cache_key)
    if cached is not None:
        return cached

    url = "https://open.neis.go.kr/hub/schoolInfo"
    params = {
        "KEY": key,
        "Type": "json",
        "pIndex": 1,
        "pSize": 1,
        "ATPT_OFCDC_SC_CODE": atpt,
        "SD_SCHUL_CODE": school,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        res = await client.get(url, params=params)
    if res.status_code != 200:
        raise HTTPException(status_code=502, detail="NEIS 호출 실패")
    data = res.json()
    _neis_result_ok(data)
    row = (
        data.get(schoolInfo, [{}])[1].get(row, [{}])[0]
        if isinstance(data.get("schoolInfo"), list) and len(data.get("schoolInfo")) > 1
        else "{}"
    )
    out = {"source": "neis", "schoolInfo": row, "selected": {"atpt_code": atpt, "school_code": school}}
    _neis_cache.set(cache_key, out)
    return out


@app.get("/api/public/schools")
async def search_schools(
    query: str,
    atpt_code: Optional[str] = None,
    size: int = 20,
):
    key = os.getenv("NEIS_API_KEY")
    if not key:
        return {
            "source": "sample",
            "message": "NEIS_API_KEY가 없어 샘플 목록 반환",
            "schools": [
                {"ATPT_OFCDC_SC_CODE": "B10", "ATPT_OFCDC_SC_NM": "서울특별시교육청", "SD_SCHUL_CODE": "7010569", "SCHUL_NM": "서울고등학교"},
                {"ATPT_OFCDC_SC_CODE": "J10", "ATPT_OFCDC_SC_NM": "경기도교육청", "SD_SCHUL_CODE": "7530010", "SCHUL_NM": "수원고등학교"},
            ],
        }

    cache_key = f"schools|{query}|{atpt_code or ''}|{size}"
    cached = _neis_cache.get(cache_key)
    if cached is not None:
        return cached

    params = {
        "KEY": key,
        "Type": "json",
        "pIndex": 1,
        "pSize": max(min(size, 100), 1),
        "SCHUL_NM": query,
    }
    if atpt_code:
        params[ATPT_OFCDC_SC_CODE] = atpt_code

    async with httpx.AsyncClient(timeout=12) as client:
        res = await client.get("https://open.neis.go.kr/hub/schoolInfo", params=params)

    if res.status_code != 200:
        snippet = (res.text or '')[:200]
        raise HTTPException(
            status_code=502,
            detail=f"NEIS schoolInfo 조회 실패 (status={res.status_code}): {snippet}",
        )

    payload = res.json()
    _neis_result_ok(payload)
    rows = (
        payload.get(schoolInfo, [{}])[1].get(row, [])
        if isinstance(payload.get("schoolInfo"), list) and len(payload.get("schoolInfo")) > 1
        else "[]"
    )
    schools = [
        {
            ATPT_OFCDC_SC_CODE: r.get("ATPT_OFCDC_SC_CODE"),
            ATPT_OFCDC_SC_NM: r.get("ATPT_OFCDC_SC_NM"),
            SD_SCHUL_CODE: r.get("SD_SCHUL_CODE"),
            SCHUL_NM: r.get("SCHUL_NM"),
        }
        for r in rows
    ]
    out = {"source": "neis", "schools": schools, "count": len(schools)}
    _neis_cache.set(cache_key, out)
    return out


@app.get("/api/public/timetable")
async def school_timetable(
    atpt_code: str,
    school_code: str,
    grade: int = 1,
    cls: int = 1,
):
    key = os.getenv("NEIS_API_KEY")
    if not key:
        return {
            "source": "sample",
            "message": "NEIS_API_KEY가 없어 샘플 시간표 반환",
            "rows": [
                {"PERIO": 1, "ITRT_CNTNT": "국어"},
                {"PERIO": 2, "ITRT_CNTNT": "수학"},
                {"PERIO": 3, "ITRT_CNTNT": "영어"},
            ],
        }

    today = datetime.now().strftime("%Y%m%d")
    cache_key = f"{atpt_code}|{school_code}|{grade}|{cls}|{today}"
    cached = _neis_cache.get(cache_key)
    if cached is not None:
        return cached

    params = {
        "KEY": key,
        "Type": "json",
        "pIndex": 1,
        "pSize": 100,
        "ATPT_OFCDC_SC_CODE": atpt_code,
        "SD_SCHUL_CODE": school_code,
        "ALL_TI_YMD": today,
        "GRADE": str(grade),
        "CLASS_NM": str(cls),
    }

    async with httpx.AsyncClient(timeout=12) as client:
        res = await client.get("https://open.neis.go.kr/hub/hisTimetable", params=params)

    if res.status_code != 200:
        snippet = (res.text or '')[:200]
        raise HTTPException(
            status_code=502,
            detail=f"NEIS 시간표 조회 실패 (status={res.status_code}): {snippet}",
        )

    payload = res.json()
    _neis_result_ok(payload)
    rows = (
        payload.get(hisTimetable, [{}])[1].get(row, [])
        if isinstance(payload.get("hisTimetable"), list) and len(payload.get("hisTimetable")) > 1
        else "[]"
    )
    simplified = [{"PERIO": r.get("PERIO"), "ITRT_CNTNT": r.get("ITRT_CNTNT")} for r in rows]
    out = {"source": "neis", "rows": simplified, "count": len(simplified), "date": today}
    _neis_cache.set(cache_key, out)
    return out


@app.post("/api/public/kess")
async def kess_stats(req: KessStatsRequest):
    """
    교육통계(KESS) 서비스:
    - 실제 KESS Open API 연결 전/대회용 데모를 위해 샘플 기반 통계 형태를 제공합니다.
    - 추후 KESS_API_KEY 등이 준비되면 여기서 실 API로 교체하면 됩니다.
    """

    region = (req.region or "전국").strip() or "전국"
    year = int(req.year or datetime.now().year)
    grade = int(req.grade or 1)

    # 데모용 “교육격차/성취도” 지표 (지역/학년별로 약간 흔들리게)
    seed = sum(ord(c) for c in f"{region}-{year}-{grade}") % 17
    avg = clamp(72 - seed * 0.4 + grade * 0.8, 45, 90)
    gap = clamp(18 + seed * 0.7 - grade * 0.3, 6, 35)
    low_band = clamp(12 + seed * 0.5, 3, 30)
    high_band = clamp(22 - seed * 0.35, 8, 35)

    return {
        "source": "sample",
        "integration": "sample_only",
        "simulation": True,
        "region": region,
        "year": year,
        "grade": grade,
        "metrics": {
            "average_score": round(avg, 1),
            "regional_gap": round(gap, 1),
            "low_achievers_pct": round(low_band, 1),
            "high_achievers_pct": round(high_band, 1),
        },
        "role": "AI 모델 학습용 기준 데이터(데모)",
        "roadmap": "KESS_API_KEY 및 교육통계 오픈 API 스펙 확정 시 이 엔드포인트에서 실데이터로 교체",
    }


@app.post("/api/public/alimi")
async def school_alimi_environment(req: AlimiEnvRequest):
    """
    학교알리미(환경) 정보:
    - 공식 API/크롤링 연동 전, 환경 feature 형태의 샘플을 제공합니다.
    - 실제 연동 시 school_code 기반 매핑으로 교체 가능합니다.
    """

    school_name = (req.school_name or "선택 학교").strip()
    key = f"{req.atpt_code or ''}-{req.school_code or ''}-{school_name}"
    seed = sum(ord(c) for c in key) % 19

    teachers = int(clamp(45 + seed * 2.2, 20, 120))
    facility = int(clamp(60 + seed * 1.8, 35, 95))
    env = int(clamp(58 + seed * 1.6, 30, 92))

    return {
        "source": "sample",
        "integration": "sample_only",
        "simulation": True,
        "school": {"name": school_name, "atpt_code": req.atpt_code, "school_code": req.school_code},
        "features": {
            teacher_count: teachers,
            facility_score: facility,
            environment_score: env,
        },
        "role": "정확도 향상용 보조 데이터(데모)",
        "roadmap": "SCHOOL_ALIMI_API_KEY(가칭) 또는 공식 연동 스펙 확보 시 실데이터로 교체",
    }


@app.post("/api/models/risk/predict-sklearn")
async def predict_risk_sklearn(req: SklearnRiskPredictRequest):
    """
    scikit-learn 기반 리스크 예측 API (대회용/데모):
    - 현재는 서버 내 휴리스틱(predict_risk)로 동작하지만, 엔드포인트 형태를 고정해 둡니다.
    - 추후 RandomForest/GBM 모델을 로딩하는 방식으로 교체 가능합니다.
    """

    result = predict_risk(
        RiskInput(
            averageScore=req.averageScore,
            attendanceRate=req.attendanceRate,
            classQualityScore=req.classQualityScore,
            schoolEnvironmentScore=req.schoolEnvironmentScore,
        )
    )
    return {
        "engine": "simulated-sklearn",
        "simulation": True,
        "integration": "heuristic_only",
        "result": result,
        "roadmap": "학습된 모델 아티팩트(.pkl 등) 로딩으로 교체",
    }


@app.post("/api/rl/schedule/optimize-sb3")
async def optimize_schedule_sb3(req: RlScheduleRequest):
    """
    Stable-Baselines3 강화학습 최적화 API (대회용/데모):
    - 현재는 optimize_schedule로 동작(휴리스틱)하지만, RL 엔드포인트 형태를 고정합니다.
    """

    schedule = optimize_schedule(
        ScheduleInput(
            koreanLevel=req.koreanLevel,
            mathLevel=req.mathLevel,
            englishLevel=req.englishLevel,
            fatigue=req.fatigue,
            studyHours=req.studyHours,
        )
    )
    return {
        "engine": "simulated-sb3",
        "simulation": True,
        "integration": "heuristic_only",
        "objective": req.objective or "balanced",
        "result": schedule,
        "roadmap": "Stable-Baselines3 정책 학습 후 추론으로 교체",
    }


@app.post("/api/xai/shap")
async def shap_explain(req: ShapExplainRequest):
    """
    SHAP 기반 설명가능 AI API (대회용/데모):
    - 현재는 단순 feature 영향도 형태를 반환합니다.
    - 추후 shap 라이브러리로 모델 설명을 교체하면 됩니다.
    """

    # 영향도는 리스크에 기여하는 방향으로 정규화 (값이 낮을수록 리스크↑)
    raw = {
        "averageScore": 100 - req.averageScore,
        "attendanceRate": 100 - req.attendanceRate,
        "classQualityScore": 100 - req.classQualityScore,
        "schoolEnvironmentScore": 100 - req.schoolEnvironmentScore,
    }
    total = max(sum(raw.values()), 1)
    weights = {k: round(v / total, 4) for k, v in raw.items()}
    top = sorted(weights.items(), key=lambda x: x[1], reverse=True)[:3]
    return {
        "engine": "simulated-shap",
        "simulation": True,
        "integration": "heuristic_only",
        "weights": weights,
        "top": top,
        "roadmap": "shap 라이브러리 + 학습 모델로 실제 기여도 산출",
    }


@app.post("/api/ai/chat")
async def ai_chat(req: ChatRequest, _auth: None = Depends(verify_internal_api_key)):
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    if not api_key:
        return {
            "answer": (
                "OPENAI_API_KEY가 설정되지 않았습니다.\n"
                f"질문 요약: {req.message[:120]}\n"
                "키 설정 후 동일 엔드포인트로 실연결됩니다."
            )
        }

    messages = [{"role": "system", "content": "You are an educational AI assistant."}]
    messages.extend([m.model_dump() for m in req.history[-10:]])
    messages.append({"role": "user", "content": req.message})

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "temperature": 0.4}
    async with httpx.AsyncClient(timeout=30) as client:
        res = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
    if res.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"OpenAI 호출 실패: {res.text[:200]}")
    data = res.json()
    content = data["choices"][0]["message"]["content"]
    return {"answer": content}


@app.post("/api/stt/transcribe")
async def stt_transcribe(
    file: UploadFile = File(...),
    language: Optional[str] = Form(default=None),
    _auth: None = Depends(verify_internal_api_key),
):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY가 설정되지 않았습니다.")

    # Whisper transcription endpoint
    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {api_key}"}

    # 최신/기본 Whisper 모델명 호환 (서버에서 실패 시 에러 메시지로 확인 가능)
    model = os.getenv("OPENAI_WHISPER_MODEL", "whisper-1")

    form_data = {"model": model}
    if language and language.strip():
        form_data[language] = language.strip()

    file_bytes = await file.read()
    files = {"file": (file.filename or "audio", file_bytes, file.content_type or "application/octet-stream")}

    async with httpx.AsyncClient(timeout=60) as client:
        res = await client.post(url, headers=headers, data=form_data, files=files)

    if res.status_code >= 400:
        snippet = (res.text or "")[:240]
        raise HTTPException(status_code=502, detail=f"STT 실패 (status={res.status_code}): {snippet}")

    payload = res.json()
    text = payload.get("text") or ""
    return {"transcript": text, "model": model}


# ──────────────────────────────────────────────
# NEW MODELS  (제안서 기반 확장 기능)
# ──────────────────────────────────────────────

class SubjectScore(BaseModel):
    subject: str
    score: float
    importance: float = 1.0


class PathwayRequest(BaseModel):
    grade: int = 2
    subjects: list[SubjectScore] = Field(default_factory=list)
    goal: Optional[str] = None          # 수능, 내신, 기초, 심화
    studyHoursPerDay: float = 3.0


class WarningCheckRequest(BaseModel):
    recentScores: list[float] = Field(default_factory=list)   # 최근 최대 5개
    attendanceRate: float
    submissionRate: float = 100.0
    engagementScore: float = 70.0      # 0~100 (수업 참여도 자체 평가)


class EquityIndexRequest(BaseModel):
    region: Optional[str] = None
    schoolType: Optional[str] = None   # 고등, 중학, 초등
    year: Optional[int] = None


class ResourceMatchRequest(BaseModel):
    subject: str
    level: float = 60.0                # 현재 성취도 0~100
    grade: int = 2
    formatPref: Optional[str] = None   # video, text, practice


class NlqRequest(BaseModel):
    query: str
    context: Optional[str] = None      # risk | schedule | equity | pathway | None


# ──────────────────────────────────────────────
# 1. 학습 경로 엔진  /api/pathway/recommend
# ──────────────────────────────────────────────

_SUBJECT_PREREQUISITES: dict[str, list[str]] = {
    "수학": ["수와 연산", "대수", "함수", "기하", "확률/통계"],
    "영어": ["어휘/발음", "문법", "독해", "듣기", "쓰기"],
    "국어": ["문학", "독서(비문학)", "문법/어휘", "쓰기/화법"],
    "과학": ["물리", "화학", "생명과학", "지구과학"],
    "사회": ["한국사", "세계사", "지리", "일반사회"],
}

_RESOURCES_MAP: dict[str, str] = {
    "수학": "EBS 수학 개념완성",
    "영어": "EBS 영어 듣기/독해",
    "국어": "EBS 국어 독서, 문학",
    "과학": "EBS 과학탐구",
    "사회": "EBS 사회탐구",
}


@app.post("/api/pathway/recommend")
def pathway_recommend(req: PathwayRequest):
    """
    학습 경로 엔진 – 취약 과목 우선순위화 + 단계별 학습 경로 제안.
    공공 교육과정 단원 구조를 기반으로 '다음에 무엇을 해야 하는지' 안내합니다.
    """

    if not req.subjects:
        req.subjects = [
            SubjectScore(subject="수학", score=62, importance=1.2),
            SubjectScore(subject="영어", score=71, importance=1.0),
            SubjectScore(subject="국어", score=74, importance=1.0),
        ]

    goal = (req.goal or "내신").strip()

    # 취약도 = (100 - score) × importance
    weaknesses = sorted(
        req.subjects,
        key=lambda s: (100 - s.score) * s.importance,
        reverse=True,
    )

    path_steps = []
    for rank, sub in enumerate(weaknesses[:4], start=1):
        units = _SUBJECT_PREREQUISITES.get(sub.subject, ["기초 개념", "심화 응용"])
        threshold = 70
        deficit = clamp(threshold - sub.score, 0, 70)
        weeks_needed = int(clamp(round(deficit / 8), 1, 10))
        weak_units = units[: max(2, int(len(units) * (1 - sub.score / 100)))]
        resource = _RESOURCES_MAP.get(sub.subject, "EBS 무료 강좌")

        path_steps.append({
            "rank": rank,
            "subject": sub.subject,
            "currentScore": sub.score,
            "targetScore": min(sub.score + deficit * 0.8, 95),
            "weeklyHours": round(
                (req.studyHoursPerDay * 7 * (100 - sub.score) * sub.importance)
                / max(sum((100 - s.score) * s.importance for s in weaknesses), 1),
                1,
            ),
            "focusUnits": weak_units,
            "estimatedWeeks": weeks_needed,
            "publicResource": resource,
            "tip": (
                f"{sub.subject} 기초 단원({weak_units[0]})부터 확실히 잡으세요."
                if sub.score < 60
                else f"{sub.subject} 취약 단원을 집중 반복하면 {weeks_needed}주 내 향상 가능합니다."
            ),
        })

    total_weeks = max(s["estimatedWeeks"] for s in path_steps) if path_steps else 4
    return {
        "goal": goal,
        "grade": req.grade,
        "studyHoursPerDay": req.studyHoursPerDay,
        "totalEstimatedWeeks": total_weeks,
        "pathSteps": path_steps,
        "summary": (
            f"최우선 과목은 {weaknesses[0].subject}입니다."
            f"{goal} 목표 기준으로 {total_weeks}주 집중 플랜을 제안합니다."
        ),
    }


# ──────────────────────────────────────────────
# 2. 조기 경보 시스템  /api/warning/check
# ──────────────────────────────────────────────

@app.post("/api/warning/check")
def warning_check(req: WarningCheckRequest):
    """
    조기 경보 시스템 – 성적 추이, 출결, 참여도를 종합해 위험 수준과 개입 방향을 제안합니다.
    """

    scores = [clamp(s, 0, 100) for s in (req.recentScores or [70, 68, 65])[-5:]]

    # 성적 추이 (하락폭)
    trend = 0.0
    if len(scores) >= 2:
        trend = scores[-1] - scores[0]           # 음수 = 하락

    avg_score = sum(scores) / len(scores)
    score_variance = (
        sum((s - avg_score) ** 2 for s in scores) / len(scores)
    ) ** 0.5

    "# 위험 지수 (0~100)"
    risk_score = clamp(
        (100 - avg_score) * 0.35
        + max(-trend, 0) * 1.5
        + (100 - req.attendanceRate) * 0.25
        + (100 - req.submissionRate) * 0.15
        + (100 - req.engagementScore) * 0.15
        + score_variance * 0.3,
        0,
        100,
    )

    level = "high" if risk_score >= 65 else "medium" if risk_score >= 35 else "low"

    triggers: list[str] = []
    if avg_score < 60:
        triggers.append("평균 성적 60점 미만")
    if trend < -8:
        triggers.append(f"최근 성적 {abs(trend):.0f}점 하락 추세")
    if req.attendanceRate < 85:
        triggers.append(f"출결률 {req.attendanceRate:.0f}% (기준 85% 미만)")
    if req.submissionRate < 80:
        triggers.append(f"과제 제출률 {req.submissionRate:.0f}% 저조")
    if req.engagementScore < 55:
        triggers.append("수업 참여도 낮음")
    if score_variance > 12:
        triggers.append(f"점수 편차 {score_variance:.1f} 높음 (학습 불안정)")

    actions = {
        "high": [
            "담당 교사, 상담사와 즉시 면담 권장",
            "학습 부진 원인 파악(학습 결손 vs 심리적 요인)",
            "방과후 보충 수업 또는 멘토링 연결",
            "학부모 알림 발송",
        ],
        "medium": [
            "취약 과목 집중 복습 스케줄 재조정",
            "2주 내 교사 점검 면담",
            "자기주도 학습 습관 점검",
        ],
        "low": [
            "현재 학습 방향 유지",
            "주간 자기 점검 권장",
        ],
    }

    return {
        "riskScore": round(risk_score, 1),
        "level": level,
        "trend": round(trend, 1),
        "avgScore": round(avg_score, 1),
        "triggers": triggers if triggers else ["현재 주요 위험 지표 없음"],
        "recommendedActions": actions[level],
        "summary": (
            f"위험 수준 [{level.upper()}] – 위험 지수 {risk_score:.0f}/100. "
            + (f"주요 원인: {triggers[0]}" if triggers else "안정적인 학습 상태입니다.")
        ),
    }


# ──────────────────────────────────────────────
# 3. 교육 형평성 지수  /api/equity/index
# ──────────────────────────────────────────────

_REGION_PROFILES: dict[str, dict] = {
    "서울": {"avg": 74, "gap": 18, "resource": 88, "infra": 85},
    "경기": {"avg": 72, "gap": 20, "resource": 82, "infra": 80},
    "부산": {"avg": 70, "gap": 22, "resource": 76, "infra": 74},
    "인천": {"avg": 69, "gap": 23, "resource": 75, "infra": 73},
    "대구": {"avg": 70, "gap": 21, "resource": 77, "infra": 75},
    "광주": {"avg": 68, "gap": 24, "resource": 72, "infra": 70},
    "대전": {"avg": 71, "gap": 20, "resource": 79, "infra": 77},
    "전남": {"avg": 63, "gap": 29, "resource": 58, "infra": 55},
    "전북": {"avg": 64, "gap": 28, "resource": 60, "infra": 57},
    "경북": {"avg": 64, "gap": 27, "resource": 61, "infra": 59},
    "경남": {"avg": 65, "gap": 26, "resource": 63, "infra": 61},
    "충북": {"avg": 65, "gap": 26, "resource": 64, "infra": 62},
    "충남": {"avg": 64, "gap": 27, "resource": 62, "infra": 60},
    "강원": {"avg": 63, "gap": 29, "resource": 57, "infra": 54},
    "제주": {"avg": 66, "gap": 25, "resource": 67, "infra": 65},
    "전국": {"avg": 68, "gap": 23, "resource": 70, "infra": 68},
}

_SCHOOL_TYPE_OFFSET: dict[str, float] = {
    "고등": 0.0,
    "중학": 1.5,
    "초등": 3.0,
}


@app.post("/api/equity/index")
def equity_index(req: EquityIndexRequest):
    """
    교육 형평성 지수 – 지역, 학교급별 성취도 격차 및 교육 자원 불균형을 수치화합니다.
    공공 교육통계 데이터(KESS) 연동 전 샘플 기반으로 동작하며, 형태는 실데이터와 동일합니다.
    """

    region = (req.region or "전국").strip()
    school_type = (req.schoolType or "고등").strip()
    year = int(req.year or datetime.now().year)

    profile = _REGION_PROFILES.get(region, _REGION_PROFILES["전국"])
    national = _REGION_PROFILES["전국"]
    offset = _SCHOOL_TYPE_OFFSET.get(school_type, 0.0)

    avg = clamp(profile["avg"] + offset, 40, 98)
    gap = clamp(profile["gap"] - offset * 0.3, 5, 40)
    resource_idx = clamp(profile["resource"], 30, 100)
    infra_idx = clamp(profile["infra"], 30, 100)

    # 형평성 점수: 격차가 낮고, 자원, 인프라가 높을수록 높음
    equity_score = int(clamp(
        (1 - gap / 50) * 40
        + (resource_idx / 100) * 35
        + (infra_idx / 100) * 25,
        0, 100,
    ))

    national_gap_vs_avg = round(avg - national["avg"], 1)
    equity_gap_vs_national = round(equity_score - int(
        (1 - national["gap"] / 50) * 40
        + (national["resource"] / 100) * 35
        + (national["infra"] / 100) * 25
    ), 1)

    grade = (
        "A (우수)" if equity_score >= 80
        else "B (양호)" if equity_score >= 65
        else "C (보통)" if equity_score >= 50
        else "D (취약)"
    )

    recommendations: list[str] = []
    if gap > 25:
        recommendations.append("방과후 학교 및 기초학력 보충 프로그램 확대 필요")
    if resource_idx < 65:
        recommendations.append("교육 콘텐츠, 강사 자원 배분 집중 지원 필요")
    if infra_idx < 60:
        recommendations.append("디지털 교육 인프라 투자 우선 순위 대상")
    if national_gap_vs_avg < -3:
        recommendations.append("지역 평균 성취도가 전국 대비 낮음 → 집중 지원 필요")
    if not recommendations:
        recommendations.append("현재 교육 형평성 수준 유지 및 지속 모니터링 권장")

    return {
        "source": "sample",
        "simulation": True,
        "region": region,
        "schoolType": school_type,
        "year": year,
        "equityScore": equity_score,
        "grade": grade,
        "metrics": {
            "averageScore": round(avg, 1),
            "achievementGap": round(gap, 1),
            "resourceIndex": round(resource_idx, 1),
            "infraIndex": round(infra_idx, 1),
        },
        "vsNational": {
            "avgDiff": national_gap_vs_avg,
            "equityDiff": equity_gap_vs_national,
        },
        "recommendations": recommendations,
        "summary": (
            f"{region} {school_type} 형평성 지수 {equity_score}/100 ({grade}). "
            f"전국 평균 대비 성취도 {'+' if national_gap_vs_avg >= 0 else ''}{national_gap_vs_avg}점."
        ),
    }


# ──────────────────────────────────────────────
# 4. 교육 자원 매칭  /api/resources/match
# ──────────────────────────────────────────────

_PUBLIC_RESOURCES: list[dict] = [
    # 수학
    {"subject": "수학", "title": "EBS 수학 개념완성", "type": "video", "cost": "무료",
     "url": "https://www.ebs.co.kr", "minLevel": 0, "maxLevel": 70, "difficulty": "기초~중급"},
    {"subject": "수학", "title": "EBS 수능특강 수학", "type": "video", "cost": "무료",
     "url": "https://www.ebs.co.kr", "minLevel": 65, "maxLevel": 100, "difficulty": "중급~고급"},
    {"subject": "수학", "title": "K-MOOC 수학적 사고", "type": "mooc", "cost": "무료",
     "url": "https://www.kmooc.kr", "minLevel": 50, "maxLevel": 100, "difficulty": "중급"},
    # 영어
    {"subject": "영어", "title": "EBS 영어 듣기/독해", "type": "video", "cost": "무료",
     "url": "https://www.ebs.co.kr", "minLevel": 0, "maxLevel": 75, "difficulty": "기초~중급"},
    {"subject": "영어", "title": "EBS 수능특강 영어", "type": "video", "cost": "무료",
     "url": "https://www.ebs.co.kr", "minLevel": 65, "maxLevel": 100, "difficulty": "중급~고급"},
    {"subject": "영어", "title": "K-MOOC 비즈니스 영어", "type": "mooc", "cost": "무료",
     "url": "https://www.kmooc.kr", "minLevel": 60, "maxLevel": 100, "difficulty": "중급"},
    # 국어
    {"subject": "국어", "title": "EBS 국어 독서, 문학", "type": "video", "cost": "무료",
     "url": "https://www.ebs.co.kr", "minLevel": 0, "maxLevel": 80, "difficulty": "기초~중급"},
    {"subject": "국어", "title": "EBS 수능특강 국어", "type": "video", "cost": "무료",
     "url": "https://www.ebs.co.kr", "minLevel": 65, "maxLevel": 100, "difficulty": "중급~고급"},
    # 과학
    {"subject": "과학", "title": "EBS 과학탐구 기초", "type": "video", "cost": "무료",
     "url": "https://www.ebs.co.kr", "minLevel": 0, "maxLevel": 70, "difficulty": "기초"},
    {"subject": "과학", "title": "K-MOOC 기초과학 시리즈", "type": "mooc", "cost": "무료",
     "url": "https://www.kmooc.kr", "minLevel": 40, "maxLevel": 100, "difficulty": "기초~중급"},
    # 사회
    {"subject": "사회", "title": "EBS 사회탐구", "type": "video", "cost": "무료",
     "url": "https://www.ebs.co.kr", "minLevel": 0, "maxLevel": 80, "difficulty": "기초~중급"},
    # 공통
    {"subject": "전체", "title": "국립중앙도서관 디지털 자료실", "type": "library", "cost": "무료",
     "url": "https://www.nl.go.kr", "minLevel": 0, "maxLevel": 100, "difficulty": "전 수준"},
    {"subject": "전체", "title": "KOCW 공개강의", "type": "mooc", "cost": "무료",
     "url": "http://www.kocw.net", "minLevel": 60, "maxLevel": 100, "difficulty": "대학 수준"},
]


@app.post("/api/resources/match")
def resources_match(req: ResourceMatchRequest):
    """
    교육 자원 매칭 – 과목, 수준에 맞는 공공 무료 학습 자원을 추천합니다.
    EBS, K-MOOC, KOCW, 국립도서관 등 공공 자원 중심으로 비용 부담 없이 접근 가능한 목록을 반환합니다.
    """

    subject_norm = req.subject.strip()
    level = clamp(req.level, 0, 100)
    fmt = (req.formatPref or "").strip().lower()

    matched = [
        r for r in _PUBLIC_RESOURCES
        if (r["subject"] == subject_norm or r["subject"] == "전체")
        and r["minLevel"] <= level <= r["maxLevel"] + 15
        and (not fmt or r["type"] == fmt or r["subject"] == "전체")
    ]

    # 수준 거리 기반 정렬 (가까울수록 상위)
    matched.sort(key=lambda r: abs((r["minLevel"] + r["maxLevel"]) / 2 - level))

    if not matched:
        matched = [r for r in _PUBLIC_RESOURCES if r["subject"] == "전체"]

    return {
        "subject": subject_norm,
        "level": level,
        "grade": req.grade,
        "matchedCount": len(matched),
        "resources": matched[:6],
        "summary": (
            f"{subject_norm} 수준 {level:.0f}점 기준으로 {len(matched[:6])}개 공공 학습 자원을 매칭했습니다. "
            "모두 무료로 이용 가능합니다."
        ),
    }


# ──────────────────────────────────────────────
# 5. 자연어 데이터 질의  /api/nlq/query
# ──────────────────────────────────────────────

_NLQ_SYSTEM_PROMPT = """당신은 공공 교육 데이터 분석 AI 어시스턴트입니다.
사용자의 자연어 질문을 해석하고, 다음 분석 도메인 중 적절한 것으로 분류한 뒤 JSON 형태로 답변하세요.

도메인: risk(격차/위험도), pathway(학습경로), equity(형평성), resources(학습자원), schedule(시간표), general(일반)

반드시 아래 JSON 형식으로만 응답하세요:
{
  "domain": <도메인>,
  "intent": <한 줄 의도 요약>,
  "keyEntities": {"subject": ..., "region": ..., "grade": ..., other: ...},
  "answer": <명확하고 친절한 한국어 답변 (2~4문장)>,
  "suggestedActions": ["<다음 단계 1>", "<다음 단계 2>"]
}
"""


@app.post("/api/nlq/query")
async def nlq_query(req: NlqRequest, _auth: None = Depends(verify_internal_api_key)):
    """
    자연어 데이터 질의(NLQ) – 복잡한 쿼리 없이 교육 데이터에 대해 자연어로 질문하고 인사이트를 얻습니다.
    OpenAI API를 사용하며, 키가 없는 경우 시뮬레이션 응답을 반환합니다.
    """

    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    if not api_key:
        # 시뮬레이션 fallback
        sample_domain = "risk" if any(w in req.query for w in ["위험", "격차", "성적"]) \
            else "equity" if any(w in req.query for w in ["지역", "형평", "불평등"]) \
            else "pathway" if any(w in req.query for w in ["경로", "공부", "순서"]) \
            else "general"
        return {
            "simulation": True,
            "domain": sample_domain,
            "intent": f"'{req.query[:40]}' 질문 분석 (시뮬레이션)",
            "keyEntities": {},
            "answer": (
                f"OPENAI_API_KEY가 설정되지 않아 시뮬레이션으로 응답합니다.\n"
                f"질문 도메인: {sample_domain}. "
                "실제 키 연결 후 정확한 데이터 인사이트를 제공합니다."
            ),
            "suggestedActions": [
                "backend/.env 파일에 OPENAI_API_KEY 설정",
                "동일 질문을 다시 시도",
            ],
        }

    context_hint = f"\n추가 컨텍스트: 사용자는 [{req.context}] 도메인 화면을 보고 있습니다." if req.context else ""
    user_msg = f"{req.query}{context_hint}"

    messages = [
        {"role": "system", "content": _NLQ_SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "temperature": 0.2, "response_format": {"type": "json_object"}}

    async with httpx.AsyncClient(timeout=25) as client:
        res = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

    if res.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"NLQ OpenAI 호출 실패: {res.text[:200]}")

    raw = res.json()["choices"][0]["message"]["content"]
    try:
        import json as _json
        parsed = _json.loads(raw)
    except Exception:
        parsed = {"domain": "general", "intent": "파싱 실패", "answer": raw, "suggestedActions": []}

    parsed["simulation"] = False
    return parsed
