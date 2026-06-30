# -*- coding: utf-8 -*-
"""Final manual patches for remaining syntax issues."""
from pathlib import Path
import re
import ast

MAIN = Path(__file__).resolve().parent.parent / "backend/app/main.py"

text = MAIN.read_text(encoding="utf-8")

# dict key bracket access
for key in ("avg", "gap", "resource", "infra"):
    text = text.replace(f"profile[{key}]", f'profile["{key}"]')
    text = text.replace(f"national[{key}]", f'national["{key}"]')

text = text.replace(
    """    grade = (
        "A (우수) if equity_score >= 80"
        else ""B (양호) if equity_score >= 65""
        else ""C (보통) if equity_score >= 50""
        else ""D (취약)""
    )""",
    """    grade = (
        "A (우수)" if equity_score >= 80
        else "B (양호)" if equity_score >= 65
        else "C (보통)" if equity_score >= 50
        else "D (취약)"
    )""",
)

reps = [
    ("recommendations.append(방과후 학교 및 기초학력 보충 프로그램 확대 필요)",
     'recommendations.append("방과후 학교 및 기초학력 보충 프로그램 확대 필요")'),
    ('recommendations.append("교육 콘텐츠", 강사 자원 배분 집중 지원 필요)',
     'recommendations.append("교육 콘텐츠, 강사 자원 배분 집중 지원 필요")'),
    ("recommendations.append(디지털 교육 인프라 투자 우선 순위 대상)",
     'recommendations.append("디지털 교육 인프라 투자 우선 순위 대상")'),
    ("recommendations.append(지역 평균 성취도가 전국 대비 낮음 → 집중 지원 필요)",
     'recommendations.append("지역 평균 성취도가 전국 대비 낮음 → 집중 지원 필요")'),
    ("recommendations.append(현재 교육 형평성 수준 유지 및 지속 모니터링 권장)",
     'recommendations.append("현재 교육 형평성 수준 유지 및 지속 모니터링 권장")'),
    ('detail="OPENAI_API_KEY가 설정되지 않았습니다.)',
     'detail="OPENAI_API_KEY가 설정되지 않았습니다.")'),
]
for a, b in reps:
    text = text.replace(a, b)

# quote snake_case metric keys in dicts
for key in (
    "simulation", "region", "year", "grade", "schoolType", "equityScore",
    "averageScore", "achievementGap", "resourceIndex", "infraIndex", "vsNational",
    "avgDiff", "equityDiff", "recommendations", "average_score", "regional_gap",
    "low_achievers_pct", "high_achievers_pct",
):
    text = re.sub(rf"(?<!\"){key}:", f'"{key}":', text)

MAIN.write_text(text, encoding="utf-8")
try:
    ast.parse(text)
    print("OK")
except SyntaxError as e:
    print(f"line {e.lineno}: {e.msg}")
    print(text.splitlines()[e.lineno - 1][:120])
