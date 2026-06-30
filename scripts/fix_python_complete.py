"""Complete quote restoration for corrupted backend Python sources."""
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
    r"(Optional\[|list\[|dict\[|Field\(|float|int|str|bool|Any|"
    r"ChatMessage|RiskInput|ScheduleInput|TwinInput|CausalInput|ExplainInput|"
    r"ClassAnalysisInput|SubjectScore|UploadFile|None\b)"
)
TYPE_ANNOT_PARAM = re.compile(
    r"^(\s+)([a-zA-Z_][a-zA-Z0-9_]*):\s*(Optional\[|str|int|float|bool|UploadFile|None\b)"
)


def is_class_field_line(line: str) -> bool:
    return bool(CLASS_FIELD.match(line) or TYPE_ANNOT_PARAM.match(line))


def quote_dict_keys(line: str) -> str:
    if is_class_field_line(line):
        return line
    if line.lstrip().startswith(("def ", "class ", "@", "from ", "import ", "#")):
        return line
    line = re.sub(r"\{([a-zA-Z_][a-zA-Z0-9_]*):", r'{"\1":', line)
    line = re.sub(r",\s*([a-zA-Z_][a-zA-Z0-9_]*):", r', "\1":', line)
    return line


def fix_fstrings(text: str) -> str:
    text = re.sub(r"(?<![a-zA-Z])f\{", 'f"{', text)
    text = re.sub(r"(?<![a-zA-Z])f([가-힣])", r'f"\1', text)
    return text


def fix_ternary_korean_strings(text: str) -> str:
    """Quote bare Korean/English string branches in parenthesized ternary chains."""
    lines = text.splitlines()
    out: list[str] = []
    in_paren_ternary = False
    paren_depth = 0

    for line in lines:
        stripped = line.strip()
        if stripped.endswith("= (") or stripped.endswith("feedback = (") or stripped.endswith("comment = ("):
            in_paren_ternary = True
            paren_depth = 0
            out.append(line)
            continue

        if in_paren_ternary:
            paren_depth += line.count("(") - line.count(")")
            if stripped.startswith(("if ", "else if ")):
                out.append(line)
                continue
            if stripped.startswith("else ") and not stripped.startswith('else "'):
                rest = stripped[5:].strip()
                if rest.startswith("if "):
                    out.append(line)
                    continue
                if rest and rest[0] not in '"\'(' and not rest.startswith("f\""):
                    indent = line[: len(line) - len(line.lstrip())]
                    out.append(f'{indent}else "{rest}"')
                    continue
            if (
                not stripped.startswith(("if ", "else"))
                and ":" not in stripped[:20]
                and stripped
                and stripped[0] not in '"\'f('
                and not re.match(r"[\w.]+\(", stripped)
            ):
                indent = line[: len(line) - len(line.lstrip())]
                out.append(f'{indent}"{stripped.rstrip(",")}",')
                continue
            if paren_depth <= 0 and stripped == ")":
                in_paren_ternary = False
        out.append(line)
    return "\n".join(out)


def fix_docstring_blocks(text: str) -> str:
    """Restore triple-quoted docstrings on endpoint handlers."""
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        if re.match(r"^(@app\.(get|post)|async def |def )", line) or (
            i > 0 and lines[i - 1].strip().startswith("@app.")
        ):
            pass
        i += 1

    # Second pass: after `async def foo(...):` or `def foo(...):`, if next non-empty lines
    # are Korean prose (not code), wrap in triple quotes.
    lines = out if out else text.splitlines()
    out = []
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
                if s.startswith(("#", '"', "'", "return ", "if ", "for ", "api_key", "key =", "region", "req.", "scores")):
                    break
                if re.match(r"^[a-zA-Z_]+\s*=", s) or s.startswith("@"):
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


def fix_tuple_strings(line: str) -> str:
    """Quote tuple first elements like (출결, x) -> ("출결", x)."""
    if is_class_field_line(line):
        return line
    return re.sub(
        r"\(([가-힣A-Za-z][가-힣A-Za-z0-9 /]*),\s",
        lambda m: f'("{m.group(1)}", ',
        line,
    )


def fix_list_string_items(line: str) -> str:
    if is_class_field_line(line):
        return line
    # list items that are bare Korean/words in [..., ...]
    if not ("[" in line and "]" in line):
        return line

    def repl(m: re.Match[str]) -> str:
        inner = m.group(1)
        if '"' in inner or "'" in inner:
            return m.group(0)
        parts = []
        for part in inner.split(","):
            p = part.strip()
            if not p:
                continue
            if p[0] in "\"'[" or p.startswith("f\""):
                parts.append(p)
            elif re.fullmatch(r"-?\d+(\.\d+)?", p):
                parts.append(p)
            elif p in {"True", "False", "None"}:
                parts.append(p)
            elif re.match(r"^[a-zA-Z_][a-zA-Z0-9_.]*$", p) and p[0].islower():
                parts.append(p)  # variable
            else:
                parts.append(f'"{p}"')
        return "[" + ", ".join(parts) + "]"

    return re.sub(r"\[([^\[\]]+)\]", repl, line)


def fix_bare_string_values(line: str) -> str:
    """Quote dict values that are bare identifiers/strings like service: class-orbit-api."""
    if is_class_field_line(line):
        return line
    # key: bare-value,  where value isn't code
    def repl(m: re.Match[str]) -> str:
        key, val, tail = m.group(1), m.group(2).strip(), m.group(3)
        if not val or val[0] in "\"'{[" or val.startswith("f\""):
            return m.group(0)
        if val in {"True", "False", "None"}:
            return m.group(0)
        if re.fullmatch(r"-?\d+(\.\d+)?", val):
            return m.group(0)
        if re.match(r"^[a-zA-Z_][\w.]*(\(|$)", val):
            return m.group(0)  # expression
        if val.startswith("req.") or val.startswith("os.") or val.startswith("clamp"):
            return m.group(0)
        if "-" in val and re.search(r"[a-z]", val):  # class-orbit-api
            return f'"{key}": "{val}"{tail}'
        if re.search(r"[가-힣]", val):
            return f'"{key}": "{val}"{tail}'
        if val in {"sample", "sample_only", "simulation", "stub_env_ready", "neis", "json", "balanced", "general", "risk", "equity", "pathway", "any", "allowlist", "heuristic_only"}:
            return f'"{key}": "{val}"{tail}'
        if val.isupper() or (val.isalnum() and val[0].isupper() and len(val) <= 6):
            return f'"{key}": "{val}"{tail}'
        return m.group(0)

    line = re.sub(r'"([a-zA-Z_][a-zA-Z0-9_]*)":\s*([^,\n]+)(,?\s*)$', repl, line)
    line = re.sub(r'"([A-Z][A-Z0-9_]*)":\s*([^,\n]+)(,?\s*)$', repl, line)
    return line


def fix_remaining_patterns(text: str) -> str:
    reps = [
        ('.split(r[.!?\\n]+, clean)', '.split(r"[.!?\\n]+", clean)'),
        ("(request.headers.get(\"X-Internal-Key\") or ).strip()", '(request.headers.get("X-Internal-Key") or "").strip()'),
        ("auth = request.headers.get(\"Authorization\") or ", 'auth = request.headers.get("Authorization") or ""'),
        ("code = str(res.get(CODE, ))", 'code = str(res.get("CODE", ""))'),
        ("bucket = _rate_buckets[\"client_ip\"]", "_rate_buckets[client_ip]"),
        ('ent = self._data.get("key")', "ent = self._data.get(key)"),
        ('del self._data["key"]', "del self._data[key]"),
        ('self._data["key"] = ', "self._data[key] = "),
        ('_neis_cache.get("cache_key")', "_neis_cache.get(cache_key)"),
        ('cache_key = f"summary|{atpt}|{school}', 'cache_key = f"summary|{atpt}|{school}'),
        ('cache_key = f"schools|{query}|{atpt_code', 'cache_key = f"schools|{query}|{atpt_code'),
        ('payload.get("text") or ', 'payload.get("text") or ""'),
        ('{"Authorization": f"Bearer {api_key}, "Content-Type": "application/json"}',
         '{"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}'),
        ('detail="OPENAI_API_KEY가 설정되지 않았습니다.)', 'detail="OPENAI_API_KEY가 설정되지 않았습니다.")'),
        ('headers = {"Authorization": f"Bearer {api_key}}', 'headers = {"Authorization": f"Bearer {api_key}"}'),
        ('form_data = {model: model}', 'form_data = {"model": model}'),
        ('{role: system, content:', '{"role": "system", "content":'),
        ('{role: user, content:', '{"role": "user", "content":'),
        ("context_hint = f\\n추가", 'context_hint = f"\\n추가'),
        ("if req.context else ", 'if req.context else ""'),
        ("intent: f'{req.query[:40]}' 질문", 'intent: f"\'{req.query[:40]}\' 질문'),
        ("fOPENAI_API_KEY가", 'f"OPENAI_API_KEY가'),
        ("grade = (\n        A (우수)", 'grade = (\n        "A (우수)'),
        ("else B (양호)", 'else "B (양호)'),
        ("else C (보통)", 'else "C (보통)'),
        ("else D (취약)", 'else "D (취약)'),
        ("region = (req.region or 전국)", 'region = (req.region or "전국")'),
        (".strip() or 전국", '.strip() or "전국"'),
        ("school_type = (req.schoolType or 고등)", 'school_type = (req.schoolType or "고등")'),
        ("goal = (req.goal or 내신)", 'goal = (req.goal or "내신")'),
        ("school_name = (req.school_name or 선택 학교)", 'school_name = (req.school_name or "선택 학교")'),
        ("objective: req.objective or balanced", 'objective: req.objective or "balanced"'),
        ("_REGION_PROFILES[전국]", '_REGION_PROFILES["전국"]'),
        ("_REGION_PROFILES.get(region, _REGION_PROFILES[전국])", '_REGION_PROFILES.get(region, _REGION_PROFILES["전국"])'),
        ("profile = _REGION_PROFILES.get(region, _REGION_PROFILES[\"전국\"])", 'profile = _REGION_PROFILES.get(region, _REGION_PROFILES["전국"])'),
        ('r["subject"] == 전체', 'r["subject"] == "전체"'),
        ("SubjectScore(subject=수학", 'SubjectScore(subject="수학"'),
        ("SubjectScore(subject=영어", 'SubjectScore(subject="영어"'),
        ("SubjectScore(subject=국어", 'SubjectScore(subject="국어"'),
        ("_RESOURCES_MAP.get(sub.subject, EBS 무료 강좌)", '_RESOURCES_MAP.get(sub.subject, "EBS 무료 강좌")'),
        ("units[: max(2,", "units[: max(2,"),  # no change
        ("[기초 개념, 심화 응용]", '["기초 개념", "심화 응용"]'),
        ("triggers else [현재 주요 위험 지표 없음]", 'triggers else ["현재 주요 위험 지표 없음"]'),
        ("recommendedActions: actions[\"level\"]", 'recommendedActions: actions[level]'),
        ("sample_domain = risk if any(w in req.query for w in [위험, 격차, 성적])",
         'sample_domain = "risk" if any(w in req.query for w in ["위험", "격차", "성적"])'),
        ("else equity if any(w in req.query for w in [지역, 형평, 불평등])",
         'else "equity" if any(w in req.query for w in ["지역", "형평", "불평등"])'),
        ("else pathway if any(w in req.query for w in [경로, 공부, 순서])",
         'else "pathway" if any(w in req.query for w in ["경로", "공부", "순서"])'),
        ("else general", 'else "general"'),
        ("triggers.append(평균 성적 60점 미만)", 'triggers.append("평균 성적 60점 미만")'),
        ("triggers.append(수업 참여도 낮음)", 'triggers.append("수업 참여도 낮음")'),
        ("if triggers else 안정적인 학습 상태입니다.)", 'if triggers else "안정적인 학습 상태입니다.")'),
        ("data.get(schoolInfo, [{}])[1].get(row, [{}])[0]",
         'data.get("schoolInfo", [{}])[1].get("row", [{}])[0]'),
        ("data.get(schoolInfo, [{}])[1].get(row, [{}])[0]",
         'data.get("schoolInfo", [{}])[1].get("row", [{}])[0]'),
        ("payload.get(schoolInfo, [{}])[1].get(row, [])",
         'payload.get("schoolInfo", [{}])[1].get("row", [])'),
        ("payload.get(hisTimetable, [{}])[1].get(row, [])",
         'payload.get("hisTimetable", [{}])[1].get("row", [])'),
        ("isinstance(data.get(\"schoolInfo\"), list)", 'isinstance(data.get("schoolInfo"), list)'),
        ("isinstance(payload.get(\"schoolInfo\"), list)", 'isinstance(payload.get("schoolInfo"), list)'),
        ("isinstance(payload.get(\"hisTimetable\"), list)", 'isinstance(payload.get("hisTimetable"), list)'),
        ("raise HTTPException(status_code=502, detail=NEIS 호출 실패)",
         'raise HTTPException(status_code=502, detail="NEIS 호출 실패")'),
        ("Type: json,", '"Type": "json",'),
        ("KEY: key,", '"KEY": key,'),
        ("pIndex: 1,", '"pIndex": 1,'),
        ("pSize:", '"pSize":'),
        ("SCHUL_NM: query", '"SCHUL_NM": query'),
        ("ATPT_OFCDC_SC_CODE: atpt", '"ATPT_OFCDC_SC_CODE": atpt'),
        ("SD_SCHUL_CODE: school", '"SD_SCHUL_CODE": school'),
        ("ALL_TI_YMD: today", '"ALL_TI_YMD": today'),
        ("GRADE: str(grade)", '"GRADE": str(grade)'),
        ("CLASS_NM: str(cls)", '"CLASS_NM": str(cls)'),
        ("PERIO: 1, ITRT_CNTNT: 국어", '"PERIO": 1, "ITRT_CNTNT": "국어"'),
        ("PERIO: 2, ITRT_CNTNT: 수학", '"PERIO": 2, "ITRT_CNTNT": "수학"'),
        ("PERIO: 3, ITRT_CNTNT: 영어", '"PERIO": 3, "ITRT_CNTNT": "영어"'),
        ("{ATPT_OFCDC_SC_CODE: B10", '{"ATPT_OFCDC_SC_CODE": "B10"'),
        ("{ATPT_OFCDC_SC_CODE: J10", '{"ATPT_OFCDC_SC_CODE": "J10"'),
        ("SCHUL_NM: 서울고등학교", '"SCHUL_NM": "서울고등학교"'),
        ("SCHUL_NM: 수원고등학교", '"SCHUL_NM": "수원고등학교"'),
        ("ATPT_OFCDC_SC_NM: 서울특별시교육청", '"ATPT_OFCDC_SC_NM": "서울특별시교육청"'),
        ("ATPT_OFCDC_SC_NM: 경기도교육청", '"ATPT_OFCDC_SC_NM": "경기도교육청"'),
        ("SD_SCHUL_CODE: 7010569", '"SD_SCHUL_CODE": "7010569"'),
        ("SD_SCHUL_CODE: 7530010", '"SD_SCHUL_CODE": "7530010"'),
        ("SCHUL_NM: 샘플고", '"SCHUL_NM": "샘플고"'),
        ("ATPT_OFCDC_SC_NM: 서울특별시교육청}", '"ATPT_OFCDC_SC_NM": "서울특별시교육청"}'),
        ("message: NEIS 키/학교코드가 없어 샘플 데이터 반환", 'message: "NEIS 키/학교코드가 없어 샘플 데이터 반환"'),
        ("message: NEIS_API_KEY가 없어 샘플 목록 반환", 'message: "NEIS_API_KEY가 없어 샘플 목록 반환"'),
        ("message: NEIS_API_KEY가 없어 샘플 시간표 반환", 'message: "NEIS_API_KEY가 없어 샘플 시간표 반환"'),
        ("source: sample,", '"source": "sample",'),
        ("source: neis,", '"source": "neis",'),
        ("integration: sample_only,", '"integration": "sample_only",'),
        ("engine: simulated-sklearn,", '"engine": "simulated-sklearn",'),
        ("engine: simulated-sb3,", '"engine": "simulated-sb3",'),
        ("engine: simulated-shap,", '"engine": "simulated-shap",'),
        ("integration: heuristic_only,", '"integration": "heuristic_only",'),
        ("role: AI 모델 학습용 기준 데이터(데모)", 'role: "AI 모델 학습용 기준 데이터(데모)"'),
        ("role: 정확도 향상용 보조 데이터(데모)", 'role: "정확도 향상용 보조 데이터(데모)"'),
        ("answer: content}", '"answer": content}'),
        ("return {answer: content}", 'return {"answer": content}'),
        ("return {transcript: text, model: model}", 'return {"transcript": text, "model": model}'),
        ("return {classInput:", 'return {"classInput":'),
        ("update={classQualityScore:", 'update={"classQualityScore":'),
        ("update={koreanLevel:", 'update={"koreanLevel":'),
        ("update={planQuality:", 'update={"planQuality":'),
        ("update={attendanceImpact:", 'update={"attendanceImpact":'),
        ("update={attendance:", 'update={"attendance":'),
        ("return {qualityScore:", 'return {"qualityScore":'),
        ("return {subjectRisk:", 'return {"subjectRisk":'),
        ("return {predictedAverage:", 'return {"predictedAverage":'),
        ("return {topDriver:", 'return {"topDriver":'),
        ("return {effectiveHours:", 'return {"effectiveHours":'),
        ("input: ClassAnalysisInput(", '"input": ClassAnalysisInput('),
        ("meta: {", '"meta": {'),
        ("sentenceCount: sentence_count", '"sentenceCount": sentence_count'),
        ("questionCount: question_count", '"questionCount": question_count'),
        ("repeatedSentenceCount: repeated", '"repeatedSentenceCount": repeated'),
        ("ok: True,", '"ok": True,'),
        ("service: class-orbit-api,", 'service: "class-orbit-api",'),
        ("version: 0.1.0,", 'version: "0.1.0",'),
        ("neis_configured:", '"neis_configured":'),
        ("openai_configured:", '"openai_configured":'),
        ("kess: stub_env_ready if kess_stub else sample_only", 'kess: "stub_env_ready" if kess_stub else "sample_only"'),
        ("school_alimi: stub_env_ready if alimi_stub else sample_only", 'school_alimi: "stub_env_ready" if alimi_stub else "sample_only"'),
        ("risk_rl_shap: simulation", 'risk_rl_shap: "simulation"'),
        ("cors_mode: any if _cors_raw == \"*\" else allowlist", 'cors_mode: "any" if _cors_raw == "*" else "allowlist"'),
        ("rate_limit_per_minute:", '"rate_limit_per_minute":'),
        ("internal_api_key_required:", '"internal_api_key_required":'),
        ("integrations: {", '"integrations": {'),
        ("security: {", '"security": {'),
        ("classInput: derived", '"classInput": derived'),
        ("meta: derived", '"meta": derived'),
        ("classResult: result", '"classResult": result'),
        ("classResult: class_result", '"classResult": class_result'),
        ("analysisMeta: derived", '"analysisMeta": derived'),
        ("riskInput: linked_risk", '"riskInput": linked_risk'),
        ("riskResult: risk_result", '"riskResult": risk_result'),
        ("scheduleInput: linked_schedule", '"scheduleInput": linked_schedule'),
        ("scheduleResult: schedule_result", '"scheduleResult": schedule_result'),
        ("twinInput: linked_twin", '"twinInput": linked_twin'),
        ("twinResult: twin_result", '"twinResult": twin_result'),
        ("causalInput: linked_causal", '"causalInput": linked_causal'),
        ("causalResult: causal_result", '"causalResult": causal_result'),
        ("xaiInput: linked_xai", '"xaiInput": linked_xai'),
        ("xaiResult: xai_result", '"xaiResult": xai_result'),
        ("schoolInfo: {SCHUL_NM:", '"schoolInfo": {"SCHUL_NM":'),
        ("scheduleCount: 5", '"scheduleCount": 5'),
        ("selected: {atpt_code:", '"selected": {"atpt_code":'),
        ("schoolInfo: row", '"schoolInfo": row'),
        ("schools: schools", '"schools": schools'),
        ("count: len(schools)", '"count": len(schools)'),
        ("rows: simplified", '"rows": simplified'),
        ("date: today", '"date": today'),
        ("metrics: {", '"metrics": {'),
        ("roadmap: KESS_API_KEY", 'roadmap: "KESS_API_KEY'),
        ("roadmap: SCHOOL_ALIMI_API_KEY", 'roadmap: "SCHOOL_ALIMI_API_KEY'),
        ("roadmap: 학습된 모델", 'roadmap: "학습된 모델'),
        ("roadmap: Stable-Baselines3", 'roadmap: "Stable-Baselines3'),
        ("roadmap: shap 라이브러리", 'roadmap: "shap 라이브러리'),
        ("features: {", '"features": {'),
        ("school: {name:", '"school": {"name":'),
        ("result: result", '"result": result'),
        ("result: schedule", '"result": schedule'),
        ("weights: weights", '"weights": weights'),
        ("top: top", '"top": top'),
        ("answer: (", '"answer": ('),
        ("simulation: True", '"simulation": True'),
        ("region: region", '"region": region'),
        ("year: year", '"year": year'),
        ("grade: grade", '"grade": grade'),
        ("goal: goal", '"goal": goal'),
        ("pathSteps: path_steps", '"pathSteps": path_steps'),
        ("totalEstimatedWeeks: total_weeks", '"totalEstimatedWeeks": total_weeks'),
        ("studyHoursPerDay: req.studyHoursPerDay", '"studyHoursPerDay": req.studyHoursPerDay'),
        ("summary: (", '"summary": ('),
        ("rank: rank", '"rank": rank'),
        ("subject: sub.subject", '"subject": sub.subject'),
        ("currentScore: sub.score", '"currentScore": sub.score'),
        ("targetScore:", '"targetScore":'),
        ("weeklyHours:", '"weeklyHours":'),
        ("focusUnits: weak_units", '"focusUnits": weak_units'),
        ("estimatedWeeks: weeks_needed", '"estimatedWeeks": weeks_needed'),
        ("publicResource: resource", '"publicResource": resource'),
        ("tip: (", '"tip": ('),
        ("riskScore: round", '"riskScore": round'),
        ("level: level", '"level": level'),
        ("trend: round", '"trend": round'),
        ("avgScore: round", '"avgScore": round'),
        ("triggers: triggers", '"triggers": triggers'),
        ("recommendedActions: actions", '"recommendedActions": actions'),
        ("equityScore: equity_score", '"equityScore": equity_score'),
        ("schoolType: school_type", '"schoolType": school_type'),
        ("vsNational: {", '"vsNational": {'),
        ("avgDiff:", '"avgDiff":'),
        ("equityDiff:", '"equityDiff":'),
        ("recommendations: recommendations", '"recommendations": recommendations'),
        ("matchedCount: len(matched)", '"matchedCount": len(matched)'),
        ("resources: matched", '"resources": matched'),
        ("domain: sample_domain", '"domain": sample_domain'),
        ("intent:", '"intent":'),
        ("keyEntities: {}", '"keyEntities": {}'),
        ("suggestedActions: [", '"suggestedActions": ['),
        ("backend/.env 파일에 OPENAI_API_KEY 설정", '"backend/.env 파일에 OPENAI_API_KEY 설정"'),
        ("동일 질문을 다시 시도", '"동일 질문을 다시 시도"'),
        ("payload = {model: model", 'payload = {"model": model'),
        ("response_format: {\"type\": \"json_object\"}", '"response_format": {"type": "json_object"}'),
        ("messages: messages", '"messages": messages'),
        ("temperature: 0.2", '"temperature": 0.2'),
        ("attendance: 100 - input_data.attendance", '"attendance": 100 - input_data.attendance'),
        ("understanding: 100 - input_data.understanding", '"understanding": 100 - input_data.understanding'),
        ("fatigue: input_data.fatigue", '"fatigue": input_data.fatigue'),
        ("classQuality: 100 - input_data.classQuality", '"classQuality": 100 - input_data.classQuality'),
        ("averageScore: 100 - req.averageScore", '"averageScore": 100 - req.averageScore'),
        ("attendanceRate: 100 - req.attendanceRate", '"attendanceRate": 100 - req.attendanceRate'),
        ("classQualityScore: 100 - req.classQualityScore", '"classQualityScore": 100 - req.classQualityScore'),
        ("schoolEnvironmentScore: 100 - req.schoolEnvironmentScore", '"schoolEnvironmentScore": 100 - req.schoolEnvironmentScore'),
        ("high: [", '"high": ['),
        ("medium: [", '"medium": ['),
        ("low: [", '"low": ['),
        ("수학: [수와 연산", '"수학": ["수와 연산"'),
        ("영어: [어휘/발음", '"영어": ["어휘/발음"'),
        ("국어: [문학", '"국어": ["문학"'),
        ("과학: [물리", '"과학": ["물리"'),
        ("사회: [한국사", '"사회": ["한국사"'),
        ("수학: EBS 수학", '"수학": "EBS 수학'),
        ("영어: EBS 영어", '"영어": "EBS 영어'),
        ("국어: EBS 국어", '"국어": "EBS 국어'),
        ("과학: EBS 과학", '"과학": "EBS 과학'),
        ("사회: EBS 사회", '"사회": "EBS 사회'),
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
        ("고등: 0.0", '"고등": 0.0'),
        ("중학: 1.5", '"중학": 1.5'),
        ("초등: 3.0", '"초등": 3.0'),
        ("{subject: 수학, title:", '{"subject": "수학", "title":'),
        ("{subject: 영어, title:", '{"subject": "영어", "title":'),
        ("{subject: 국어, title:", '{"subject": "국어", "title":'),
        ("{subject: 과학, title:", '{"subject": "과학", "title":'),
        ("{subject: 사회, title:", '{"subject": "사회", "title":'),
        ("{subject: 전체, title:", '{"subject": "전체", "title":'),
        ("type: video", '"type": "video"'),
        ("type: mooc", '"type": "mooc"'),
        ("type: library", '"type": "library"'),
        ("cost: 무료", '"cost": "무료"'),
        ("url: https://", '"url": "https://'),
        ("minLevel:", '"minLevel":'),
        ("maxLevel:", '"maxLevel":'),
        ("difficulty:", '"difficulty":'),
        ("기초~중급", '"기초~중급"'),
        ("중급~고급", '"중급~고급"'),
        ("기초", '"기초"'),
        ("중급", '"중급"'),
        ("대학 수준", '"대학 수준"'),
        ("전 수준", '"전 수준"'),
        ("_NLQ_SYSTEM_PROMPT = 당신은", '_NLQ_SYSTEM_PROMPT = """당신은'),
        ("suggestedActions: [\"<다음 단계 1>\", \"<다음 단계 2>\"]\n}\n\"\"\"", 'suggestedActions: ["<다음 단계 1>", "<다음 단계 2>"]\n}\n"""'),
    ]
    for old, new in reps:
        text = text.replace(old, new)
    return text


def fix_unclosed_fstrings_and_urls(text: str) -> str:
    text = re.sub(
        r'detail=f"(NEIS schoolInfo 조회 실패 \(status=\{res\.status_code\}\): \{snippet\}),',
        r'detail=f"NEIS schoolInfo 조회 실패 (status={res.status_code}): {snippet}",',
        text,
    )
    text = re.sub(
        r'detail=f"(NEIS 시간표 조회 실패 \(status=\{res\.status_code\}\): \{snippet\}),',
        r'detail=f"NEIS 시간표 조회 실패 (status={res.status_code}): {snippet}",',
        text,
    )
    text = re.sub(
        r'detail=f"(STT 실패 \(status=\{res\.status_code\}\): \{snippet\})',
        r'detail=f"STT 실패 (status={res.status_code}): {snippet}")',
        text,
    )
    text = re.sub(
        r'detail=f"(NLQ OpenAI 호출 실패: \{res\.text\[:200\]\})',
        r'detail=f"NLQ OpenAI 호출 실패: {res.text[:200]}")',
        text,
    )
    text = re.sub(
        r'detail=f"(OpenAI 호출 실패: \{res\.text\[:200\]\})',
        r'detail=f"OpenAI 호출 실패: {res.text[:200]}")',
        text,
    )
    return text


def process_file(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = _fix.fix_known_literals(text)
    text = _fix.fix_getenv(text)
    text = _fix.fix_paths_and_urls(text)
    text = _fix.fix_headers_and_attrs(text)
    text = fix_remaining_patterns(text)
    text = fix_fstrings(text)
    text = fix_ternary_korean_strings(text)

    lines = []
    for line in text.splitlines():
        line = quote_dict_keys(line)
        line = fix_tuple_strings(line)
        line = fix_list_string_items(line)
        line = fix_bare_string_values(line)
        lines.append(line)
    text = "\n".join(lines) + "\n"
    text = fix_docstring_blocks(text)
    text = fix_unclosed_fstrings_and_urls(text)

    path.write_text(text, encoding="utf-8")
    print(f"complete-fixed {path.relative_to(ROOT)}")


def verify(path: Path) -> bool:
    src = path.read_text(encoding="utf-8")
    try:
        ast.parse(src)
        return True
    except SyntaxError as e:
        print(f"  still broken {path}: line {e.lineno}: {e.msg}", file=sys.stderr)
        lines = src.splitlines()
        if e.lineno and e.lineno <= len(lines):
            print(f"    {lines[e.lineno - 1][:120]}", file=sys.stderr)
        return False


def main() -> int:
    paths = [ROOT / "backend/app/main.py", ROOT / "backend/tests/test_smoke.py"]
    for p in paths:
        process_file(p)
    ok = all(verify(p) for p in paths)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
