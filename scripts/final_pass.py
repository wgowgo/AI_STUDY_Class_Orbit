"""Final pass: quote dict keys and fix broken ternary string chains."""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "backend/app/main.py"

CLASS_FIELD = re.compile(
    r"^(\s+)([a-zA-Z_][a-zA-Z0-9_]*):\s*"
    r"(Optional\[|list\[|dict\[|Field\(|float|int|str|bool|Any|UploadFile|None\b|"
    r"ChatMessage|RiskInput|ScheduleInput|TwinInput|CausalInput|ExplainInput|"
    r"ClassAnalysisInput|SubjectScore)"
)


def is_class_field(line: str) -> bool:
    return bool(CLASS_FIELD.match(line))


def quote_keys(line: str) -> str:
    if is_class_field(line):
        return line
    stripped = line.lstrip()
    if stripped.startswith(("def ", "class ", "@", "from ", "import ", "#", "async def ")):
        return line
    line = re.sub(r"\{([a-zA-Z_][a-zA-Z0-9_]*):", r'{"\1":', line)
    line = re.sub(r",\s*([a-zA-Z_][a-zA-Z0-9_]*):", r', "\1":', line)
    m = re.match(r"^(\s+)([a-zA-Z_][a-zA-Z0-9_]*):\s*(.+)$", line)
    if m:
        indent, key, rest = m.groups()
        if key in {"if", "else", "elif", "for", "while", "return", "def", "class", "try", "except", "with", "async"}:
            return line
        if re.match(r"^(float|int|str|bool|Optional|list|dict|Any|Field|UploadFile)\b", rest):
            return line
        if rest.startswith('"') or rest.startswith("'") or rest.startswith("f\""):
            return f'{indent}"{key}": {rest}'
        if re.match(r"^[A-Z][a-zA-Z0-9_]*\(", rest):
            return f'{indent}"{key}": {rest}'
        if re.match(r"^[a-zA-Z_][\w.]*(\(|\.|\[)", rest) or rest in {"True", "False", "None"}:
            return f'{indent}"{key}": {rest}'
        if re.fullmatch(r"-?\d+(\.\d+)?,?", rest):
            return f'{indent}"{key}": {rest}'
    return line


def fix_ternary_commas(text: str) -> str:
    """Remove trailing commas after ternary branch strings before 'if'."""
    return re.sub(
        r'("(?:[^"\\]|\\.)*"),(\s*\n\s*if )',
        r'\1\2',
        text,
    )


def main() -> int:
    text = MAIN.read_text(encoding="utf-8")
    text = fix_ternary_commas(text)
    lines = [quote_keys(ln) for ln in text.splitlines()]
    text = "\n".join(lines) + "\n"
    MAIN.write_text(text, encoding="utf-8")

    try:
        ast.parse(text)
        print("main.py parses OK")
        return 0
    except SyntaxError as e:
        print(f"still broken line {e.lineno}: {e.msg}", file=sys.stderr)
        ls = text.splitlines()
        if e.lineno:
            print(ls[e.lineno - 1][:120], file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
