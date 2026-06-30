"""Safe quote fixes without bracket/type-hint corruption."""
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("fix_python", ROOT / "scripts" / "fix_python.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def fix_file(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = mod.fix_known_literals(text)
    text = mod.fix_getenv(text)
    text = mod.fix_paths_and_urls(text)
    # headers: only explicit patterns, not generic [key] quoting
    import re
    text = re.sub(r"request\.headers\.get\(([A-Za-z-]+)\)", r'request.headers.get("\1")', text)
    text = re.sub(r"auth = request\.headers\.get\(\"Authorization\"\) or\s*$", 'auth = request.headers.get("Authorization") or ""', text, flags=re.M)
    text = re.sub(r"\(request\.headers\.get\(\"X-Internal-Key\"\) or \)\.strip\(\)", '(request.headers.get("X-Internal-Key") or "").strip()', text)
    text = re.sub(r"payload\.get\(\"text\"\) or\s*$", 'payload.get("text") or ""', text, flags=re.M)
    text = re.sub(r"\.get\(([A-Z][A-Z0-9_]*),\s*\)", r'.get("\1", "")', text)
    path.write_text(text, encoding="utf-8")
    print(f"safe-fixed {path.relative_to(ROOT)}")


if __name__ == "__main__":
    for rel in ("backend/app/main.py", "backend/tests/test_smoke.py"):
        fix_file(ROOT / rel)
