"""Conservative quote restoration for corrupted Python sources."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SKIP_PREFIXES = (
    "from ",
    "import ",
    "class ",
    "def ",
    "@",
    "#",
    "try:",
    "except",
    "async def ",
)


def should_skip_line(line: str) -> bool:
    stripped = line.lstrip()
    if not stripped:
        return True
    if stripped.startswith(SKIP_PREFIXES):
        return True
    if "->" in line and "def " in line:
        return True
    if "Optional[" in line or "list[" in line or "dict[" in line or "Field(" in line:
        return True
    if stripped.startswith('"""') or '"""' in stripped:
        return True
    if re.match(r"\w+:\s*(float|int|str|bool|Optional|list|dict|Any)\b", stripped):
        return True
    if re.match(r"\w+:\s*(float|int|str|bool|Optional|list|dict|Any)\s*=", stripped):
        return True
    if re.match(r"\w+:\s*[A-Z][a-zA-Z0-9_]*\b", stripped):
        return True
    return False


def fix_getenv(text: str) -> str:
    def repl(m: re.Match[str]) -> str:
        var, default = m.group(1), m.group(2).strip()
        if default == "":
            d = '""'
        elif default == "*":
            d = '"*"'
        elif re.fullmatch(r"-?\d+(\.\d+)?", default):
            d = default
        elif default == ",":
            d = '","'
        else:
            d = f'"{default}"'
        return f'os.getenv("{var}", {d})'

    text = re.sub(r"os\.getenv\(([A-Z][A-Z0-9_]*),\s*([^)]*)\)", repl, text)
    return re.sub(r"os\.getenv\(([A-Z][A-Z0-9_]*)\)", r'os.getenv("\1")', text)


def fix_paths_and_urls(text: str) -> str:
    text = re.sub(
        r"@app\.(get|post|put|delete)\((/[^)]+)\)",
        r'@app.\1("\2")',
        text,
    )
    text = re.sub(r"@app\.middleware\((http)\)", r'@app.middleware("\1")', text)
    text = re.sub(r"\.startswith\((/api)\)", r'.startswith("\1")', text)
    text = re.sub(r"client\.(get|post)\((/[^)]+)\)", r'client.\1("\2")', text)
    text = re.sub(
        r"(?<== )https?://[^\s,\)\"']+",
        lambda m: f'"{m.group(0)}"',
        text,
    )
    return text


def fix_headers_and_attrs(text: str) -> str:
    text = re.sub(r"request\.headers\.get\(([A-Za-z-]+)\)", r'request.headers.get("\1")', text)
    text = re.sub(r"\.get\(([A-Z][A-Z0-9_]*)\)", r'.get("\1")', text)
    text = re.sub(r"\.get\(([a-z][a-zA-Z0-9_]*)\)", r'.get("\1")', text)
    text = re.sub(r"\.get\(([a-z][a-zA-Z0-9_]*),\s*\)", r'.get("\1", "")', text)
    text = re.sub(r"(?<!\[)\[([a-z][a-zA-Z0-9_]*)\]", r'["\1"]', text)
    text = re.sub(r"(?<!\[)\[([A-Z][A-Z0-9_]*)\]", r'["\1"]', text)
    text = re.sub(r"payload\.get\(text\) or\s*$", 'payload.get("text") or ""', text, flags=re.M)
    text = re.sub(
        r"auth = request\.headers\.get\(Authorization\) or\s*$",
        'auth = request.headers.get("Authorization") or ""',
        text,
        flags=re.M,
    )
    text = re.sub(r"res\.text or \)\[:", 'res.text or "")[:', text)
    return text


def fix_known_literals(text: str) -> str:
    reps = [
        ("parent.parent / .env)", 'parent.parent / ".env")'),
        ("__import__(re)", '__import__("re")'),
        (".split(r[.!?\\n]+, clean)", '.split(r"[.!?\\n]+", clean)'),
        (".sub(r\\s+,  , s)", '.sub(r"\\s+", "  ", s)'),
        ("EXPLAIN_WORDS = [정리, 핵심, 개념, 이유, 공식, 원리, 따라서, because, therefore, concept]",
         'EXPLAIN_WORDS = ["정리", "핵심", "개념", "이유", "공식", "원리", "따라서", "because", "therefore", "concept"]'),
        ("CHAT_WORDS = [농담, 잡담, 딴얘기, 잠깐, 쉬자, 웃음, ㅋㅋ, ㅎㅎ]",
         'CHAT_WORDS = ["농담", "잡담", "딴얘기", "잠깐", "쉬자", "웃음", "ㅋㅋ", "ㅎㅎ"]'),
        ('QUESTION_WORDS = [?, 질문, 이해, 왜, 어떻게, what, why, how]',
         'QUESTION_WORDS = ["?", "질문", "이해", "왜", "어떻게", "what", "why", "how"]'),
        ("KEYWORDS = [학습, 성적, 분석, 피드백, 예측, 복습, 전략, 수업, 위험도, time, model]",
         'KEYWORDS = ["학습", "성적", "분석", "피드백", "예측", "복습", "전략", "수업", "위험도", "time", "model"]'),
        ("FastAPI(title=Class Orbit API, version=0.1.0)", 'FastAPI(title="Class Orbit API", version="0.1.0")'),
        ("allow_methods=[*]", 'allow_methods=["*"]'),
        ("allow_headers=[*]", 'allow_headers=["*"]'),
        ("_allow_origins = [*]", '_allow_origins = ["*"]'),
        ("_cors_raw == *", '_cors_raw == "*"'),
        ("if _cors_raw == *", 'if _cors_raw == "*"'),
        ("_cors_raw.split(,)", '_cors_raw.split(",")'),
        ("else unknown", 'else "unknown"'),
        ("auth.lower().startswith(bearer )", 'auth.lower().startswith("bearer ")'),
        ("detail=Invalid or missing internal API key", 'detail="Invalid or missing internal API key"'),
        ("{detail: Too many requests}", '{"detail": "Too many requests"}'),
        ("strftime(%Y%m%d)", 'strftime("%Y%m%d")'),
        ("level = high if", 'level = "high" if'),
        ("else medium if", 'else "medium" if'),
        ("else low", 'else "low"'),
        ("code.startswith(INFO)", 'code.startswith("INFO")'),
        ("res.get(MESSAGE, NEIS API 오류)", 'res.get("MESSAGE", "NEIS API 오류")'),
        ('{role: system, content: You are an educational AI assistant.}',
         '{"role": "system", "content": "You are an educational AI assistant."}'),
        ('{role: user, content: req.message}', '{"role": "user", "content": req.message}'),
        ('{model: model, messages: messages, temperature: 0.4}',
         '{"model": model, "messages": messages, "temperature": 0.4}'),
        ('{type: json_object}', '{"type": "json_object"}'),
        ("(req.formatPref or ).strip()", '(req.formatPref or "").strip()'),
        ('if req.context else ', 'if req.context else ""'),
        ('parsed[simulation] = False', 'parsed["simulation"] = False'),
        ('{domain: general, intent: 파싱 실패, answer: raw, suggestedActions: []}',
         '{"domain": "general", "intent": "파싱 실패", "answer": raw, "suggestedActions": []}'),
        ("client.get(/api/health)", 'client.get("/api/health")'),
        ("client.post(/api/public/kess, json={region: 전국, year: 2026, grade: 1})",
         'client.post("/api/public/kess", json={"region": "전국", "year": 2026, "grade": 1})'),
        ("client.post(\n        /api/models/risk/predict-sklearn,",
         'client.post(\n        "/api/models/risk/predict-sklearn",'),
        ('assert body.get(ok)', 'assert body.get("ok")'),
        ('assert integrations in body', 'assert "integrations" in body'),
        ('assert body[integrations].get(kess)', 'assert body["integrations"].get("kess")'),
        ("== sample_only", '== "sample_only"'),
        ('assert data.get(source)', 'assert data.get("source")'),
        ('assert data.get(integration)', 'assert data.get("integration")'),
        ('assert data.get(simulation)', 'assert data.get("simulation")'),
        ('assert r.json().get(simulation)', 'assert r.json().get("simulation")'),
        ("== sample", '== "sample"'),
        ("{Authorization: fBearer", '{"Authorization": f"Bearer'),
        ("Content-Type: application/json", '"Content-Type": "application/json"'),
        ("detail=fNEIS:", 'detail=f"NEIS:'),
        ("detail=fNEIS schoolInfo", 'detail=f"NEIS schoolInfo'),
        ("detail=fNEIS 시간표", 'detail=f"NEIS 시간표'),
        ("detail=fOpenAI", 'detail=f"OpenAI'),
        ("detail=fSTT", 'detail=f"STT'),
        ("detail=fNLQ", 'detail=f"NLQ'),
        ("cache_key = fsummary|", 'cache_key = f"summary|'),
        ("cache_key = fschools|", 'cache_key = f"schools|'),
        ("raise HTTPException(status_code=400, detail=OPENAI_API_KEY가", 'raise HTTPException(status_code=400, detail="OPENAI_API_KEY가'),
        ("{file: (file.filename or audio,", '{"file": (file.filename or "audio",'),
        ("file.content_type or application/octet-stream)", 'file.content_type or "application/octet-stream")'),
        ("_NLQ_SYSTEM_PROMPT = 당신은", '_NLQ_SYSTEM_PROMPT = """당신은'),
        ("suggestedActions: [<다음 단계 1>, <다음 단계 2>]\n}\n\n\n",
         'suggestedActions: ["<다음 단계 1>", "<다음 단계 2>"]\n}\n"""\n\n'),
    ]
    for old, new in reps:
        text = text.replace(old, new)
    return text


def quote_dict_keys_line(line: str) -> str:
    if line.lstrip().startswith("def "):
        return line
    line = re.sub(r"\{([a-z][a-zA-Z0-9_]*):", r'{"\1":', line)
    line = re.sub(r",\s*([a-z][a-zA-Z0-9_]*):", r', "\1":', line)
    line = re.sub(r"\{([A-Z][A-Z0-9_]*):", r'{"\1":', line)
    line = re.sub(r",\s*([A-Z][A-Z0-9_]*):", r', "\1":', line)
    return line


def fix_fstrings(text: str) -> str:
    text = re.sub(r"\bf\{", 'f"{', text)
    return re.sub(r"\bf([가-힣])", r'f"\1', text)


def fix_line(line: str) -> str:
    if should_skip_line(line):
        return line

    line = fix_fstrings(line)
    line = quote_dict_keys_line(line)
    line = re.sub(r"^(\s+)([a-z][a-zA-Z0-9_]*)(\s*):", r'\1"\2"\3:', line)
    line = re.sub(r"^(\s+)([A-Z][A-Z0-9_]*)(\s*):", r'\1"\2"\3:', line)

    line = re.sub(
        r"\(([가-힣A-Za-z][가-힣A-Za-z0-9 /]*),\s",
        lambda m: f'("{m.group(1)}", ',
        line,
    )

    def quote_value(m: re.Match[str]) -> str:
        prefix, val, suffix = m.group(1), m.group(2).strip(), m.group(3)
        if not val:
            return m.group(0)
        if val[0] in "\"'{[" or val.startswith("f\""):
            return m.group(0)
        if re.fullmatch(r"-?\d+(\.\d+)?", val):
            return m.group(0)
        if val in {"True", "False", "None"}:
            return m.group(0)
        if re.search(r"[()\[\].]", val) and not re.search(r"[가-힣]", val):
            return m.group(0)
        if any(val.startswith(p) for p in ("req.", "os.", "clamp", "round", "int(", "float(", "bool(", "derived", "result", "class_", "linked_", "schedule_", "risk_", "twin_", "causal_", "xai_", "payload", "res.", "data.", "client.", "f\"", "max(", "min(", "sum(", "len(", "sorted(", "any(", "all(", "str(", "list(", "dict(", "SubjectScore", "RiskInput", "ScheduleInput", "_REGION_PROFILES", "_PUBLIC_RESOURCES", "_SUBJECT_PREREQUISITES", "_RESOURCES_MAP", "_SCHOOL_TYPE_OFFSET", "actions[", "profile[", "national[", "weaknesses", "path_steps", "triggers", "recommendations", "matched", "level.", "sample_domain", "context_hint", "user_msg", "parsed", "raw", "weights", "top", "ranking", "items", "schools", "rows", "out", "params", "headers", "form_data", "files", "messages", "comment", "feedback", "grade", "region", "school_type", "year", "goal", "fmt", "subject_norm", "level", "key", "seed", "avg", "gap", "resource", "weak_units", "total_weeks", "trend", "avg_score", "score_variance", "risk_score", "equity_score", "national_gap", "equity_gap", "offset", "infra", "resource_idx", "teachers", "facility", "env", "school_name", "today", "atpt", "school", "query", "size", "snippet", "text", "model", "api_key", "content", "answer", "intent", "domain", "engine", "simulation", "integration", "roadmap", "role", "metrics", "features", "school", "resources", "summary", "tip", "triggers", "recommendedActions", "vsNational", "matchedCount", "keyEntities", "suggestedActions", "topDriver", "topWeight", "predictedAverage", "delta", "qualityScore", "explanationRatio", "subjectRisk", "dropoutProbability", "effectiveHours", "routine", "classInput", "analysisMeta", "classResult", "riskInput", "riskResult", "scheduleInput", "scheduleResult", "twinInput", "twinResult", "causalInput", "causalResult", "xaiInput", "xaiResult", "meta", "input", "sentenceCount", "questionCount", "repeatedSentenceCount", "source", "message", "schoolInfo", "scheduleCount", "selected", "count", "date", "integration", "simulation", "region", "year", "grade", "pathSteps", "totalEstimatedWeeks", "studyHoursPerDay", "riskScore", "avgScore", "equityScore", "grade", "recommendations", "vsNational", "matchedCount", "resources", "OPENAI")):
            return m.group(0)
        return f'{prefix}"{val}"{suffix}'

    line = re.sub(r'(: )([^,\n]+)(,?\s*)$', quote_value, line)
    return line


def fix_file(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = fix_known_literals(text)
    text = fix_getenv(text)
    text = fix_paths_and_urls(text)
    text = fix_headers_and_attrs(text)
    lines = [fix_line(ln) for ln in text.splitlines()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"fixed {path.relative_to(ROOT)}")


def main() -> int:
    for rel in ("backend/app/main.py", "backend/tests/test_smoke.py"):
        fix_file(ROOT / rel)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
