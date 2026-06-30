"""Restore quotes in backend/main.py using curated replacements only."""
from __future__ import annotations

import ast
import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "backend/app/main.py"

spec = importlib.util.spec_from_file_location("fix_python", ROOT / "scripts" / "fix_python.py")
_fix = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_fix)


def apply_safe_globals(text: str) -> str:
    text = _fix.fix_known_literals(text)
    # fix split pattern where \n is literal backslash-n in source file
    text = text.replace(".split(r[.!?\\n]+, clean)", '.split(r"[.!?\\n]+", clean)')
    text = _fix.fix_getenv(text)
    text = _fix.fix_paths_and_urls(text)
    text = re.sub(r"request\.headers\.get\(([A-Za-z-]+)\)", r'request.headers.get("\1")', text)
    text = re.sub(
        r"\(request\.headers\.get\(\"X-Internal-Key\"\) or \)\.strip\(\)",
        '(request.headers.get("X-Internal-Key") or "").strip()',
        text,
    )
    text = re.sub(
        r"auth = request\.headers\.get\(\"Authorization\"\) or\s*$",
        'auth = request.headers.get("Authorization") or ""',
        text,
        flags=re.M,
    )
    text = re.sub(r"payload\.get\(\"text\"\) or\s*$", 'payload.get("text") or ""', text, flags=re.M)
    text = re.sub(r"\.get\(([A-Z][A-Z0-9_]*),\s*\)", r'.get("\1", "")', text)
    return text


def apply_replacements(text: str) -> str:
    reps_path = ROOT / "scripts" / "main_replacements.txt"
    if reps_path.exists():
        for block in reps_path.read_text(encoding="utf-8").split("\n---\n"):
            block = block.strip()
            if not block or block.startswith("#"):
                continue
            old, new = block.split("\n===>\n", 1)
            text = text.replace(old, new)
    return text


def quote_dict_line(line: str) -> str:
    if re.match(r"^\s+(region|year|grade|averageScore|attendanceRate|classQualityScore|schoolEnvironmentScore|koreanLevel|mathLevel|englishLevel|fatigue|studyHours|objective|role|content|message|history|transcriptLength|explanationFocus|repetitionCount|questionPromptRate|keywordDensity|currentAverage|planQuality|consistency|weeks|attendanceImpact|classQualityImpact|selfStudyImpact|environmentImpact|attendance|understanding|classQuality|transcript|risk_input|schedule_input|twin_input|causal_input|xai_input|subject|score|importance|goal|studyHoursPerDay|recentScores|submissionRate|engagementScore|region|schoolType|level|formatPref|query|context):\s", line):
        return line
    if re.match(r"^def \w+\(", line) or re.match(r"^\s+def \w+\(", line):
        return line
    line = re.sub(r"\{([a-zA-Z_][a-zA-Z0-9_]*):", r'{"\1":', line)
    line = re.sub(r",\s*([a-zA-Z_][a-zA-Z0-9_]*):", r', "\1":', line)
    return line


def main() -> int:
    text = MAIN.read_text(encoding="utf-8")
    text = apply_safe_globals(text)
    text = apply_replacements(text)
    text = "\n".join(quote_dict_line(l) for l in text.splitlines()) + "\n"
    MAIN.write_text(text, encoding="utf-8")
    try:
        ast.parse(text)
        print("OK")
        return 0
    except SyntaxError as e:
        print(f"line {e.lineno}: {e.msg}", file=sys.stderr)
        lines = text.splitlines()
        if e.lineno:
            print(lines[e.lineno - 1][:120], file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
