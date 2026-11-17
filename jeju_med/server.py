# -*- coding: utf-8 -*-
"""로컬 웹 서버. 인터넷·API 키 없이 동작한다.

실행: python server.py  → 브라우저에서 http://127.0.0.1:8765 자동 열림
"""
import json
import os
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from engine import Engine, DATA_LABEL, GROUP_ORDER, COORD_LABEL  # noqa: E402
import llm  # noqa: E402

ENGINE = Engine()
STATIC = os.path.join(HERE, "static")
HOST, PORT = "127.0.0.1", int(os.environ.get("JEJU_MED_PORT", "8765"))


def handle_ask(body):
    q = (body.get("question") or "").strip()
    cond = body.get("conditions")
    if cond:
        return ENGINE.ask(conditions=cond)
    r = ENGINE.ask(q, context=body.get("context"))
    # 규칙으로 못 알아들었을 때만 LLM에 '질문 다시 쓰기'를 부탁한다 (숫자 계산에는 관여하지 않음)
    if r.get("status") == "need_more" and llm.available():
        rewritten = llm.rewrite_question(q)
        if rewritten and rewritten != q:
            r2 = ENGINE.ask(rewritten)
            if r2.get("status") in ("ok", "confirm"):
                # AI가 고쳐 쓴 조건은 바로 계산하지 않고 사용자 확인을 받는다 (오타 확인과 같은 방식)
                return {"status": "typo", "llm_used": True,
                        "typo": {"kind": "AI 해석", "typed": q, "options": [{"label": rewritten, "question": rewritten}]},
                        "message": "AI가 아래 조회 조건을 제안했습니다. 아직 집계하지 않았습니다. 맞으면 버튼을 누르고, "
                                   "틀리면 지역(읍·면·동)과 진료과목을 고쳐 다시 입력해 주세요.",
                        "steps": [{"t": "질문 이해", "d": "[해석 방식: AI 보조] 규칙으로 읽지 못한 질문을 AI가 "
                                   f"'{rewritten}'(으)로 고쳐 썼고, 규칙 엔진이 이 문장을 해석할 수 있음을 확인했습니다."},
                                  {"t": "사용자 확인", "d": "AI 해석은 틀릴 수 있어(예: 마을 이름의 소속 읍·면·동) 사용자가 승인하기 전에는 세지 않습니다."}]}
        r["llm_used"] = True
        r["message"] = (r.get("message") or "") + " (AI 보조도 확실한 읍·면·동과 진료과목을 찾지 못했습니다. 마을·관광지 이름은 소속 읍·면·동으로 바꿔 물어 주세요.)"
        _mark_mode(r, "해석 방식: 규칙 + AI 보조(해석 실패)")
        return r
    r["llm_used"] = False
    _mark_mode(r, "해석 방식: 규칙")
    return r


def _mark_mode(r, label):
    """판단 과정 첫 단계(질문 이해)에 이번 질문을 어떻게 해석했는지 붙인다."""
    steps = r.get("steps") or []
    if steps and steps[0].get("t") == "질문 이해":
        steps[0]["d"] = f"[{label}] " + steps[0]["d"]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # 콘솔을 조용하게

    def _send(self, code, data, ctype="application/json; charset=utf-8"):
        raw = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/meta":
            return self._send(200, {"data_label": DATA_LABEL, "facilities": len(ENGINE.facilities),
                                    "groups": GROUP_ORDER, "llm": llm.available(), "llm_name": llm.provider_name(), "coord_label": COORD_LABEL,
                                    "coords": sum(1 for f in ENGINE.facilities if f.lon is not None),
                                    **ENGINE.meta()})
        if path in ("/", "/index.html"):
            path = "/index.html"
        fp = os.path.normpath(os.path.join(STATIC, path.lstrip("/")))
        if not fp.startswith(STATIC) or not os.path.isfile(fp):
            return self._send(404, {"error": "not found"})
        ctype = {"html": "text/html; charset=utf-8", "js": "text/javascript; charset=utf-8",
                 "css": "text/css; charset=utf-8", "svg": "image/svg+xml",
                 "json": "application/json; charset=utf-8"}.get(fp.rsplit(".", 1)[-1],
                                                                              "application/octet-stream")
        with open(fp, "rb") as f:
            self._send(200, f.read(), ctype)

    def do_POST(self):
        if self.path != "/api/ask":
            return self._send(404, {"error": "not found"})
        try:
            n = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
            self._send(200, handle_ask(body))
        except Exception as e:  # 화면이 멈추지 않도록 오류도 JSON으로
            self._send(500, {"status": "error", "message": f"처리 중 오류가 났습니다: {e}"})


def main():
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://{HOST}:{PORT}/"
    print("=" * 56)
    print(" 제주 읍면동별 진료과목 분포 비교 Agent 실행 중")
    print(f" 브라우저 주소: {url}")
    print(f" 데이터: {DATA_LABEL}")
    print(f" LLM 보조: {'사용 (' + llm.provider_name() + ')' if llm.available() else '꺼짐 (키 없음 - 규칙 해석만 사용)'}")
    print(" 끝내려면 이 창을 닫거나 Ctrl+C")
    print("=" * 56)
    if "--no-browser" not in sys.argv:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
