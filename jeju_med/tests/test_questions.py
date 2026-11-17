# -*- coding: utf-8 -*-
"""질문 20개 회귀 시험.
기대값은 엔진 코드를 쓰지 않고 CSV를 직접 세는 '독립 계산'으로 만든다.
실행: python tests/test_questions.py   (모두 통과하면 'ALL PASS')
"""
import csv, os, re, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from engine import Engine  # noqa

ROWS = list(csv.DictReader(open(os.path.join(HERE, "data", "hospitals_jeju_859_open_20261110.csv"), encoding="utf-8-sig")))
MED = {"의원", "병원", "종합병원", "요양병원(일반요양병원)", "요양병원(노인병원)", "정신병원", "보건소", "보건지소", "보건진료소"}
DENT = {"치과의원", "치과병원"}
FIX = {"정신과": "정신건강의학과", "흉부외과": "심장혈관흉부외과", "일반외과": "외과", "비뇨기과": "비뇨의학과"}
NOT = {"보건소", "보건지소", "조산원"}


def subs(r):
    out = set()
    for s in r["진료과목_원본"].split(","):
        s = re.sub(r"\(\d+개과\)", "", s.strip())
        s = FIX.get(s, s)
        if s and s not in NOT:
            out.add(s)
    return out


def indep(areas, subject, types=MED):
    fs = [r for r in ROWS if (r["시"], r["법정동_읍면"]) in areas and r["종류"] in types]
    return len(fs), sum(1 for r in fs if subject in subs(r)), sum(1 for r in fs if not subs(r))


J, S = "제주시", "서귀포시"
JU = {(J, d) for d in ["일도일동", "일도이동", "이도일동", "이도이동", "도남동", "삼도일동", "삼도이동", "용담일동", "용담이동", "용담삼동", "건입동",
                       "화북일동", "화북이동", "삼양일동", "삼양이동", "삼양삼동", "도련일동", "도련이동", "봉개동", "회천동", "용강동", "아라일동", "아라이동",
                       "월평동", "영평동", "오등동", "오라일동", "오라이동", "오라삼동", "연동", "노형동", "해안동", "외도일동", "외도이동", "내도동", "도평동",
                       "이호일동", "이호이동", "도두일동", "도두이동"]}
SU = {(S, d) for d in ["보목동", "동홍동", "서귀동", "토평동", "서홍동", "신효동", "하효동", "상효동", "법환동", "서호동", "호근동", "강정동", "도순동",
                       "영남동", "월평동", "대포동", "중문동", "하원동", "회수동", "상예동", "색달동", "하예동"]}

CASES = [
    # (질문, 기대 status, 기대 [(total, registered, unfilled), ...] 또는 None)
    ("한경면에 소아청소년과 있어?", "ok", [indep({(J, "한경면")}, "소아청소년과")]),
    ("한경 소아과", "ok", [indep({(J, "한경면")}, "소아청소년과")]),
    ("애월읍과 한림읍 정형외과 비교", "ok", [indep({(J, "애월읍")}, "정형외과"), indep({(J, "한림읍")}, "정형외과")]),
    ("우도 내과", "ok", [indep({(J, "우도면")}, "내과")]),
    ("추자면 소아청소년과", "ok", [indep({(J, "추자면")}, "소아청소년과")]),
    ("표선면 산부인과", "ok", [indep({(S, "표선면")}, "산부인과")]),
    ("서귀포시 동지역 비뇨기과", "ok", [indep(SU, "비뇨의학과")]),
    ("제주시 동지역 산부인과", "ok", [indep(JU, "산부인과")]),
    ("아라동 이비인후과", "ok", [indep({(J, d) for d in ["아라일동", "아라이동", "월평동", "영평동", "오등동"]}, "이비인후과")]),
    ("이도2동 안과", "ok", [indep({(J, "이도이동"), (J, "도남동")}, "안과")]),
    ("삼도1동 피부과", "confirm", None),  # 행안부 대조: 삼도일동은 삼도1동·삼도2동에 나뉨 → 되묻기
    ("삼도이동 피부과", "ok", [indep({(J, "삼도이동")}, "피부과")]),
    ("노형동 정신과", "ok", [indep({(J, "노형동")}, "정신건강의학과")]),
    ("대정읍 성산읍 남원읍 소아과 비교", "ok", [indep({(S, "대정읍")}, "소아청소년과"), indep({(S, "성산읍")}, "소아청소년과"), indep({(S, "남원읍")}, "소아청소년과")]),
    ("한림읍 소아치과", "ok", [indep({(J, "한림읍")}, "소아치과", DENT)]),
    ("중문동 내과", "confirm", None),
    ("정방동 산부인과", "confirm", None),
    ("산부인과 등록 시설이 없는 지역은?", "rank", None),
    ("배가 아파요 어디 가야 해요?", "out_of_scope", None),
    ("가장 가까운 소아과 알려줘", "out_of_scope", None),
    ("병원", "need_more", None),
    # 추가: 줄임말·조사
    ("노형 소아과", "ok", [indep({(J, "노형동")}, "소아청소년과")]),
    ("애월이랑 한림 소아과", "ok", [indep({(J, "애월읍")}, "소아청소년과"), indep({(J, "한림읍")}, "소아청소년과")]),
    ("화북 정형외과", "ok", [indep({(J, "화북일동"), (J, "화북이동")}, "정형외과")]),
]


def main():
    e = Engine()
    fails = 0
    for q, st, exp in CASES:
        r = e.ask(q)
        got_st = r.get("status")
        if st == "rank":
            ok = got_st == "ok" and r.get("intent") == "rank"
            if ok:  # 권역별 결과의 합 = 제주 전체 독립 계산
                allarea = {(si, a) for si, a in ((rw["시"], rw["법정동_읍면"]) for rw in ROWS)}
                t, g, u = indep(allarea, "산부인과")
                ok = (sum(x["total"] for x in r["results"]), sum(x["registered"] for x in r["results"]),
                      sum(x["unfilled"] for x in r["results"])) == (t, g, u) and len(r["results"]) == 14
            got = "rank"
        else:
            ok = got_st == st
            got = got_st
            if ok and exp is not None:
                got = [(x["total"], x["registered"], x["unfilled"]) for x in r["results"]]
                ok = got == exp
        fails += 0 if ok else 1
        print(("PASS" if ok else "FAIL"), q, "| 기대:", exp if exp else st, "| 결과:", got)
    # 이어 묻기: 직전 확정 조건을 이어받는지 (기대값은 독립 계산)
    ctx = e.ask("한경면에 소아청소년과 있어?")["conditions"]
    FOLLOW = [
        ("그럼 한림읍은?", [indep({(J, "한림읍")}, "소아청소년과")]),
        ("산부인과는?", [indep({(J, "한경면")}, "산부인과")]),
        ("대정읍도", [indep({(S, "대정읍")}, "소아청소년과")]),
    ]
    for q, exp in FOLLOW:
        r = e.ask(q, context=ctx)
        got = [(x["total"], x["registered"], x["unfilled"]) for x in r.get("results", [])]
        ok = r.get("status") == "ok" and got == exp and any(s["t"] == "이어 묻기" for s in r["steps"])
        fails += 0 if ok else 1
        print(("PASS" if ok else "FAIL"), "[이어 묻기]", q, "| 기대:", exp, "| 결과:", got)
    # 이어 묻기 신호가 없으면 이어받지 않는다
    r = e.ask("노형동", context=ctx)
    ok = r["conditions"]["subject"] is None
    fails += 0 if ok else 1
    print(("PASS" if ok else "FAIL"), "[이어 묻기 아님] 노형동 → 과목 이어받지 않음")
    # "…없는 지역은?"은 '은?'으로 끝나도 이어 묻기가 아니라 권역별 비교다
    r = e.ask("산부인과 등록 시설이 없는 지역은?", context=ctx)
    ok = r.get("intent") == "rank" and len(r["results"]) == 14
    fails += 0 if ok else 1
    print(("PASS" if ok else "FAIL"), "[이어 묻기 아님] 산부인과 등록 시설이 없는 지역은? → 권역별 비교")
    # 확인 질문에서 범위를 고르면 과목·시설 조건을 유지한 채 다시 센다
    r = e.ask("정방동 산부인과")
    opt = r["confirms"][0]["options"][0]
    c = dict(r["conditions"]); c["areas"] = [opt]; c["intent"] = "single"
    r2 = e.ask(conditions=c)
    got = [(x["total"], x["registered"], x["unfilled"]) for x in r2["results"]]
    exp = [indep({(S, "서귀동")}, "산부인과")]
    ok = got == exp and r2["conditions"]["subject"] == "산부인과" and \
        (opt["preview"]["total"], opt["preview"]["registered"], opt["preview"]["unfilled"]) == exp[0]
    fails += 0 if ok else 1
    print(("PASS" if ok else "FAIL"), "[확인 후 재집계] 정방동 산부인과 → 서귀동 전체 | 기대:", exp, "| 결과:", got)
    # 지도 좌표(보조): 집계 숫자를 바꾸지 않고, 제주 안에 있으며, 결과 수와 표시 수를 정직하게 알린다
    import engine as eng
    withc = sum(1 for f in e.facilities if f.lon is not None)
    inside = all(126.0 < f.lon < 127.1 and 33.0 < f.lat < 34.1 for f in e.facilities if f.lon is not None)
    r = e.ask("한경면에 소아청소년과 있어?")
    x = r["results"][0]
    shown_ok = x["map_total"] == x["registered"] + x["unfilled"] and \
        x["map_shown"] == sum(1 for y in x["registered_list"] + x["unfilled_list"] if y["경도"] is not None)
    ok = withc >= 0.9 * len(e.facilities) and inside and shown_ok and \
        not any(f.lon is not None for f in e.facilities if f.name in ("서광동보건진료소", "서광서보건진료소"))
    fails += 0 if ok else 1
    print(("PASS" if ok else "FAIL"), f"[지도] 표시 {withc}/{len(e.facilities)}곳, 모두 제주 안, 표시 수 일치, 지역 불일치 시설은 보류")
    saved = eng.COORD_FILE
    eng.COORD_FILE = saved + ".없음"
    e2 = eng.Engine()
    eng.COORD_FILE = saved
    r2 = e2.ask("한경면에 소아청소년과 있어?")
    ok = r2["results"][0]["registered"] == x["registered"] and r2["results"][0]["map_shown"] == 0
    fails += 0 if ok else 1
    print(("PASS" if ok else "FAIL"), "[지도] 좌표 파일이 없어도 같은 결과, 지도 표시 0곳")
    # 오타: 바로 세지 않고 후보로 되묻는다. 고르면 정상 결과
    for q, want in [("한깅면 소아과", "한경면 소아과"), ("노헝동 내과", "노형동 내과"), ("한경면 소아청소녀과", "한경면 소아청소년과")]:
        r = e.ask(q)
        ok = r.get("status") == "typo" and r["typo"]["options"][0]["question"] == want and "results" not in r
        if ok:
            r2 = e.ask(want)
            ok = r2.get("status") == "ok"
        fails += 0 if ok else 1
        print(("PASS" if ok else "FAIL"), f"[오타] {q} → 되묻기 후보 '{want}'")
    # 지역 없이 과목만: 제주 전체로 넘어가지 않고 지역을 묻는다
    r = e.ask("소아과")
    ok = r.get("status") == "need_more" and r.get("suggestions") and "results" not in r
    fails += 0 if ok else 1
    print(("PASS" if ok else "FAIL"), "[지역 없음] 소아과 → 지역을 묻고 권역별 보기는 버튼으로만")
    # 증상 + 지역: 증상으로 과목을 정하지 않고, 지역만 잡혔다고 전체 시설 수로 답하지도 않는다
    r = e.ask("애들 감기 걸리면 갈만한데 한경면에 있나?")
    ok = (r.get("status") == "need_more" and "results" not in r
          and [a["label"] for a in r["conditions"].get("areas", [])] == ["한경면"] and not r["conditions"].get("subject"))
    fails += 0 if ok else 1
    print(("PASS" if ok else "FAIL"), "[증상+지역] 감기+한경면 → 지역 유지, 과목을 묻고 세지 않음")
    # 증상만: 범위 밖 안내 (need_more가 아니므로 LLM에 넘기지 않아 과목을 짐작할 경로가 없음)
    r = e.ask("감기")
    ok = r.get("status") == "out_of_scope" and r.get("kind") == "symptom" and "results" not in r
    fails += 0 if ok else 1
    print(("PASS" if ok else "FAIL"), "[증상만] 감기 → 범위 밖 안내, AI에 넘기지 않음")
    # 과목도 시설 표현도 없으면 세지 않고, '병원'·'의료기관'처럼 전체 조회 의도가 분명하면 센다
    r = e.ask("한경면 맛집")
    r2 = e.ask("한경면 의료기관 몇 곳이야?")
    ok = (r.get("status") == "need_more" and "results" not in r
          and r2.get("status") == "ok" and r2["results"][0]["total"] == indep({(J, "한경면")}, "내과")[0])
    fails += 0 if ok else 1
    print(("PASS" if ok else "FAIL"), "[과목 없음] 한경면 맛집 → 세지 않음 / 한경면 의료기관 → 전체 시설 수")
    # 전화번호: 짝이 맞은 시설만, 나머지는 '확인 안 됨'
    allrows = [y for f in e.facilities for y in [f.to_row()]]
    has = sum(1 for y in allrows if y["기관 전화번호"] != "확인 안 됨")
    ok = 900 <= has <= 989 and all(re.match(r"^[0-9-]+$", y["기관 전화번호"]) for y in allrows if y["기관 전화번호"] != "확인 안 됨")
    fails += 0 if ok else 1
    print(("PASS" if ok else "FAIL"), f"[전화번호] {has}곳 표시, 형식 확인")
    print("ALL PASS" if fails == 0 else f"{fails} FAIL")
    return fails


if __name__ == "__main__":
    sys.exit(main())
