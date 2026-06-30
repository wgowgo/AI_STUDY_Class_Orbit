"""Restore quotes in corrupted backend Python files."""
from __future__ import annotations

import ast
import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

spec = importlib.util.spec_from_file_location("fix_python", ROOT / "scripts" / "fix_python.py")
_fix = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_fix)

CLASS_FIELD = re.compile(
    r"^(\s+)([a-zA-Z_][a-zA-Z0-9_]*):\s*"
    r"(Optional\[|list\[|dict\[|Field\(|float|int|str|bool|Any|UploadFile|None\b|"
    r"ChatMessage|RiskInput|ScheduleInput|TwinInput|CausalInput|ExplainInput|"
    r"ClassAnalysisInput|SubjectScore)"
)
PARAM_ANNOT = re.compile(r"^(\s+)([a-zA-Z_][a-zA-Z0-9_]*):\s*(Optional\[|str|int|float|bool|UploadFile|None\b)")


def is_type_field(line: str) -> bool:
    return bool(CLASS_FIELD.match(line) or PARAM_ANNOT.match(line))


def fix_headers_only(text: str) -> str:
    text = re.sub(r"request\.headers\.get\(([A-Za-z-]+)\)", r'request.headers.get("\1")', text)
    text = re.sub(r"\.get\(([A-Z][A-Z0-9_]*),\s*\)", r'.get("\1", "")', text)
    text = re.sub(
        r"(?<=\.get\()([A-Z][A-Z0-9_]*)(?=\))",
        r'"\1"',
        text,
    )
    text = re.sub(
        r"(?<=\.get\()([a-z][a-zA-Z0-9_]*)(?=\))",
        r'"\1"',
        text,
    )
    text = re.sub(
        r"auth = request\.headers\.get\(\"Authorization\"\) or\s*$",
        'auth = request.headers.get("Authorization") or ""',
        text,
        flags=re.M,
    )
    text = re.sub(
        r"\(request\.headers\.get\(\"X-Internal-Key\"\) or \)\.strip\(\)",
        '(request.headers.get("X-Internal-Key") or "").strip()',
        text,
    )
    text = re.sub(r"payload\.get\(\"text\"\) or\s*$", 'payload.get("text") or ""', text, flags=re.M)
    return text


def quote_dict_keys(line: str) -> str:
    if is_type_field(line):
        return line
    stripped = line.lstrip()
    if stripped.startswith(("def ", "class ", "@", "from ", "import ", "#", "async def ")):
        return line
    line = re.sub(r"\{([a-zA-Z_][a-zA-Z0-9_]*):", r'{"\1":', line)
    line = re.sub(r",\s*([a-zA-Z_][a-zA-Z0-9_]*):", r', "\1":', line)
    return line


def fix_fstrings_line(line: str) -> str:
    if "from " in line or "import " in line:
        return line
    line = re.sub(r"(?<![a-zA-Z])f\{", 'f"{', line)
    line = re.sub(r"(?<![a-zA-Z])f([가-힣])", r'f"\1', line)
    # close unterminated f-strings at end of line before comma
    if 'f"' in line and line.count('"') % 2 == 1:
        if line.rstrip().endswith(","):
            line = line.rstrip()[:-1] + '",'
        elif line.rstrip().endswith(")"):
            line = re.sub(r'(\)\s*)$', r'")', line.rstrip()) + "\n" if False else line
    return line


def fix_line_content(line: str) -> str:
    if is_type_field(line):
        return line
    line = fix_fstrings_line(line)
    line = quote_dict_keys(line)
    line = re.sub(
        r"\(([가-힣A-Za-z][가-힣A-Za-z0-9 /·\-]*),\s",
        lambda m: f'("{m.group(1)}", ',
        line,
    )
    return line


def fix_ternary_block(text: str) -> str:
    """Quote string literals in ( ... if ... else ... ) chains."""
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if re.search(r"=\s*\(\s*$", line) and i + 1 < len(lines):
            out.append(line)
            i += 1
            while i < len(lines):
                ln = lines[i]
                s = ln.strip()
                if s == ")":
                    out.append(ln)
                    i += 1
                    break
                if s.startswith("if ") or s.startswith("else if "):
                    out.append(ln)
                elif s.startswith("else ") and not s.startswith('else "'):
                    rest = s[5:].strip()
                    if rest.startswith("if "):
                        out.append(ln)
                    else:
                        ind = ln[: len(ln) - len(ln.lstrip())]
                        out.append(f'{ind}else "{rest.rstrip(",")}"')
                elif s and not s.startswith(("if ", "else", '"', "f\"", "+")) and " if " not in s[:30]:
                    if re.search(r"[가-힣]", s) or (s.endswith(",") and " " in s):
                        ind = ln[: len(ln) - len(ln.lstrip())]
                        body = s.rstrip(",")
                        out.append(f'{ind}"{body}",')
                    else:
                        out.append(ln)
                else:
                    out.append(ln)
                i += 1
            continue
        out.append(line)
        i += 1
    return "\n".join(out)


def fix_docstrings(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        if re.match(r"^(async )?def \w+\(", line) and line.rstrip().endswith(":"):
            j = i + 1
            block: list[str] = []
            while j < len(lines):
                nxt = lines[j]
                if not nxt.strip():
                    break
                s = nxt.strip()
                if re.match(
                    r"^(return |if |for |while |api_key|key =|region |req\.|scores |school_name|"
                    r"subject_norm|level =|fmt =|matched|goal =|weaknesses|path_steps|"
                    r"result =|schedule =|#|\"|\'|@|async )",
                    s,
                ):
                    break
                if re.match(r"^[a-zA-Z_]+\s*=", s):
                    break
                if re.search(r"[가-힣]", s) and not s.endswith(":"):
                    block.append(nxt)
                    j += 1
                    continue
                break
            if block:
                out.append('    """')
                out.extend(block)
                out.append('    """')
                i = j
                continue
        i += 1
    return "\n".join(out)


def apply_bulk_replacements(text: str) -> str:
    """Hand-curated replacements for patterns too risky for heuristics."""
    reps = [
        ('.split(r[.!?\\n]+, clean)', '.split(r"[.!?\\n]+", clean)'),
        ('__import__(re).sub(r\\s+,  , s)', '__import__("re").sub(r"\\s+", "  ", s)'),
        ("__import__(re).split", '__import__("re").split'),
        ("__import__(re).sub", '__import__("re").sub'),
        ("bucket = _rate_buckets[\"client_ip\"]", "_rate_buckets[client_ip]"),
        ('ent = self._data.get("key")', "ent = self._data.get(key)"),
        ('del self._data["key"]', "del self._data[key]"),
        ('self._data["key"] = ', "self._data[key] = "),
        ('_neis_cache.get("cache_key")', "_neis_cache.get(cache_key)"),
        ("code = str(res.get(CODE, ))", 'code = str(res.get("CODE", ""))'),
        ('form_data = {"model": model}', 'form_data = {"model": model}'),
        ('form_data = {model: model}', 'form_data = {"model": model}'),
        ('{"Authorization": f"Bearer {api_key}, "Content-Type": "application/json"}',
         '{"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}'),
        ('headers = {"Authorization": f"Bearer {api_key}}', 'headers = {"Authorization": f"Bearer {api_key}"}'),
        ('detail="OPENAI_API_KEY가 설정되지 않았습니다.)', 'detail="OPENAI_API_KEY가 설정되지 않았습니다.")'),
        ("region = (req.region or 전국)", 'region = (req.region or "전국")'),
        (".strip() or 전국", '.strip() or "전국"'),
        ("school_type = (req.schoolType or 고등)", 'school_type = (req.schoolType or "고등")'),
        ("goal = (req.goal or 내신)", 'goal = (req.goal or "내신")'),
        ("school_name = (req.school_name or 선택 학교)", 'school_name = (req.school_name or "선택 학교")'),
        ("objective: req.objective or balanced", 'objective: req.objective or "balanced"'),
        ("_REGION_PROFILES[전국]", '_REGION_PROFILES["전국"]'),
        ('r["subject"] == 전체', 'r["subject"] == "전체"'),
        ("SubjectScore(subject=수학", 'SubjectScore(subject="수학"'),
        ("SubjectScore(subject=영어", 'SubjectScore(subject="영어"'),
        ("SubjectScore(subject=국어", 'SubjectScore(subject="국어"'),
        ('_RESOURCES_MAP.get(sub.subject, EBS 무료 강좌)', '_RESOURCES_MAP.get(sub.subject, "EBS 무료 강좌")'),
        ("[기초 개념, 심화 응용]", '["기초 개념", "심화 응용"]'),
        ("triggers else [현재 주요 위험 지표 없음]", 'triggers else ["현재 주요 위험 지표 없음"]'),
        ("recommendedActions: actions[level]", 'recommendedActions: actions[level]'),
        ('sample_domain = risk if any(w in req.query for w in [위험, 격차, 성적])',
         'sample_domain = "risk" if any(w in req.query for w in ["위험", "격차", "성적"])'),
        ('else equity if any(w in req.query for w in [지역, 형평, 불평등])',
         'else "equity" if any(w in req.query for w in ["지역", "형평", "불평등"])'),
        ('else pathway if any(w in req.query for w in [경로, 공부, 순서])',
         'else "pathway" if any(w in req.query for w in ["경로", "공부", "순서"])'),
        ("else general\n", 'else "general"\n'),
        ('triggers.append(평균 성적 60점 미만)', 'triggers.append("평균 성적 60점 미만")'),
        ("triggers.append(수업 참여도 낮음)", 'triggers.append("수업 참여도 낮음")'),
        ("if triggers else 안정적인 학습 상태입니다.)", 'if triggers else "안정적인 학습 상태입니다.")'),
        ("raise HTTPException(status_code=502, detail=NEIS 호출 실패)",
         'raise HTTPException(status_code=502, detail="NEIS 호출 실패")'),
        ("grade = (\n        A (우수)", 'grade = (\n        "A (우수)'),
        ("else B (양호)", 'else "B (양호)'),
        ("else C (보통)", 'else "C (보통)'),
        ("else D (취약)", 'else "D (취약)'),
        ("context_hint = f\\n추가", 'context_hint = f"\\n추가'),
        ("if req.context else ", 'if req.context else ""'),
        ("intent: f'{req.query[:40]}' 질문", 'intent: f"\'{req.query[:40]}\' 질문'),
        ("fOPENAI_API_KEY가", 'f"OPENAI_API_KEY가'),
        ('_NLQ_SYSTEM_PROMPT = """당신은', '_NLQ_SYSTEM_PROMPT = """당신은'),
        ("_NLQ_SYSTEM_PROMPT = 당신은", '_NLQ_SYSTEM_PROMPT = """당신은'),
        ('suggestedActions: ["<다음 단계 1>", "<다음 단계 2>"]\n}\n"""',
         'suggestedActions: ["<다음 단계 1>", "<다음 단계 2>"]\n}\n"""'),
        ("suggestedActions: [<다음 단계 1>, <다음 단계 2>]\n}\n\n",
         'suggestedActions: ["<다음 단계 1>", "<다음 단계 2>"]\n}\n"""\n\n'),
        ('cache_key = f"summary|{atpt}|{school}', 'cache_key = f"summary|{atpt}|{school}'),
        ('cache_key = f"schools|{query}|{atpt_code', 'cache_key = f"schools|{query}|{atpt_code}'),
        ('service: class-orbit-api,', 'service: "class-orbit-api",'),
        ('version: 0.1.0,', 'version: "0.1.0",'),
        ('kess: stub_env_ready if kess_stub else sample_only',
         'kess: "stub_env_ready" if kess_stub else "sample_only"'),
        ('school_alimi: stub_env_ready if alimi_stub else sample_only',
         'school_alimi: "stub_env_ready" if alimi_stub else "sample_only"'),
        ('risk_rl_shap: simulation', 'risk_rl_shap: "simulation"'),
        ('cors_mode: any if _cors_raw == "*" else allowlist',
         'cors_mode: "any" if _cors_raw == "*" else "allowlist"'),
        ('message: NEIS 키/학교코드가 없어 샘플 데이터 반환',
         'message: "NEIS 키/학교코드가 없어 샘플 데이터 반환"'),
        ('message: NEIS_API_KEY가 없어 샘플 목록 반환',
         'message: "NEIS_API_KEY가 없어 샘플 목록 반환"'),
        ('message: NEIS_API_KEY가 없어 샘플 시간표 반환',
         'message: "NEIS_API_KEY가 없어 샘플 시간표 반환"'),
        ('source: sample,', '"source": "sample",'),
        ('source: neis,', '"source": "neis",'),
        ('integration: sample_only,', '"integration": "sample_only",'),
        ('engine: simulated-sklearn,', '"engine": "simulated-sklearn",'),
        ('engine: simulated-sb3,', '"engine": "simulated-sb3",'),
        ('engine: simulated-shap,', '"engine": "simulated-shap",'),
        ('integration: heuristic_only,', '"integration": "heuristic_only",'),
        ('role: AI 모델 학습용 기준 데이터(데모)', 'role: "AI 모델 학습용 기준 데이터(데모)"'),
        ('role: 정확도 향상용 보조 데이터(데모)', 'role: "정확도 향상용 보조 데이터(데모)"'),
        ('{PERIO: 1, ITRT_CNTNT: 국어}', '{"PERIO": 1, "ITRT_CNTNT": "국어"}'),
        ('{PERIO: 2, ITRT_CNTNT: 수학}', '{"PERIO": 2, "ITRT_CNTNT": "수학"}'),
        ('{PERIO: 3, ITRT_CNTNT: 영어}', '{"PERIO": 3, "ITRT_CNTNT": "영어"}'),
        ('{ATPT_OFCDC_SC_CODE: B10, ATPT_OFCDC_SC_NM: 서울특별시교육청, SD_SCHUL_CODE: 7010569, SCHUL_NM: 서울고등학교}',
         '{"ATPT_OFCDC_SC_CODE": "B10", "ATPT_OFCDC_SC_NM": "서울특별시교육청", "SD_SCHUL_CODE": "7010569", "SCHUL_NM": "서울고등학교"}'),
        ('{ATPT_OFCDC_SC_CODE: J10, ATPT_OFCDC_SC_NM: 경기도교육청, SD_SCHUL_CODE: 7530010, SCHUL_NM: 수원고등학교}',
         '{"ATPT_OFCDC_SC_CODE": "J10", "ATPT_OFCDC_SC_NM": "경기도교육청", "SD_SCHUL_CODE": "7530010", "SCHUL_NM": "수원고등학교"}'),
        ('schoolInfo: {SCHUL_NM: 샘플고, ATPT_OFCDC_SC_NM: 서울특별시교육청}',
         'schoolInfo: {"SCHUL_NM": "샘플고", "ATPT_OFCDC_SC_NM": "서울특별시교육청"}'),
        ("Type: json,", '"Type": "json",'),
        ("KEY: key,", '"KEY": key,'),
        ("pIndex: 1,", '"pIndex": 1,'),
        ("SCHUL_NM: query", '"SCHUL_NM": query'),
        ("ATPT_OFCDC_SC_CODE: atpt", '"ATPT_OFCDC_SC_CODE": atpt'),
        ("SD_SCHUL_CODE: school", '"SD_SCHUL_CODE": school'),
        ("ALL_TI_YMD: today", '"ALL_TI_YMD": today'),
        ("GRADE: str(grade)", '"GRADE": str(grade)'),
        ("CLASS_NM: str(cls)", '"CLASS_NM": str(cls)'),
        ("수학: [수와 연산, 대수, 함수, 기하, 확률/통계]",
         '"수학": ["수와 연산", "대수", "함수", "기하", "확률/통계"]'),
        ("영어: [어휘/발음, 문법, 독해, 듣기, 쓰기]",
         '"영어": ["어휘/발음", "문법", "독해", "듣기", "쓰기"]'),
        ("국어: [문학, 독서(비문학), 문법/어휘, 쓰기/화법]",
         '"국어": ["문학", "독서(비문학)", "문법/어휘", "쓰기/화법"]'),
        ("과학: [물리, 화학, 생명과학, 지구과학]",
         '"과학": ["물리", "화학", "생명과학", "지구과학"]'),
        ("사회: [한국사, 세계사, 지리, 일반사회]",
         '"사회": ["한국사", "세계사", "지리", "일반사회"]'),
        ("수학: EBS 수학 개념완성,", '"수학": "EBS 수학 개념완성",'),
        ("영어: EBS 영어 듣기/독해,", '"영어": "EBS 영어 듣기/독해",'),
        ("국어: EBS 국어 독서, 문학,", '"국어": "EBS 국어 독서, 문학",'),
        ("과학: EBS 과학탐구,", '"과학": "EBS 과학탐구",'),
        ("사회: EBS 사회탐구,", '"사회": "EBS 사회탐구",'),
        ("서울: {avg:", '"서울": {"avg":'),
        ("경기: {avg:", '"경기": {"avg":'),
        ("부산: {avg:", '"부산": {"avg":'),
        ("인천: {avg:", '"인천": {"avg":'),
        ("대구: {avg:", '"대구": {"avg":'),
        ("광주: {avg:", '"광주": {"avg":'),
        ("대전: {avg:", '"대전": {"avg":'),
        ("전남: {avg:", '"전남": {"avg":'),
        ("전북: {avg:", '"전북": {"avg":'),
        ("경북: {avg:", '"경북": {"avg":'),
        ("경남: {avg:", '"경남": {"avg":'),
        ("충북: {avg:", '"충북": {"avg":'),
        ("충남: {avg:", '"충남": {"avg":'),
        ("강원: {avg:", '"강원": {"avg":'),
        ("제주: {avg:", '"제주": {"avg":'),
        ("전국: {avg:", '"전국": {"avg":'),
        ("고등: 0.0,", '"고등": 0.0,'),
        ("중학: 1.5,", '"중학": 1.5,'),
        ("초등: 3.0,", '"초등": 3.0,'),
        ('{subject: 수학, title: EBS 수학 개념완성, type: video, cost: 무료,',
         '{"subject": "수학", "title": "EBS 수학 개념완성", "type": "video", "cost": "무료",'),
        ('{subject: 영어, title: EBS 영어 듣기/독해, type: video, cost: 무료,',
         '{"subject": "영어", "title": "EBS 영어 듣기/독해", "type": "video", "cost": "무료",'),
        ('{subject: 국어, title: EBS 국어 독서, 문학, type: video, cost: 무료,',
         '{"subject": "국어", "title": "EBS 국어 독서, 문학", "type": "video", "cost": "무료",'),
        ('{subject: 과학, title: EBS 과학탐구 기초, type: video, cost: 무료,',
         '{"subject": "과학", "title": "EBS 과학탐구 기초", "type": "video", "cost": "무료",'),
        ('{subject: 사회, title: EBS 사회탐구, type: video, cost: 무료,',
         '{"subject": "사회", "title": "EBS 사회탐구", "type": "video", "cost": "무료",'),
        ('{subject: 전체, title: 국립중앙도서관 디지털 자료실, type: library, cost: 무료,',
         '{"subject": "전체", "title": "국립중앙도서관 디지털 자료실", "type": "library", "cost": "무료",'),
        ("url: https://www.ebs.co.kr", 'url: "https://www.ebs.co.kr"'),
        ("url: https://www.kmooc.kr", 'url: "https://www.kmooc.kr"'),
        ("url: https://www.nl.go.kr", 'url: "https://www.nl.go.kr"'),
        ("url: http://www.kocw.net", 'url: "http://www.kocw.net"'),
        ("minLevel: 0, maxLevel: 70, difficulty: 기초~중급", 'minLevel: 0, maxLevel: 70, difficulty: "기초~중급"'),
        ("minLevel: 65, maxLevel: 100, difficulty: 중급~고급", 'minLevel: 65, maxLevel: 100, difficulty: "중급~고급"'),
        ("minLevel: 50, maxLevel: 100, difficulty: 중급", 'minLevel: 50, maxLevel: 100, difficulty: "중급"'),
        ("minLevel: 0, maxLevel: 70, difficulty: 기초", 'minLevel: 0, maxLevel: 70, difficulty: "기초"'),
        ("minLevel: 0, maxLevel: 100, difficulty: 전 수준", 'minLevel: 0, maxLevel: 100, difficulty: "전 수준"'),
        ("minLevel: 60, maxLevel: 100, difficulty: 대학 수준", 'minLevel: 60, maxLevel: 100, difficulty: "대학 수준"'),
        ("담당 교사, 상담사와 즉시 면담 권장,", '"담당 교사, 상담사와 즉시 면담 권장",'),
        ("학습 부진 원인 파악(학습 결손 vs 심리적 요인),", '"학습 부진 원인 파악(학습 결손 vs 심리적 요인)",'),
        ("방과후 보충 수업 또는 멘토링 연결,", '"방과후 보충 수업 또는 멘토링 연결",'),
        ("학부모 알림 발송,", '"학부모 알림 발송",'),
        ("취약 과목 집중 복습 스케줄 재조정,", '"취약 과목 집중 복습 스케줄 재조정",'),
        ("2주 내 교사 점검 면담,", '"2주 내 교사 점검 면담",'),
        ("자기주도 학습 습관 점검,", '"자기주도 학습 습관 점검",'),
        ("현재 학습 방향 유지,", '"현재 학습 방향 유지",'),
        ("주간 자기 점검 권장,", '"주간 자기 점검 권장",'),
        ("방과후 학교 및 기초학력 보충 프로그램 확대 필요", '"방과후 학교 및 기초학력 보충 프로그램 확대 필요"'),
        ("교육 콘텐츠, 강사 자원 배분 집중 지원 필요", '"교육 콘텐츠, 강사 자원 배분 집중 지원 필요"'),
        ("디지털 교육 인프라 투자 우선 순위 대상", '"디지털 교육 인프라 투자 우선 순위 대상"'),
        ("지역 평균 성취도가 전국 대비 낮음 → 집중 지원 필요", '"지역 평균 성취도가 전국 대비 낮음 → 집중 지원 필요"'),
        ("현재 교육 형평성 수준 유지 및 지속 모니터링 권장", '"현재 교육 형평성 수준 유지 및 지속 모니터링 권장"'),
        ("backend/.env 파일에 OPENAI_API_KEY 설정", '"backend/.env 파일에 OPENAI_API_KEY 설정"'),
        ("동일 질문을 다시 시도", '"동일 질문을 다시 시도"'),
        ("{role: system, content: _NLQ_SYSTEM_PROMPT}", '{"role": "system", "content": _NLQ_SYSTEM_PROMPT}'),
        ("{role: user, content: user_msg}", '{"role": "user", "content": user_msg}'),
        ("payload = {model: model, messages: messages, temperature: 0.2, response_format: {type: json_object}}",
         'payload = {"model": model, "messages": messages, "temperature": 0.2, "response_format": {"type": "json_object"}}'),
        ("data.get(schoolInfo, [{}])[1].get(row, [{}])[0]",
         'data.get("schoolInfo", [{}])[1].get("row", [{}])[0]'),
        ("payload.get(schoolInfo, [{}])[1].get(row, [])",
         'payload.get("schoolInfo", [{}])[1].get("row", [])'),
        ("payload.get(hisTimetable, [{}])[1].get(row, [])",
         'payload.get("hisTimetable", [{}])[1].get("row", [])'),
    ]
    for old, new in reps:
        text = text.replace(old, new)
    return text


def quote_bare_values(text: str) -> str:
    """Quote remaining bare string values after colons in dict-like lines."""
    lines = []
    for line in text.splitlines():
        if is_type_field(line):
            lines.append(line)
            continue
        m = re.match(r"^(\s+)\"([^\"]+)\":\s*([^,\n]+)(,?\s*)$", line)
        if m:
            indent, key, val, tail = m.groups()
            val = val.strip()
            if val and val[0] not in "\"'{" and not re.fullmatch(r"-?\d+(\.\d+)?", val):
                if val not in {"True", "False", "None"} and not re.match(r"^[a-zA-Z_][\w.]*(\(|\.|\[)", val):
                    if re.search(r"[가-힣\-]|sample|neis|json|balanced|simulation|heuristic|stub", val):
                        line = f'{indent}"{key}": "{val}"{tail}'
        lines.append(line)
    return "\n".join(lines)


def fix_test_file(text: str) -> str:
    text = _fix.fix_paths_and_urls(text)
    text = re.sub(r"assert body\.get\((\w+)\)", r'assert body.get("\1")', text)
    text = re.sub(r"assert (\w+) in body", r'assert "\1" in body', text)
    text = re.sub(r"assert body\[(\w+)\]", r'assert body["\1"]', text)
    text = re.sub(r"assert data\.get\((\w+)\)", r'assert data.get("\1")', text)
    text = re.sub(r"assert r\.json\(\)\.get\((\w+)\)", r'assert r.json().get("\1")', text)
    text = re.sub(r"== sample_only", '== "sample_only"', text)
    text = re.sub(r"== sample", '== "sample"', text)

    def fix_json_block(m: re.Match[str]) -> str:
        inner = m.group(1)
        parts = []
        for part in inner.split(","):
            if ":" not in part:
                continue
            k, v = part.split(":", 1)
            k, v = k.strip(), v.strip()
            if not k.startswith('"'):
                k = f'"{k}"'
            if v and v[0] not in '"\'{' and not re.fullmatch(r"-?\d+(\.\d+)?", v):
                if v not in {"True", "False", "None"}:
                    v = f'"{v}"'
            parts.append(f"{k}: {v}")
        return "json={" + ", ".join(parts) + "}"

    text = re.sub(r"json=\{([^}]+)\}", fix_json_block, text)
    return text


def process_main(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    text = _fix.fix_known_literals(text)
    text = _fix.fix_getenv(text)
    text = _fix.fix_paths_and_urls(text)
    text = fix_headers_only(text)
    text = apply_bulk_replacements(text)
    text = fix_ternary_block(text)
    lines = [fix_line_content(ln) for ln in text.splitlines()]
    text = "\n".join(lines)
    text = quote_bare_values(text)
    text = fix_docstrings(text)
    return text + "\n"


def process_test(path: Path) -> str:
    return fix_test_file(path.read_text(encoding="utf-8")) + "\n"


def main() -> int:
    main_path = ROOT / "backend/app/main.py"
    test_path = ROOT / "backend/tests/test_smoke.py"

    main_path.write_text(process_main(main_path), encoding="utf-8")
    test_path.write_text(process_test(test_path), encoding="utf-8")
    print(f"fixed {main_path.relative_to(ROOT)}")
    print(f"fixed {test_path.relative_to(ROOT)}")

    ok = True
    for p in (main_path, test_path):
        try:
            ast.parse(p.read_text(encoding="utf-8"))
        except SyntaxError as e:
            ok = False
            lines = p.read_text(encoding="utf-8").splitlines()
            print(f"ERROR {p.name} line {e.lineno}: {e.msg}", file=sys.stderr)
            if e.lineno and e.lineno <= len(lines):
                print(f"  {lines[e.lineno-1][:120]}", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
