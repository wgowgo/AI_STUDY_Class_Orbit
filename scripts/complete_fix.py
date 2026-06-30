# -*- coding: utf-8 -*-
"""One-shot restoration for backend/app/main.py after safe fix."""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "backend/app/main.py"

COMPREHENSION_KEYS = frozenset("k v s r o p e m x i j n".split())

API_KEYS = frozenset(
    """
    input meta ok service version integrations security classInput classResult analysisMeta
    riskInput riskResult scheduleInput scheduleResult twinInput twinResult causalInput causalResult
    xaiInput xaiResult qualityScore explanationRatio feedback subjectRisk dropoutProbability level
    effectiveHours routine predictedAverage delta comment topDriver topWeight summary ranking
    attendance understanding fatigue classQuality averageScore attendanceRate classQualityScore
    schoolEnvironmentScore source message schoolInfo scheduleCount selected count schools rows date
    integration simulation region year grade metrics role roadmap engine result weights top
    objective answer transcript model domain intent keyEntities suggestedActions pathSteps
    totalEstimatedWeeks studyHoursPerDay goal rank subject currentScore targetScore weeklyHours
    focusUnits estimatedWeeks publicResource tip riskScore trend avgScore triggers recommendedActions
    equityScore schoolType vsNational avgDiff equityDiff recommendations matchedCount resources
    features school neis_configured openai_configured kess school_alimi risk_rl_shap cors_mode
    rate_limit_per_minute internal_api_key_required TYPE KEY pIndex pSize SCHUL_NM ATPT_OFCDC_SC_CODE
    SD_SCHUL_CODE ALL_TI_YMD GRADE CLASS_NM PERIO ITRT_CNTNT ATPT_OFCDC_SC_NM high medium low
    simulation metrics average_score regional_gap low_achievers_pct high_achievers_pct roadmap
    """.split()
)


def should_quote_key(key: str) -> bool:
    if key in COMPREHENSION_KEYS:
        return False
    if key in API_KEYS:
        return True
    if re.search(r"[a-z][A-Z]", key):
        return True
    return False


def quote_api_dict_keys(text: str) -> str:
    def repl_brace(m: re.Match[str]) -> str:
        key = m.group(1)
        return f'{{"{key}":' if should_quote_key(key) else m.group(0)

    def repl_comma(m: re.Match[str]) -> str:
        key = m.group(1)
        return f', "{key}":' if should_quote_key(key) else m.group(0)

    # Only quote inside return/param dict literals — skip dict comprehensions `{k:`
    lines = []
    for line in text.splitlines():
        if " for " in line and " in " in line and line.strip().startswith("return {"):
            lines.append(line)
            continue
        line = re.sub(r"\{([a-zA-Z_][a-zA-Z0-9_]*):", repl_brace, line)
        line = re.sub(r",\s*([a-zA-Z_][a-zA-Z0-9_]*):", repl_comma, line)
        lines.append(line)
    return "\n".join(lines)


def fix_fstrings(text: str) -> str:
    text = re.sub(r"(?<![a-zA-Z])f\{", 'f"{', text)
    text = re.sub(r"(?<![a-zA-Z])f([가-힣])", r'f"\1', text)
    return text


def fix_ternary_strings(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if re.search(r"=\s*\(\s*$", line.rstrip()):
            out.append(line)
            i += 1
            while i < len(lines):
                ln = lines[i]
                st = ln.strip()
                if st == ")":
                    out.append(ln)
                    i += 1
                    break
                if st.startswith(("if ", "else if ")):
                    out.append(ln)
                elif st.startswith("else "):
                    rest = st[5:].strip()
                    if rest.startswith("if "):
                        out.append(ln)
                    else:
                        ind = ln[: len(ln) - len(ln.lstrip())]
                        out.append(f'{ind}else "{rest.rstrip(",")}"')
                elif st and not st.startswith(("if ", "else", '"', "f\"", "+ (")):
                    if re.search(r"[가-힣]", st) and not re.match(r"[\w.]+\(", st):
                        ind = ln[: len(ln) - len(ln.lstrip())]
                        out.append(f'{ind}"{st.rstrip(",")}"')
                    else:
                        out.append(ln)
                else:
                    out.append(ln)
                i += 1
            continue
        out.append(line)
        i += 1
    return "\n".join(out)


def fix_tuple_labels(text: str) -> str:
    return re.sub(
        r"\(([가-힣][가-힣A-Za-z0-9 /·\-]*),\s",
        lambda m: f'("{m.group(1)}", ',
        text,
    )


def fix_get_calls(text: str) -> str:
    text = re.sub(r"\.get\(([A-Z][A-Z0-9_]*)\)", r'.get("\1")', text)
    text = re.sub(r"payload\.get\(([a-z][a-zA-Z0-9_]*)\)", r'payload.get("\1")', text)
    text = re.sub(r"data\.get\(([a-z][a-zA-Z0-9_]*)\)", r'data.get("\1")', text)
    text = re.sub(r"res\.get\(([A-Z][A-Z0-9_]*)\)", r'res.get("\1")', text)
    return text


def fix_misc(text: str) -> str:
    reps = [
        ("code.startswith(INFO)", 'code.startswith("INFO")'),
        ("msg = res.get(\"MESSAGE\", NEIS API 오류)", 'msg = res.get("MESSAGE", "NEIS API 오류")'),
        ("detail=fNEIS:", 'detail=f"NEIS:'),
        ("if auth.lower().startswith(bearer )", 'if auth.lower().startswith("bearer ")'),
        ("detail=Invalid or missing internal API key", 'detail="Invalid or missing internal API key"'),
        ("else unknown", 'else "unknown"'),
        ("region = (req.region or 전국)", 'region = (req.region or "전국")'),
        (".strip() or 전국", '.strip() or "전국"'),
        ("school_type = (req.schoolType or 고등)", 'school_type = (req.schoolType or "고등")'),
        ("goal = (req.goal or 내신)", 'goal = (req.goal or "내신")'),
        ("school_name = (req.school_name or 선택 학교)", 'school_name = (req.school_name or "선택 학교")'),
        ("objective: req.objective or balanced", '"objective": req.objective or "balanced"'),
        ("_REGION_PROFILES[전국]", '_REGION_PROFILES["전국"]'),
        ('r["subject"] == 전체', 'r["subject"] == "전체"'),
        ("SubjectScore(subject=수학", 'SubjectScore(subject="수학"'),
        ("SubjectScore(subject=영어", 'SubjectScore(subject="영어"'),
        ("SubjectScore(subject=국어", 'SubjectScore(subject="국어"'),
        ('_RESOURCES_MAP.get(sub.subject, EBS 무료 강좌)', '_RESOURCES_MAP.get(sub.subject, "EBS 무료 강좌")'),
        ("[기초 개념, 심화 응용]", '["기초 개념", "심화 응용"]'),
        ("triggers else [현재 주요 위험 지표 없음]", 'triggers else ["현재 주요 위험 지표 없음"]'),
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
        ("_NLQ_SYSTEM_PROMPT = 당신은", '_NLQ_SYSTEM_PROMPT = """당신은'),
        ("suggestedActions: [<다음 단계 1>, <다음 단계 2>]\n}\n\n",
         'suggestedActions: ["<다음 단계 1>", "<다음 단계 2>"]\n}\n"""\n\n'),
        ('{role: system, content: "You are an educational AI assistant."}',
         '{"role": "system", "content": "You are an educational AI assistant."}'),
        ('messages.append({role: user, content: req.message})',
         'messages.append({"role": "user", "content": req.message})'),
        ("{Authorization: fBearer", '{"Authorization": f"Bearer'),
        ("Content-Type: application/json}", '"Content-Type": "application/json"}'),
        ("form_data = {model: model}", 'form_data = {"model": model}'),
        ("{file: (file.filename or audio,", '{"file": (file.filename or "audio",'),
        ("file.content_type or application/octet-stream)", 'file.content_type or "application/octet-stream")'),
        ("detail=fOpenAI", 'detail=f"OpenAI'),
        ("detail=fSTT", 'detail=f"STT'),
        ("detail=fNLQ", 'detail=f"NLQ'),
        ("detail=fNEIS schoolInfo", 'detail=f"NEIS schoolInfo'),
        ("detail=fNEIS 시간표", 'detail=f"NEIS 시간표'),
        ('detail="OPENAI_API_KEY가 설정되지 않았습니다.)',
         'detail="OPENAI_API_KEY가 설정되지 않았습니다.")'),
        ("{model: model, messages: messages, temperature: 0.4}",
         '{"model": model, "messages": messages, "temperature": 0.4}'),
        ("payload = {model: model, messages: messages, temperature: 0.2, response_format: {type: json_object}}",
         'payload = {"model": model, "messages": messages, "temperature": 0.2, "response_format": {"type": "json_object"}}'),
        ("{role: system, content: _NLQ_SYSTEM_PROMPT}", '{"role": "system", "content": _NLQ_SYSTEM_PROMPT}'),
        ("{role: user, content: user_msg}", '{"role": "user", "content": user_msg}'),
        ('parsed = {domain: general, intent: 파싱 실패, answer: raw, suggestedActions: []}',
         '{"domain": "general", "intent": "파싱 실패", "answer": raw, "suggestedActions": []}'),
        ("service: class-orbit-api,", 'service: "class-orbit-api",'),
        ("version: 0.1.0,", 'version: "0.1.0",'),
        ("kess: stub_env_ready if kess_stub else sample_only",
         'kess: "stub_env_ready" if kess_stub else "sample_only"'),
        ("school_alimi: stub_env_ready if alimi_stub else sample_only",
         'school_alimi: "stub_env_ready" if alimi_stub else "sample_only"'),
        ("risk_rl_shap: simulation", 'risk_rl_shap: "simulation"'),
        ('cors_mode: any if _cors_raw == "*" else allowlist',
         'cors_mode: "any" if _cors_raw == "*" else "allowlist"'),
        ("message: NEIS 키/학교코드가 없어 샘플 데이터 반환",
         'message: "NEIS 키/학교코드가 없어 샘플 데이터 반환"'),
        ("message: NEIS_API_KEY가 없어 샘플 목록 반환",
         'message: "NEIS_API_KEY가 없어 샘플 목록 반환"'),
        ("message: NEIS_API_KEY가 없어 샘플 시간표 반환",
         'message: "NEIS_API_KEY가 없어 샘플 시간표 반환"'),
        ('source: sample,', '"source": "sample",'),
        ('source: neis,', '"source": "neis",'),
        ("integration: sample_only,", '"integration": "sample_only",'),
        ("engine: simulated-sklearn,", '"engine": "simulated-sklearn",'),
        ("engine: simulated-sb3,", '"engine": "simulated-sb3",'),
        ("engine: simulated-shap,", '"engine": "simulated-shap",'),
        ("integration: heuristic_only,", '"integration": "heuristic_only",'),
        ('role: AI 모델 학습용 기준 데이터(데모)', 'role: "AI 모델 학습용 기준 데이터(데모)"'),
        ('role: 정확도 향상용 보조 데이터(데모)', 'role: "정확도 향상용 보조 데이터(데모)"'),
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
        ('{PERIO: 1, ITRT_CNTNT: 국어}', '{"PERIO": 1, "ITRT_CNTNT": "국어"}'),
        ('{PERIO: 2, ITRT_CNTNT: 수학}', '{"PERIO": 2, "ITRT_CNTNT": "수학"}'),
        ('{PERIO: 3, ITRT_CNTNT: 영어}', '{"PERIO": 3, "ITRT_CNTNT": "영어"}'),
        ('{ATPT_OFCDC_SC_CODE: B10, ATPT_OFCDC_SC_NM: 서울특별시교육청, SD_SCHUL_CODE: 7010569, SCHUL_NM: 서울고등학교}',
         '{"ATPT_OFCDC_SC_CODE": "B10", "ATPT_OFCDC_SC_NM": "서울특별시교육청", "SD_SCHUL_CODE": "7010569", "SCHUL_NM": "서울고등학교"}'),
        ('{ATPT_OFCDC_SC_CODE: J10, ATPT_OFCDC_SC_NM: 경기도교육청, SD_SCHUL_CODE: 7530010, SCHUL_NM: 수원고등학교}',
         '{"ATPT_OFCDC_SC_CODE": "J10", "ATPT_OFCDC_SC_NM": "경기도교육청", "SD_SCHUL_CODE": "7530010", "SCHUL_NM": "수원고등학교"}'),
        ('schoolInfo: {SCHUL_NM: 샘플고, ATPT_OFCDC_SC_NM: 서울특별시교육청}',
         '"schoolInfo": {"SCHUL_NM": "샘플고", "ATPT_OFCDC_SC_NM": "서울특별시교육청"}'),
        ('summary: f{top[0]} 요인이 가장 큰 원인으로 추정됩니다. 다음 영향 요인은 {second[0]}입니다.,',
         '"summary": f"{top[0]} 요인이 가장 큰 원인으로 추정됩니다. 다음 영향 요인은 {second[0]}입니다.",'),
        ("attendance: 100 - input_data.attendance,", '"attendance": 100 - input_data.attendance,'),
        ("understanding: 100 - input_data.understanding,", '"understanding": 100 - input_data.understanding,'),
        ("fatigue: input_data.fatigue,", '"fatigue": input_data.fatigue,'),
        ("classQuality: 100 - input_data.classQuality,", '"classQuality": 100 - input_data.classQuality,'),
        ("Type: json,", '"Type": "json",'),
        ("KEY: key,", '"KEY": key,'),
        ("pIndex: 1,", '"pIndex": 1,'),
        ("SCHUL_NM: query", '"SCHUL_NM": query'),
        ("ATPT_OFCDC_SC_CODE: atpt", '"ATPT_OFCDC_SC_CODE": atpt'),
        ("SD_SCHUL_CODE: school", '"SD_SCHUL_CODE": school'),
        ("ALL_TI_YMD: today", '"ALL_TI_YMD": today'),
        ("GRADE: str(grade)", '"GRADE": str(grade)'),
        ("CLASS_NM: str(cls)", '"CLASS_NM": str(cls)'),
        ("담당 교사, 상담사와 즉시 면담 권장,", '"담당 교사, 상담사와 즉시 면담 권장",'),
        ("학습 부진 원인 파악(학습 결손 vs 심리적 요인),", '"학습 부진 원인 파악(학습 결손 vs 심리적 요인)",'),
        ("방과후 보충 수업 또는 멘토링 연결,", '"방과후 보충 수업 또는 멘토링 연결",'),
        ("학부모 알림 발송,", '"학부모 알림 발송",'),
        ("취약 과목 집중 복습 스케줄 재조정,", '"취약 과목 집중 복습 스케줄 재조정",'),
        ("2주 내 교사 점검 면담,", '"2주 내 교사 점검 면담",'),
        ("자기주도 학습 습관 점검,", '"자기주도 학습 습관 점검",'),
        ("현재 학습 방향 유지,", '"현재 학습 방향 유지",'),
        ("주간 자기 점검 권장,", '"주간 자기 점검 권장",'),
        ("backend/.env 파일에 OPENAI_API_KEY 설정", '"backend/.env 파일에 OPENAI_API_KEY 설정"'),
        ("동일 질문을 다시 시도", '"동일 질문을 다시 시도"'),
        ("return {answer: content}", 'return {"answer": content}'),
        ("return {transcript: text, model: model}", 'return {"transcript": text, "model": model}'),
        ("update={classQualityScore:", 'update={"classQualityScore":'),
        ("update={koreanLevel:", 'update={"koreanLevel":'),
        ("update={planQuality:", 'update={"planQuality":'),
        ("update={attendanceImpact:", 'update={"attendanceImpact":'),
        ("update={attendance:", 'update={"attendance":'),
        ("derived[input]", 'derived["input"]'),
        ("derived[meta]", 'derived["meta"]'),
        ("class_result[qualityScore]", 'class_result["qualityScore"]'),
        ("risk_result[subjectRisk]", 'risk_result["subjectRisk"]'),
        ("schedule_result[effectiveHours]", 'schedule_result["effectiveHours"]'),
        ("actions[level]", 'actions[level]'),
        ("client.get(https://open.neis.go.kr/hub/schoolInfo, params=params)",
         'client.get("https://open.neis.go.kr/hub/schoolInfo", params=params)'),
        ("client.get(https://open.neis.go.kr/hub/hisTimetable, params=params)",
         'client.get("https://open.neis.go.kr/hub/hisTimetable", params=params)'),
        ("client.post(https://api.openai.com/v1/chat/completions, headers=headers, json=payload)",
         'client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)'),
        ('seed = sum(ord(c) for c in f"{region}-{year}-{grade}) % 17"',
         'seed = sum(ord(c) for c in f"{region}-{year}-{grade}") % 17'),
        ("seed = sum(ord(c) for c in f{region}-{year}-{grade}) % 17",
         'seed = sum(ord(c) for c in f"{region}-{year}-{grade}") % 17'),
        ("key = f{req.atpt_code or ''}-{req.school_code or ''}-{school_name}",
         'key = f"{req.atpt_code or \'\'}-{req.school_code or \'\'}-{school_name}"'),
        ('cache_key = f"summary|{atpt}|{school}', 'cache_key = f"summary|{atpt}|{school}"'),
        ('cache_key = f"schools|{query}|{atpt_code or \'\'}|{size}', 'cache_key = f"schools|{query}|{atpt_code or \'\'}|{size}"'),
        ('cache_key = f"{atpt_code}|{school_code}|{grade}|{cls}|{today}', 'cache_key = f"{atpt_code}|{school_code}|{grade}|{cls}|{today}"'),
        ("user_msg = f{req.query}{context_hint}", 'user_msg = f"{req.query}{context_hint}"'),
        ("answer: (\n                OPENAI_API_KEY가 설정되지 않았습니다.\\n",
         '"answer": (\n                "OPENAI_API_KEY가 설정되지 않았습니다.\\n"'),
        ("                f질문 요약: {req.message[:120]}\\n",
         '                f"질문 요약: {req.message[:120]}\\n"'),
        ("                키 설정 후 동일 엔드포인트로 실연결됩니다.",
         '                "키 설정 후 동일 엔드포인트로 실연결됩니다."'),
        ('headers = {"Authorization": f"Bearer {api_key}, "Content-Type": "application/json"}"',
         'headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}'),
        ("data[choices][0][message][content]", 'data["choices"][0]["message"]["content"]'),
        ("res.json()[choices][0][message][content]", 'res.json()["choices"][0]["message"]["content"]'),
        ('res.json()["choices"][0]["message"]["content"]', 'res.json()["choices"][0]["message"]["content"]'),
        ("roadmap: KESS_API_KEY 및 교육통계 오픈 API 스펙 확정 시 이 엔드포인트에서 실데이터로 교체,",
         'roadmap: "KESS_API_KEY 및 교육통계 오픈 API 스펙 확정 시 이 엔드포인트에서 실데이터로 교체",'),
        ("roadmap: SCHOOL_ALIMI_API_KEY(가칭) 또는 공식 연동 스펙 확보 시 실데이터로 교체,",
         'roadmap: "SCHOOL_ALIMI_API_KEY(가칭) 또는 공식 연동 스펙 확보 시 실데이터로 교체",'),
        ("roadmap: 학습된 모델 아티팩트(.pkl 등) 로딩으로 교체,",
         'roadmap: "학습된 모델 아티팩트(.pkl 등) 로딩으로 교체",'),
        ("roadmap: Stable-Baselines3 정책 학습 후 추론으로 교체,",
         'roadmap: "Stable-Baselines3 정책 학습 후 추론으로 교체",'),
        ("roadmap: shap 라이브러리 + 학습 모델로 실제 기여도 산출,",
         'roadmap: "shap 라이브러리 + 학습 모델로 실제 기여도 산출",'),
        ("마감 20분: 오늘 학습 회고 및 내일 계획,", '"마감 20분: 오늘 학습 회고 및 내일 계획",'),
        ("모두 무료로 이용 가능합니다.", '"모두 무료로 이용 가능합니다.",'),
    ]
    for a, b in reps:
        text = text.replace(a, b)
    return text


def fix_docstrings(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        if re.match(r"^(async )?def \w+\(", line) and line.rstrip().endswith(":"):
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            block: list[str] = []
            while j < len(lines):
                nxt = lines[j]
                if not nxt.strip():
                    break
                s = nxt.strip()
                if re.match(
                    r"^(return |if |for |while |#|\"|\'|@|async |api_key|key =|region |req\.|scores |"
                    r"school_name|subject_norm|level =|fmt =|matched|goal =|weaknesses|path_steps|"
                    r"result =|schedule =|text =|lines =|out =|params =|headers =|messages =|payload =|"
                    r"today =|cache_key|seed =|teachers =|school_type =|profile =|goal =|region =|"
                    r"linked_|class_|derived|xai_|twin_|causal_|risk_|schedule_|raw =|weights =|top =|"
                    r"parsed|sample_domain|context_hint|user_msg|model =|url =|form_data|file_bytes|"
                    r"weak_|total_weeks|triggers|recommendations|equity_|national_|avg =|gap =|"
                    r"resource_idx|infra_idx|offset =|grade =|schools =|rows =|simplified =|"
                    r"atpt =|school =|query|size|openai_ready|neis_ready|kess_stub|alimi_stub)",
                    s,
                ):
                    break
                if re.match(r"^[a-zA-Z_]+\s*=", s):
                    break
                if re.search(r"[가-힣]", s):
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


def close_fstrings(text: str) -> str:
    lines = []
    for line in text.splitlines():
        s = line.rstrip()
        if 'f"' in s and s.count('"') % 2 == 1:
            if s.endswith(","):
                s = s[:-1] + '",'
            elif s.endswith(")"):
                s = s[:-1] + '")'
            else:
                s += '"'
        lines.append(s)
    return "\n".join(lines) + "\n"


def fix_resource_dicts(text: str) -> str:
    """Fix partially quoted _PUBLIC_RESOURCES entries."""
    text = re.sub(
        r'\{"subject": (\w+), "title": ([^,]+), "type": (\w+), "cost": (\w+),',
        lambda m: f'{{"subject": "{m.group(1)}", "title": "{m.group(2).strip()}", "type": "{m.group(3)}", "cost": "{m.group(4)}",',
        text,
    )
    text = re.sub(
        r'"difficulty": ([^",}\n]+)\}',
        lambda m: f'"difficulty": "{m.group(1).strip()}"}}' if not m.group(1).strip().startswith('"') else m.group(0),
        text,
    )
    return text


def main() -> int:
    text = MAIN.read_text(encoding="utf-8")
    text = fix_ternary_strings(text)
    text = fix_misc(text)
    text = fix_fstrings(text)
    text = close_fstrings(text)
    text = fix_tuple_labels(text)
    text = fix_get_calls(text)
    text = quote_api_dict_keys(text)
    text = fix_docstrings(text)
    text = fix_resource_dicts(text)
    MAIN.write_text(text, encoding="utf-8")
    try:
        ast.parse(text)
        print("main.py OK")
        return 0
    except SyntaxError as e:
        print(f"line {e.lineno}: {e.msg}", file=sys.stderr)
        ls = text.splitlines()
        if e.lineno:
            for j in range(max(0, e.lineno - 2), min(len(ls), e.lineno + 2)):
                print(f"{j+1}: {ls[j][:120]}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
