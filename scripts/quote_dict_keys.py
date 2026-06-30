# -*- coding: utf-8 -*-
from pathlib import Path
import re

MAIN = Path(__file__).resolve().parent.parent / "backend/app/main.py"
text = MAIN.read_text(encoding="utf-8")

KEYS = [
    "ok", "service", "integrations", "security", "metrics", "role", "roadmap", "result",
    "neis_configured", "openai_configured", "input", "meta", "classInput", "classResult",
    "analysisMeta", "riskInput", "riskResult", "scheduleInput", "scheduleResult", "twinInput",
    "twinResult", "causalInput", "causalResult", "xaiInput", "xaiResult", "message", "schoolInfo",
    "scheduleCount", "selected", "features", "school", "summary", "intent", "domain", "simulation",
    "objective", "answer", "suggestedActions", "goal", "pathSteps", "rank", "tip", "subject",
    "level", "matchedCount", "resources", "topDriver", "topWeight", "ranking", "effectiveHours",
    "routine", "predictedAverage", "delta", "comment", "qualityScore", "explanationRatio",
    "feedback", "subjectRisk", "dropoutProbability", "weights", "top", "pSize", "name", "atpt_code",
    "school_code", "sentenceCount", "questionCount", "repeatedSentenceCount", "currentScore",
    "targetScore", "weeklyHours", "focusUnits", "estimatedWeeks", "publicResource", "totalEstimatedWeeks",
    "studyHoursPerDay", "cors_mode", "rate_limit_per_minute", "internal_api_key_required",
    "kess", "school_alimi", "risk_rl_shap", "engine", "integration", "attendance", "understanding",
    "fatigue", "classQuality", "keyEntities", "rows", "count", "date", "schools",
]

lines = []
for line in text.splitlines():
    m = re.match(r"^(\s+)([a-zA-Z_][a-zA-Z0-9_]*):\s*(.+)$", line)
    if m:
        indent, key, rest = m.groups()
        if key in KEYS and not re.match(r"^(float|int|str|bool|Optional|list|dict|Field|UploadFile|ClassAnalysisInput|RiskInput|True|False)", rest):
            if not rest.startswith('"') or key in KEYS:
                line = f'{indent}"{key}": {rest}'
    line = re.sub(r"\{([a-zA-Z_][a-zA-Z0-9_]*):", lambda m: f'{{"{m.group(1)}":' if m.group(1) in KEYS else m.group(0), line)
    line = re.sub(r",\s*([a-zA-Z_][a-zA-Z0-9_]*):", lambda m: f', "{m.group(1)}":' if m.group(1) in KEYS else m.group(0), line)
    lines.append(line)

MAIN.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("dict keys quoted")
