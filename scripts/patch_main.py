"""Patch remaining syntax issues in main.py after bulk quote restore."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "backend/app/main.py"


def close_unterminated_fstrings(text: str) -> str:
    lines = []
    for line in text.splitlines():
        s = line.rstrip()
        if 'f"' in s and s.count('"') % 2 == 1:
            if s.endswith(","):
                s = s[:-1] + '",'
            elif s.endswith(")"):
                # detail=f"...)  -> detail=f"...")
                s = s[:-1] + '")'
            else:
                s = s + '"'
        lines.append(s)
    return "\n".join(lines) + "\n"


def main() -> None:
    text = MAIN.read_text(encoding="utf-8")
    text = text.replace('def get("self",', "def get(self,")
    text = text.replace('def set("self",', "def set(self,")
    text = text.replace('{"risk_score":.0f}', "{risk_score:.0f}")

    reps = [
        ('cache_key = f"schools|{query}|{atpt_code} or \'\'}|{size}', 'cache_key = f"schools|{query}|{atpt_code or \'\'}|{size}"'),
    ]
    for old, new in reps:
        text = text.replace(old, new)

    text = close_unterminated_fstrings(text)
    MAIN.write_text(text, encoding="utf-8")
    print("patched main.py")


if __name__ == "__main__":
    main()
