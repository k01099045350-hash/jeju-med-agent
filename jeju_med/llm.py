# -*- coding: utf-8 -*-
"""선택 기능: 외부 LLM으로 '알아듣기 어려운 질문'을 표준 질문 문장으로 다시 쓴다.

- 키를 읽는 곳 (먼저 찾은 것을 사용):
    1) 환경변수 ANTHROPIC_API_KEY 또는 OPENAI_API_KEY
    2) 압축을 푼 폴더 맨 위의 '평가용_API키.txt' (대회 규정상 심사용 키만 이 파일로 제출 가능)
  프로그램은 키를 별도로 저장하거나 화면·로그에 출력하지 않는다.
- 비용을 막기 위해 한 번 실행하는 동안 호출 횟수(기본 200회)와 질문 길이(200자)를 제한한다.
- LLM은 숫자를 만들지 않는다. 다시 쓴 문장은 다시 규칙 엔진이 해석하고 계산한다.
- 키가 없거나, 인터넷이 안 되거나, 응답이 이상하면 조용히 None을 돌려준다.
"""
import json
import os
import urllib.request
import urllib.error

TIMEOUT = 12
MAX_CALLS = int(os.environ.get("JEJU_MED_LLM_MAX_CALLS", "200"))
MAX_LEN = 200
_calls = 0
KEY_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "평가용_API키.txt")


def _file_keys():
    """'평가용_API키.txt'에서 이름=값 줄을 읽는다. 비어 있거나 없으면 빈 dict."""
    out = {}
    try:
        with open(KEY_FILE, encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "JEJU_MED_OPENAI_MODEL", "JEJU_MED_ANTHROPIC_MODEL") and v:
                    out[k] = v
    except OSError:
        pass
    return out


def _get(name):
    return os.environ.get(name) or _file_keys().get(name)

PROMPT = (
    "너는 제주 병·의원 통계 도구의 질문 정리 담당이다. 사용자의 말을 아래 형식의 한국어 한 문장으로만 바꿔라.\n"
    "형식(셋 중 하나): '<지역> <표준 진료과목명>' / '<지역1>과 <지역2> <표준 진료과목명> 비교' / '<표준 진료과목명> 없는 지역'(사용자가 지역 간 비교를 원할 때만).\n"
    "지역은 사용자가 말한 지역이 아래 목록의 이름(또는 '노형'→노형동, '애월'→애월읍처럼 목록 이름의 줄임말)일 때만 쓴다. "
    "목록에 없는 마을·리 이름, 관광지, 옛 지명은 어느 읍·면·동에 속하는지 추측하지 말고 '모름'을 출력한다.\n"
    "지역 목록: 한림읍 애월읍 구좌읍 조천읍 한경면 추자면 우도면 대정읍 남원읍 성산읍 안덕면 표선면 "
    "일도1동 일도2동 이도1동 이도2동 삼도1동 삼도2동 용담1동 용담2동 건입동 화북동 삼양동 봉개동 아라동 오라동 연동 노형동 외도동 이호동 도두동 "
    "송산동 정방동 중앙동 천지동 효돈동 영천동 동홍동 서홍동 대륜동 대천동 중문동 예래동 제주시 동지역 서귀포시 동지역\n"
    "과목은 표준명(예: 소아청소년과, 산부인과, 정형외과, 내과, 안과, 이비인후과, 피부과, 정신건강의학과, 치과)만 쓴다. "
    "'여성 병원'→산부인과, '아이 병원'→소아청소년과처럼 진료과를 직접 가리키는 말만 바꾼다.\n"
    "증상·병 이름(감기, 복통 등)으로 진료과를 추측하지 말고 '모름'을 출력한다. 지역이나 과목을 알 수 없어도 '모름'. 설명, 따옴표, 숫자 추측은 금지.\n"
    "예) 연동에 여성 병원 있어? → 연동 산부인과 / 애월이랑 한림 피부과 견줘 줘 → 애월읍과 한림읍 피부과 비교 / 모슬포 산부인과 → 모름 / 배 아파 → 모름\n"
    "사용자 말: "
)


def provider():
    if _get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if _get("OPENAI_API_KEY"):
        return "openai"
    return None


def available():
    return provider() is not None


def provider_name():
    return {"anthropic": "Anthropic Claude", "openai": "OpenAI"}.get(provider(), "없음")


def _post(url, headers, payload):
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def rewrite_question(q):
    global _calls
    p = provider()
    if not p or not q or len(q) > MAX_LEN or _calls >= MAX_CALLS:
        return None
    _calls += 1
    try:
        if p == "anthropic":
            model = _get("JEJU_MED_ANTHROPIC_MODEL") or "claude-haiku-5-5"
            data = _post("https://api.anthropic.com/v1/messages",
                         {"x-api-key": _get("ANTHROPIC_API_KEY"), "anthropic-version": "2023-06-01",
                          "content-type": "application/json"},
                         {"model": model, "max_tokens": 80, "messages": [{"role": "user", "content": PROMPT + q}]})
            text = "".join(b.get("text", "") for b in data.get("content", []))
        else:
            model = _get("JEJU_MED_OPENAI_MODEL") or "gpt-4o-mini"
            data = _post("https://api.openai.com/v1/chat/completions",
                         {"Authorization": "Bearer " + _get("OPENAI_API_KEY"), "Content-Type": "application/json"},
                         {"model": model, "max_tokens": 80, "temperature": 0, "messages": [{"role": "user", "content": PROMPT + q}]})
            text = data["choices"][0]["message"]["content"]
        text = (text or "").strip().splitlines()[0].strip(" '\"") if (text or "").strip() else ""
        if not text or text == "모름" or len(text) > 60:
            _log(f"AI 응답을 쓰지 않음('{text[:20]}') → 규칙 해석 유지")
            return None
        _log(f"AI가 질문을 '{text}'(으)로 고쳐 씀")
        return text
    except urllib.error.HTTPError as e:
        code = ""
        try:
            code = json.loads(e.read().decode("utf-8")).get("error", {}).get("code") or ""
        except Exception:
            pass
        _log(f"AI 호출 실패: HTTP {e.code} {code} → 규칙 해석 유지")
        return None
    except Exception as e:
        _log(f"AI 호출 실패: {type(e).__name__} → 규칙 해석 유지")
        return None


def _log(msg):
    """실행 창에 한 줄 남긴다(키는 출력하지 않음)."""
    try:
        print("[LLM 보조] " + msg, flush=True)
    except Exception:
        pass
