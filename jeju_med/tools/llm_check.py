# -*- coding: utf-8 -*-
"""AI 보조 연결 점검: 키가 읽히는지, 어떤 모델이 응답하는지 확인한다. 키 값은 출력하지 않는다.
실행: python\\python.exe jeju_med\\tools\\llm_check.py
"""
import json, os, sys, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import llm

print("키 제공자:", llm.provider_name())
if llm.provider() != "openai":
    print("OpenAI 키가 없어 점검을 끝냅니다. '평가용_API키.txt' 또는 환경변수를 확인하세요.")
    sys.exit(0)
key = llm._get("OPENAI_API_KEY")
print("키 형식: sk-로 시작", key.startswith("sk-"), "/ 길이", len(key))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine import Engine
E = Engine()
model = llm._get("JEJU_MED_OPENAI_MODEL") or "gpt-4o-mini"
print("모델:", model, "\n(Prompt 예시에 없는 질문으로 시험)")
for q in ["노형 쪽 아기 진료하는 데", "삼양이랑 화북 여성 진료 비교", "성읍 마을 내과 있나", "신창이랑 판포 소아과 비교", "배 아파요"]:
    before = E.ask(q).get("status")
    body = {"model": model, "max_tokens": 80, "temperature": 0, "messages": [{"role": "user", "content": llm.PROMPT + q}]}
    req = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=json.dumps(body).encode("utf-8"),
                                 headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            out = json.loads(r.read().decode("utf-8"))["choices"][0]["message"]["content"].strip()
        after = E.ask(out) if out != "모름" else {"status": "-"}
        res = ", ".join(f"{x['area']['label']} {x['registered']}곳" for x in after.get("results", []))
        print(f"- {q} | 규칙만: {before} | AI 고쳐 쓰기: {out!r} | 규칙 재해석: {after.get('status')} {res} (실제 화면은 사용자 확인 후 계산)")
    except urllib.error.HTTPError as e:
        print(f"- {q} | 실패 HTTP {e.code}")
    except Exception as e:
        print(f"- {q} | 실패 {type(e).__name__}")
input("\n엔터를 누르면 창이 닫힙니다...")
