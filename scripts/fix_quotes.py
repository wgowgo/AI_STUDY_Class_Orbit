"""Restore quotes stripped from project source files."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

JSX_ATTRS = (
    "className|type|id|role|lang|aria-label|href|content|name|rel|src|for|tabIndex|crossorigin|"
    "key|aria-live|aria-labelledby|aria-hidden|accept|placeholder|value|min|max|step|rows|disabled|"
    "readOnly|multiple|autoComplete|initial|animate|transition|viewport|variants|whileInView|"
    "title|target|wheelHint|k|items|open|autoFocus|spellCheck|inputMode"
)


def fix_tsx(content: str) -> str:
    def repl(m: re.Match[str]) -> str:
        attr, val = m.group(1), m.group(2).strip()
        if not val:
            return f'{attr}=""'
        return f'{attr}="{val}"'

    pattern = (
        r"\b([a-zA-Z][\w:-]*)="
        r'([^"\'\s{][^>\n]*?)'
        r"(?=\s+[a-zA-Z][\w:-]*=|\s*/?>|\s*>|\s*$)"
    )
    prev = None
    while prev != content:
        prev = content
        content = re.sub(pattern, repl, content)
    content = re.sub(r"\bvalue=>", 'value=""', content)
    return content


def quote_token(token: str) -> str:
    token = token.strip()
    if not token:
        return '""'
    if token[0] in "\"'":
        return token
    if token in {"True", "False", "None"}:
        return token
    if re.fullmatch(r"-?\d+(\.\d+)?", token):
        return token
    if re.fullmatch(r"f[A-Za-z0-9_가-힣].*", token):
        return f'"{token[1:]}"' if not token.startswith('f"') else token
    return f'"{token}"'


def fix_python_list_items(text: str) -> str:
    def repl_list(m: re.Match[str]) -> str:
        inner = m.group(1)
        if '"' in inner or "'" in inner:
            return m.group(0)
        parts = [p.strip() for p in inner.split(",")]
        fixed = ", ".join(quote_token(p) for p in parts if p)
        return f"[{fixed}]"

    return re.sub(r"\[([^\[\]]+)\]", repl_list, text)


def fix_python(content: str) -> str:
    content = re.sub(
        r'load_dotenv\(dotenv_path=Path\(__file__\)\.resolve\(\)\.parent\.parent / \.env\)',
        'load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")',
        content,
    )
    content = re.sub(r"__import__\('re'\)\.split\(r([^,\)]+),", r'__import__("re").split(r"\1",', content)
    content = re.sub(r"__import__\('re'\)\.sub\(r([^,\)]+),", r'__import__("re").sub(r"\1",', content)
    content = re.sub(
        r"os\.getenv\(([A-Z][A-Z0-9_]*),\s*([^)]*)\)",
        lambda m: f'os.getenv("{m.group(1)}", {quote_token(m.group(2)) if m.group(2).strip() not in {"120", "60", "0"} else m.group(2).strip()})',
        content,
    )
    content = re.sub(
        r"os\.getenv\(([A-Z][A-Z0-9_]*)\)",
        r'os.getenv("\1")',
        content,
    )
    content = re.sub(
        r"request\.headers\.get\(([A-Za-z-]+)\)",
        r'request.headers.get("\1")',
        content,
    )
    content = re.sub(
        r"@app\.(get|post|put|delete|middleware)\(([^)\"']+)\)",
        lambda m: f'@app.{m.group(1)}("{m.group(2).strip()}")',
        content,
    )
    content = re.sub(
        r"client\.(get|post)\(([^)\"']+)\)",
        lambda m: f'client.{m.group(1)}("{m.group(2).strip()}")',
        content,
    )
    content = re.sub(
        r"\.startswith\(([^)\"']+)\)",
        lambda m: f'.startswith({quote_token(m.group(1))})',
        content,
    )
    content = re.sub(
        r"\.split\(([^)\"']+)\)",
        lambda m: f'.split({quote_token(m.group(1))})',
        content,
    )
    content = re.sub(
        r"HTTPException\(status_code=(\d+), detail=([^)]+)\)",
        lambda m: f'HTTPException(status_code={m.group(1)}, detail={quote_token(m.group(2))})',
        content,
    )
    content = re.sub(
        r"FastAPI\(title=([^,]+), version=([^)]+)\)",
        lambda m: f'FastAPI(title={quote_token(m.group(1))}, version={quote_token(m.group(2))})',
        content,
    )
    content = re.sub(
        r"JSONResponse\(\{detail: ([^}]+)\}",
        lambda m: f'JSONResponse({{"detail": {quote_token(m.group(1))}}}',
        content,
    )
    content = re.sub(
        r"f([A-Za-z0-9_가-힣][^,\n\)]*)",
        lambda m: f'f"{m.group(1)}"' if not m.group(0).startswith('f"') else m.group(0),
        content,
    )
    content = re.sub(
        r"(\w+)\.get\(([A-Z_]+)\)",
        r'\1.get("\2")',
        content,
    )
    content = re.sub(
        r"(\w+)\.get\(([a-z][a-zA-Z]+)\)",
        r'\1.get("\2")',
        content,
    )
    content = re.sub(
        r"(\w+)\[([a-zA-Z_가-힣][a-zA-Z0-9_가-힣]*)\]",
        r'\1["\2"]',
        content,
    )
    content = re.sub(
        r"\{([a-z][a-zA-Z0-9_]*):",
        r'{"\1":',
        content,
    )
    content = re.sub(
        r",\s*([a-z][a-zA-Z0-9_]*):",
        r', "\1":',
        content,
    )
    content = re.sub(
        r"assert body\.get\(([^)]+)\)",
        lambda m: f'assert body.get({quote_token(m.group(1))})',
        content,
    )
    content = re.sub(
        r"assert (\w+) in body",
        r'assert "\1" in body',
        content,
    )
    content = re.sub(
        r"assert body\[([^\]]+)\]",
        lambda m: f'assert body[{quote_token(m.group(1))}]',
        content,
    )
    content = re.sub(
        r"assert data\.get\(([^)]+)\)",
        lambda m: f'assert data.get({quote_token(m.group(1))})',
        content,
    )
    content = re.sub(
        r"assert r\.json\(\)\.get\(([^)]+)\)",
        lambda m: f'assert r.json().get({quote_token(m.group(1))})',
        content,
    )
    content = re.sub(
        r"json=\{([^}]+)\}",
        lambda m: "{" + ", ".join(
            f'"{k.strip()}": {quote_token(v.strip())}'
            for k, v in (part.split(":", 1) for part in m.group(1).split(","))
        ) + "}",
        content,
    )

    lines = content.splitlines()
    fixed_lines: list[str] = []
    for line in lines:
        if re.search(r"= \[[^\"']+\]", line) or re.search(r"= \[\*\]", line):
            line = fix_python_list_items(line)
        if re.search(r"return \{[a-z]", line) or re.search(r"^\s+[a-z]+:", line):
            line = re.sub(r"^(\s+)([a-z][a-zA-Z0-9_]*):", r'\1"\2":', line)
        if " if " in line and re.search(r" else [a-z가-힣]", line):
            line = re.sub(
                r"(else |if )([a-z][a-zA-Z0-9_가-힣][^,\n]*)",
                lambda m: f'{m.group(1)}{quote_token(m.group(2))}',
                line,
            )
        fixed_lines.append(line)
    content = "\n".join(fixed_lines) + ("\n" if content.endswith("\n") else "")

    return content


def main() -> int:
    for path in (ROOT / "web" / "src").rglob("*.tsx"):
        original = path.read_text(encoding="utf-8")
        fixed = fix_tsx(original)
        if fixed != original:
            path.write_text(fixed, encoding="utf-8")
            print(f"fixed tsx: {path.relative_to(ROOT)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
