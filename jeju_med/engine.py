# -*- coding: utf-8 -*-
"""제주 읍면동별 진료과목 분포 비교 Agent - 계산 엔진.

원칙
- 숫자는 전부 이 파일의 규칙과 코드가 계산한다. (LLM은 질문 해석 보조만)
- 같은 조건이면 언제나 같은 건수와 같은 근거 목록을 돌려준다.
- 데이터: 제주데이터허브 #859 병·의원 정보, 영업/정상 1,067건 정리본.
"""
import csv
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(HERE, "data", "hospitals_jeju_859_open_20261110.csv")
DATA_LABEL = "제주데이터허브 #859 병·의원 정보 (원본 갱신 2025-08-31, 영업/정상 기준)"
COORD_FILE = os.path.join(HERE, "data", "coords_hira_20260930.csv")
COORD_LABEL = ("지도 위치는 건강보험심사평가원 '전국 병의원 및 약국 현황'(2026-09-30 기준) 자료에서 "
               "기관명과 도로명주소가 일치한 시설에 한해 표시합니다.")

# ---------------------------------------------------------------- 시설 종류
TYPE_GROUPS = {
    "의과": ["의원", "병원", "종합병원", "요양병원(일반요양병원)", "요양병원(노인병원)", "정신병원"],
    "보건기관": ["보건소", "보건지소", "보건진료소"],
    "치과": ["치과의원", "치과병원"],
    "한방": ["한의원", "한방병원"],
    "기타": ["조산원"],
}
GROUP_ORDER = ["의과", "보건기관", "치과", "한방", "기타"]
DEFAULT_GROUPS = ["의과", "보건기관"]

# ---------------------------------------------------------------- 진료과목 정리
SUBJECT_FIX = {
    "정신과": "정신건강의학과",
    "흉부외과": "심장혈관흉부외과",
    "일반외과": "외과",
    "한방침구과": "침구과",
    "한방안.이비인후.피부과": "한방안·이비인후·피부과",
    "한방안이비인후피부과": "한방안·이비인후·피부과",
    "비뇨기과": "비뇨의학과",
}
NOT_SUBJECT = {"보건소", "보건지소", "조산원"}  # 과목이 아니라 시설 종류
DENTAL_SUBJECTS = {"치과", "치과교정과", "예방치과", "치과보철과", "소아치과", "치주과", "치과보존과",
                   "통합치의학과", "구강악안면외과", "구강내과", "영상치의학과", "구강병리과", "구강악안면방사선과"}


def is_korean_medicine(s):
    return s.startswith("한방") or s in ("침구과", "사상체질과")


def subject_group(s):
    if s in DENTAL_SUBJECTS:
        return "치과"
    if is_korean_medicine(s):
        return "한방"
    return "의과"


def normalize_subject(raw):
    s = re.sub(r"\(\d+개과\)", "", raw.strip())
    s = SUBJECT_FIX.get(s, s)
    return None if (not s or s in NOT_SUBJECT) else s


# 사용자가 쓰는 말 → 표준 과목명 (긴 말부터 찾음)
SUBJECT_ALIASES = {
    "소아청소년과": "소아청소년과", "소아과": "소아청소년과", "소청과": "소아청소년과",
    "산부인과": "산부인과", "부인과": "산부인과", "산과": "산부인과",
    "비뇨의학과": "비뇨의학과", "비뇨기과": "비뇨의학과", "비뇨과": "비뇨의학과",
    "정신건강의학과": "정신건강의학과", "신경정신과": "정신건강의학과", "정신과": "정신건강의학과",
    "이비인후과": "이비인후과", "이빈후과": "이비인후과",
    "정형외과": "정형외과", "신경외과": "신경외과", "성형외과": "성형외과",
    "심장혈관흉부외과": "심장혈관흉부외과", "흉부외과": "심장혈관흉부외과",
    "외과": "외과", "내과": "내과", "신경과": "신경과", "피부과": "피부과", "안과": "안과",
    "가정의학과": "가정의학과", "재활의학과": "재활의학과", "재활과": "재활의학과",
    "마취통증의학과": "마취통증의학과", "마취과": "마취통증의학과", "통증의학과": "마취통증의학과",
    "영상의학과": "영상의학과", "응급의학과": "응급의학과", "진단검사의학과": "진단검사의학과",
    "결핵과": "결핵과", "핵의학과": "핵의학과", "병리과": "병리과", "예방의학과": "예방의학과",
    "직업환경의학과": "직업환경의학과",
    "치과교정과": "치과교정과", "교정과": "치과교정과", "소아치과": "소아치과", "치주과": "치주과",
    "치과보철과": "치과보철과", "치과보존과": "치과보존과", "구강악안면외과": "구강악안면외과",
    "침구과": "침구과", "사상체질과": "사상체질과", "한방소아과": "한방소아과",
    "한방부인과": "한방부인과", "한방내과": "한방내과", "한방재활의학과": "한방재활의학과",
    "한방신경정신과": "한방신경정신과",
}
# 과목 없이 종류만 말하는 경우
TYPE_WORDS = [("치과", "치과"), ("한의원", "한방"), ("한방", "한방"), ("보건진료소", "보건기관"),
              ("보건소", "보건기관"), ("보건지소", "보건기관")]

# ---------------------------------------------------------------- 지역
# 행정동 → 법정동 (* = 여러 행정동에 걸친 법정동)
# 출처: 행정안전부 '행정기관(행정동) 및 관할구역(법정동) 코드' KIKmix.20261026 (2026-10-26 기준)으로 31개 행정동 전부 대조함
ADMIN_DONG = {
    "제주시": {
        "일도1동": ["일도일동"], "일도2동": ["일도이동"], "이도1동": ["이도일동"], "이도2동": ["이도이동", "도남동"],
        "삼도1동": ["삼도일동*"], "삼도2동": ["삼도일동*", "삼도이동"], "용담1동": ["용담일동"], "용담2동": ["용담이동", "용담삼동"],
        "건입동": ["건입동"], "화북동": ["화북일동", "화북이동"],
        "삼양동": ["삼양일동", "삼양이동", "삼양삼동", "도련일동", "도련이동"],
        "봉개동": ["봉개동", "회천동", "용강동"], "아라동": ["아라일동", "아라이동", "월평동", "영평동", "오등동"],
        "오라동": ["오라일동", "오라이동", "오라삼동"], "연동": ["연동"], "노형동": ["노형동", "해안동"],
        "외도동": ["외도일동", "외도이동", "내도동", "도평동"], "이호동": ["이호일동", "이호이동"],
        "도두동": ["도두일동", "도두이동"],
    },
    "서귀포시": {
        "송산동": ["보목동", "동홍동*", "서귀동*", "토평동*"], "정방동": ["서귀동*"], "중앙동": ["서귀동*"],
        "천지동": ["서귀동*", "서홍동*"], "효돈동": ["신효동", "하효동"], "영천동": ["상효동", "토평동*"],
        "동홍동": ["동홍동*"], "서홍동": ["서홍동*"], "대륜동": ["법환동", "서호동", "호근동"],
        "대천동": ["강정동", "도순동", "영남동", "월평동"], "중문동": ["대포동", "중문동", "하원동", "회수동"],
        "예래동": ["상예동", "색달동", "하예동"],
    },
}
EUPMYEON = {
    "제주시": ["한림읍", "애월읍", "구좌읍", "조천읍", "한경면", "추자면", "우도면"],
    "서귀포시": ["대정읍", "남원읍", "성산읍", "안덕면", "표선면"],
}
NUM_TO_KO = {"1": "일", "2": "이", "3": "삼"}


def legal_dongs(si):
    out = []
    for members in ADMIN_DONG[si].values():
        for m in members:
            m = m.rstrip("*")
            if m not in out:
                out.append(m)
    return out


def legal_to_admin(si, legal):
    return [a for a, ms in ADMIN_DONG[si].items() if legal in [m.rstrip("*") for m in ms]]


def is_split_legal(si, legal):
    return any(m == legal + "*" for ms in ADMIN_DONG[si].values() for m in ms)


# ---------------------------------------------------------------- 데이터
class Facility:
    __slots__ = ("name", "type", "group", "si", "area", "subjects_raw", "subjects", "addr", "opened", "lon", "lat", "map_note", "phone")

    def to_row(self):
        return {"시설명": self.name, "종류": self.type, "시": self.si, "법정동·읍면": self.area,
                "등록 진료과목": ", ".join(self.subjects_raw) if self.subjects_raw else "(과목 정보 없음)",
                "주소": f"{self.si} {self.addr}", "개설일": self.opened,
                "경도": self.lon, "위도": self.lat, "지도": self.map_note,
                "기관 전화번호": self.phone or "확인 안 됨"}


def type_group(t):
    for g, ts in TYPE_GROUPS.items():
        if t in ts:
            return g
    return "기타"


def load(path=DATA_FILE):
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            x = Facility()
            x.name, x.type, x.si, x.area = r["시설명"], r["종류"], r["시"], r["법정동_읍면"]
            x.group = type_group(x.type)
            x.subjects_raw = [s.strip() for s in r["진료과목_원본"].split(",") if s.strip()]
            x.subjects = {s for s in (normalize_subject(v) for v in x.subjects_raw) if s}
            x.addr, x.opened = r["주소"], r["개설일"]
            x.lon = x.lat = None
            x.map_note = "위치 미확인"
            x.phone = ""
            rows.append(x)
    # 지도 표시용 좌표(보조). 집계에는 쓰지 않는다. 파일이 없어도 동작한다.
    if os.path.exists(COORD_FILE):
        with open(COORD_FILE, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                i = int(r["순번"])
                if i < len(rows) and rows[i].name == r["시설명"]:
                    rows[i].phone = (r.get("전화번호") or "").strip()
                    st = r.get("상태", "")
                    if st.startswith("표시") and r["경도"]:
                        rows[i].lon, rows[i].lat = float(r["경도"]), float(r["위도"])
                        rows[i].map_note = ""
                    elif st.startswith("보류"):
                        rows[i].map_note = "지도 표시 보류: 자료 간 주소 지역과 좌표 지역이 다름"
    return rows


def map_regions(members):
    """집계 범위와 지도 경계(행정동·읍면)가 정확히 같을 때만 경계 이름 목록을 돌려준다. 다르면 None."""
    mem = set(members)
    out = []
    for si in ("제주시", "서귀포시"):
        for e_ in EUPMYEON[si]:
            if (si, e_) in mem:
                out.append((si, e_))
        for adm, ms in ADMIN_DONG[si].items():
            legal = {(si, m.rstrip("*")) for m in ms}
            if legal <= mem:
                out.append((si, adm))
    covered = set()
    for si, nm in out:
        if nm in EUPMYEON[si]:
            covered.add((si, nm))
        else:
            covered |= {(si, m.rstrip("*")) for m in ADMIN_DONG[si][nm]}
    if covered != mem:
        return None
    # 여러 행정동에 걸친 법정동은 그 법정동을 가진 행정동이 모두 들어와야 경계가 같다
    for si in ("제주시", "서귀포시"):
        for adm, ms in ADMIN_DONG[si].items():
            for m in ms:
                if m.endswith("*") and (si, m[:-1]) in mem and (si, adm) not in out:
                    return None
    return [f"{si} {nm}" for si, nm in out]


# ---------------------------------------------------------------- 지역 단위(집계 대상)
class Area:
    """집계 단위. members = (시, 법정동/읍면) 목록."""

    def __init__(self, label, members, kind, note=""):
        self.label, self.members, self.kind, self.note = label, members, kind, note

    def contains(self, f):
        return (f.si, f.area) in self.members

    def to_dict(self):
        return {"label": self.label, "kind": self.kind, "note": self.note,
                "members": [f"{si} {a}" for si, a in self.members],
                "map_regions": map_regions(self.members)}


def area_catalog():
    """질문에서 찾을 이름 → 후보 해석 목록."""
    cat = {}

    def add(name, item):
        cat.setdefault(name, []).append(item)

    for si in ("제주시", "서귀포시"):
        for e in EUPMYEON[si]:
            a = Area(e, [(si, e)], "읍면", "")
            add(e, a)
            add(e[:-1], a)  # 한경, 애월 ...
        for d in legal_dongs(si):
            add(d, ("legal", si, d))
            m = re.match(r"^(.+?)(일|이|삼)동$", d)
            if m:
                num = {"일": "1", "이": "2", "삼": "3"}[m.group(2)]
                digit = m.group(1) + num + "동"
                if digit not in ADMIN_DONG[si]:  # '이도2동'처럼 숫자 표기는 행정동 이름이므로 행정동으로 해석
                    add(digit, ("legal", si, d))
        for adm in ADMIN_DONG[si]:
            add(adm, ("admin", si, adm))
        # '노형', '아라', '중문'처럼 '동'을 뺀 줄임말 (두 글자 이상, 숫자 없는 이름만)
        for nm in list(ADMIN_DONG[si]) + legal_dongs(si):
            stem = nm[:-1]
            if len(stem) >= 2 and not re.search(r"(일|이|삼|[0-9])$", stem):
                for it in (cat.get(nm) or []):
                    if it not in cat.get(stem, []):
                        add(stem, it)
        add(si, ("city", si))
        add(si + " 동지역", ("cityurban", si))
        add(si + "동지역", ("cityurban", si))
    add("서귀포", ("city", "서귀포시"))
    for w in ("제주 전체", "제주도 전체", "제주도", "도 전체", "전체"):
        add(w, ("all",))
    return cat


CATALOG = area_catalog()


def resolve_area_token(name, facilities):
    """이름 하나를 실제 집계 단위로. 애매하면 확인 질문용 선택지를 돌려준다.
    반환: (Area 또는 None, 선택지 목록 또는 None)"""
    items = CATALOG.get(name, [])
    legal = [i for i in items if isinstance(i, tuple) and i[0] == "legal"]
    admin = [i for i in items if isinstance(i, tuple) and i[0] == "admin"]
    other = [i for i in items if not (isinstance(i, tuple) and i[0] in ("legal", "admin"))]

    def count(members):
        return sum(1 for f in facilities if (f.si, f.area) in members)

    if other:
        it = other[0]
        if isinstance(it, Area):
            return it, None
        if it[0] == "city":
            si = it[1]
            mem = [(si, e) for e in EUPMYEON[si]] + [(si, d) for d in legal_dongs(si)]
            return Area(si + " 전체", mem, "시", ""), None
        if it[0] == "cityurban":
            si = it[1]
            return Area(si + " 동지역", [(si, d) for d in legal_dongs(si)], "동지역", "읍·면을 뺀 동 지역 전체"), None
        if it[0] == "all":
            mem = [(si, x) for si in ("제주시", "서귀포시") for x in EUPMYEON[si] + legal_dongs(si)]
            return Area("제주 전체", mem, "전체", ""), None

    legal_area = None
    if legal:
        _, si, d = legal[0]
        note = ""
        adm = legal_to_admin(si, d)
        if is_split_legal(si, d):
            note = f"{d}은(는) 행정동 {', '.join(adm)}에 나뉘어 있어 법정동 전체 기준으로 셉니다."
        legal_area = Area(d, [(si, d)], "법정동", note)

    admin_area, admin_split = None, False
    if admin:
        _, si, a = admin[0]
        ms = ADMIN_DONG[si][a]
        admin_split = any(m.endswith("*") for m in ms)
        mem = [(si, m.rstrip("*")) for m in ms]
        label = a if not legal else f"{a}(행정동)"
        note = "행정동 " + a + " = 법정동 " + ", ".join(m.rstrip("*") for m in ms)
        admin_area = Area(label, mem, "행정동", note)

    if legal_area and admin_area:
        # 같은 이름이 법정동이기도 하고 행정동이기도 함 (예: 노형동, 중문동)
        contained = set(legal_area.members) <= set(admin_area.members)
        if contained and count(legal_area.members) == count(admin_area.members):
            legal_area.note = (legal_area.note + " " if legal_area.note else "") + \
                f"#859 자료 기준으로 행정동 {admin[0][2]}(={', '.join(m for _, m in admin_area.members)}) 범위를 적용해도 포함되는 시설은 같습니다."
            return legal_area, None
        legal_area.label = f"{legal_area.label}(법정동)"
        return None, [legal_area, admin_area]
    if legal_area:
        return legal_area, None
    if admin_area:
        if admin_split:
            # 정방동처럼 주소만으로는 단독 집계가 안 되는 행정동
            si = admin[0][1]
            whole = Area(" · ".join(m for _, m in admin_area.members) + " 전체", admin_area.members, "법정동묶음",
                         f"행정동 {admin[0][2]} 단독 집계는 주소로 확인할 수 없어, 걸쳐 있는 법정동 전체로 셉니다.")
            return None, [whole]
        return admin_area, None
    return None, None


# ---------------------------------------------------------------- 질문 해석(규칙)
OUT_OF_SCOPE = [
    (r"(응급|위급|119|급해|쓰러|숨이)", "emergency"),
    (r"(아파|아프|열이|기침|증상|어지러|토하|다쳤|감기|독감|콧물|몸살|두통|복통|배탈|설사|발열|고열|가려워|가렵|치통|생리통|코로나)", "symptom"),
    (r"(가까운|가장 가까|근처|주변에|길찾|가는 길|몇 분)", "nearest"),
    (r"(지금 문|영업시간|진료시간|야간|주말|예약)", "hours"),
]
OUT_MSG = {
    "emergency": "응급 상황이면 바로 119에 전화하세요. 이 도구는 지역별 '등록 진료과목' 통계만 보여 주며 응급 진료 가능 여부는 알 수 없습니다.",
    "symptom": "증상에 맞는 진료과를 추천하는 기능은 없습니다. 진료과를 정해서 물어보시면 지역별 등록 시설을 보여 드립니다.",
    "nearest": "가장 가까운 병원 찾기, 거리 계산, 길 안내는 하지 않습니다. 지역 이름을 말씀하시면 그 지역의 등록 시설 수와 목록을 지도와 함께 보여 드립니다.",
    "hours": "진료시간·예약 정보는 이 데이터에 없습니다. 지역과 과목으로 물어보시면 근거 목록에 기관 전화번호(건강보험심사평가원 2026-09-30 기준)를 함께 보여 드리니, 방문 전 전화로 확인하세요.",
}
RANK_WORDS = r"(어디|어느|없는|적은|많은|부족|순위|비교해|분포|현황)"


def find_subject(q):
    for alias in sorted(SUBJECT_ALIASES, key=len, reverse=True):
        if alias in q:
            return SUBJECT_ALIASES[alias], alias
    return None, None


def find_areas(q):
    found, used = [], []
    for name in sorted(CATALOG, key=len, reverse=True):
        if len(name) < 2:
            continue
        idx = q.find(name)
        while idx >= 0:
            span = (idx, idx + len(name))
            if not any(s < span[1] and span[0] < e for s, e in used):
                # 짧은 이름(한경, 애월 등)이 다른 낱말 일부일 때 오인 방지: 앞 글자가 한글이면 건너뜀
                prev = q[idx - 1] if idx > 0 else " "
                if len(name) <= 2 and re.match(r"[가-힣]", prev):
                    pass
                else:
                    used.append(span)
                    found.append((idx, name))
            idx = q.find(name, idx + 1)
    found.sort()
    out = []
    for _, n in found:
        if n not in out:
            out.append(n)
    return out


def edit_distance(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


PARTICLES = ("에서", "이랑", "랑", "에는", "에", "은", "는", "이", "가", "도", "의", "을", "를", "와")


def typo_candidates(token, names):
    """편집거리 1을 기본으로, 5글자 이상이면 거리 2까지(최단 후보가 하나일 때만). 최대 3개."""
    scored = sorted((edit_distance(token, n), n) for n in names if abs(len(n) - len(token)) <= 2)
    if not scored:
        return []
    best = scored[0][0]
    cands = [n for d, n in scored if d == best]
    if best == 1:
        return cands[:3]
    if best == 2 and len(token) >= 5 and len(cands) == 1:
        return cands
    return []


def find_typo(q0, q_wo, subject, areas):
    """찾지 못한 지역·과목이 오타로 보이면 바로잡은 질문 후보를 돌려준다."""
    tokens = re.findall(r"[가-힣0-9]+", q_wo)
    if not areas:
        area_names = [n for n in CATALOG if len(n) >= 3 and re.search(r"(읍|면|동)$", n)]
        for t in tokens:
            core = t
            for p in PARTICLES:
                if core.endswith(p) and re.search(r"(읍|면|동)$", core[:-len(p)]):
                    core = core[:-len(p)]
                    break
            if len(core) >= 3 and re.search(r"(읍|면|동)$", core) and core not in CATALOG:
                c = typo_candidates(core, area_names)
                if c:
                    return {"kind": "지역", "typed": core, "options": [{"label": n, "question": q0.replace(core, n, 1)} for n in c]}
    if not subject:
        subj_names = sorted(set(SUBJECT_ALIASES) | set(SUBJECT_ALIASES.values()))
        for t in tokens:
            core = t
            for p in PARTICLES:
                if core.endswith(p) and core[:-len(p)].endswith("과"):
                    core = core[:-len(p)]
                    break
            if len(core) >= 3 and core.endswith("과") and core not in SUBJECT_ALIASES:
                c = typo_candidates(core, subj_names)
                if c:
                    return {"kind": "진료과목", "typed": core,
                            "options": [{"label": SUBJECT_ALIASES.get(n, n), "question": q0.replace(core, n, 1)} for n in c]}
    return None


def parse(q):
    """질문 → 조건. 숫자 계산은 하지 않는다."""
    q0 = q.strip()
    subject, alias = find_subject(q0)
    q_wo = q0.replace(alias, " ") if alias else q0
    symptom = False
    for pat, kind in OUT_OF_SCOPE:
        if re.search(pat, q_wo):
            if kind == "symptom" and not subject and find_areas(q_wo):
                # 증상 + 지역: 거절하지 않고 지역은 유지한 채 진료과목을 묻는다 (증상으로 과목을 정하지 않음)
                symptom = True
                break
            return {"status": "out_of_scope", "kind": kind, "message": OUT_MSG[kind]}
    groups = None
    if subject:
        g = subject_group(subject)
        groups = [g] if g != "의과" else list(DEFAULT_GROUPS)
    else:
        for w, g in TYPE_WORDS:
            if w in q_wo:
                groups = [g]
                break
    hospital_only = bool(re.search(r"병원(만|급)", q0))
    areas = find_areas(q_wo)
    intent = "single"
    if len(areas) >= 2:
        intent = "compare"
    elif re.search(RANK_WORDS, q0) and (not areas or areas[0] in ("제주시", "서귀포시", "서귀포", "제주 전체",
                                                                  "제주도 전체", "제주도", "도 전체", "전체")):
        intent = "rank"
    elif not areas:
        # 지역을 못 찾았다고 제주 전체로 넘어가지 않는다 (비교 의도가 드러날 때만 권역별 비교)
        intent = "need_area" if subject else "unknown"
    order = "desc" if re.search(r"(있는|많은)", q0) and not re.search(r"(없는|적은|부족)", q0) else "asc"
    followup = bool(re.search(FOLLOWUP, q0))
    if intent != "rank":
        ty = find_typo(q0, q_wo, subject, areas)
        if ty:
            return {"status": "typo", "typo": ty, "subject": subject, "areas": areas,
                    "message": f"'{ty['typed']}'을(를) 찾지 못했습니다. 혹시 아래 {ty['kind']}을 말씀하신 건가요? 고르기 전에는 세지 않습니다."}
    # 과목도, 시설 종류·전체 조회 표현도 없으면 지역만 잡혔다고 전체 시설 수로 답하지 않는다
    needs_subject = symptom or (not subject and groups is None and not re.search(GENERIC_WORDS, q0))
    return {"status": "parsed", "intent": intent, "order": order, "subject": subject, "alias": alias,
            "needs_subject": needs_subject, "symptom": symptom,
            "areas": areas, "groups": groups or list(DEFAULT_GROUPS), "hospital_only": hospital_only,
            "groups_explicit": groups is not None, "followup": followup,
            "rank_explicit": bool(re.search(RANK_WORDS, q0))}


# 과목 없이 "시설 전체"를 묻는 것으로 볼 수 있는 표현
GENERIC_WORDS = r"(병원|의원|시설|의료|보건|진료소|조산원|기관|병·의원|병의원|전체|모든)"

# 이어 묻기 신호: "그럼 한림읍은?", "산부인과는?", "성산읍도"
FOLLOWUP = r"(^\s*(그럼|그러면|그렇다면|그리고|이번엔|이번에는|같은 조건))|((은|는|도)\s*(요)?\s*\??\s*$)"


def apply_context(p, ctx):
    """직전에 확정된 조건(ctx)에서 이번 질문에 빠진 것을 이어받는다. 이어받은 내용을 문장으로 돌려준다."""
    if not ctx or p.get("status") != "parsed" or not p.get("followup"):
        return None
    got = []
    if not p["subject"] and not p["groups_explicit"] and not p.get("symptom") and ctx.get("subject") and p["areas"]:
        p["subject"] = ctx["subject"]
        p["groups"] = list(ctx.get("groups") or DEFAULT_GROUPS)
        p["hospital_only"] = bool(ctx.get("hospital_only"))
        got.append(f"과목 '{p['subject']}'와 시설 범위")
    elif p["subject"] and not p["areas"] and not p.get("rank_explicit") and ctx.get("intent") != "rank" and ctx.get("areas"):
        p["areas"] = list(ctx["areas"])
        p["intent"] = "compare" if len(p["areas"]) > 1 else "single"
        got.append("지역 '" + ", ".join(a["label"] if isinstance(a, dict) else a for a in p["areas"]) + "'")
    if not got:
        return None
    if p["intent"] == "unknown":
        p["intent"] = "single"
    return "직전 질문에서 " + ", ".join(got) + "을(를) 이어받았습니다. 조건 칸에서 바꿀 수 있습니다."


# ---------------------------------------------------------------- 집계
HOSPITAL_LEVEL = {"병원", "종합병원", "요양병원(일반요양병원)", "요양병원(노인병원)", "정신병원", "한방병원", "치과병원"}


class Engine:
    def __init__(self, path=DATA_FILE):
        self.facilities = load(path)

    def meta(self):
        from collections import Counter
        c = Counter(s for f in self.facilities for s in f.subjects)
        subjects = [{"name": s, "group": subject_group(s), "count": n} for s, n in c.most_common()]
        areas = []
        for si in ("제주시", "서귀포시"):
            for e_ in EUPMYEON[si]:
                areas.append({"label": e_, "si": si, "kind": "읍면", "members": [f"{si} {e_}"], "note": ""})
            areas.append({"label": si + " 동지역", "si": si, "kind": "동지역",
                          "members": [f"{si} {d}" for d in legal_dongs(si)], "note": "읍·면을 뺀 동 지역 전체"})
            for d in legal_dongs(si):
                note = ""
                if is_split_legal(si, d):
                    note = f"{d}은(는) 행정동 {', '.join(legal_to_admin(si, d))}에 나뉘어 있어 법정동 전체 기준으로 셉니다."
                areas.append({"label": d, "si": si, "kind": "법정동", "members": [f"{si} {d}"], "note": note})
        return {"subjects": subjects, "areas": areas}

    # 범위 안 시설
    def in_scope(self, groups, hospital_only=False):
        fs = [f for f in self.facilities if f.group in groups]
        if hospital_only:
            fs = [f for f in fs if f.type in HOSPITAL_LEVEL]
        return fs

    def count_area(self, area, subject, groups, hospital_only=False):
        fs = [f for f in self.in_scope(groups, hospital_only) if area.contains(f)]
        if subject:
            reg = [f for f in fs if subject in f.subjects]
            unf = [f for f in fs if not f.subjects]
        else:
            reg, unf = fs, []
        key = lambda f: (0 if f.type in HOSPITAL_LEVEL else 1, f.type, f.name)
        reg, unf = sorted(reg, key=key), sorted(unf, key=key)
        shown = [f for f in reg + unf if f.lon is not None]
        return {"area": area.to_dict(), "map_shown": len(shown), "map_total": len(reg) + len(unf), "total": len(fs), "registered": len(reg), "unfilled": len(unf),
                "registered_list": [f.to_row() for f in reg], "unfilled_list": [f.to_row() for f in unf]}

    def rank_units(self, unit):
        if unit == "legal":
            units = []
            for si in ("제주시", "서귀포시"):
                for e in EUPMYEON[si]:
                    units.append(Area(e, [(si, e)], "읍면"))
                for d in legal_dongs(si):
                    units.append(Area(d, [(si, d)], "법정동"))
            return units
        units = []
        for si in ("제주시", "서귀포시"):
            for e in EUPMYEON[si]:
                units.append(Area(e, [(si, e)], "읍면"))
            units.append(Area(si + " 동지역", [(si, d) for d in legal_dongs(si)], "동지역"))
        return units

    def ask(self, question=None, conditions=None, context=None):
        carried = None
        if conditions is None and context:
            p = parse(question or "")
            carried = apply_context(p, context)
            if carried:
                r = self._ask(None, p)
            else:
                r = self._ask(question, None)
        else:
            r = self._ask(question, conditions)
        try:
            r["steps"] = self.explain(r, from_question=conditions is None)
            if carried:
                r["steps"].insert(1, {"t": "이어 묻기", "d": carried})
                r.setdefault("notes", []).insert(0, carried)
        except Exception:
            r["steps"] = []
        return r

    def explain(self, r, from_question=True):
        """Agent가 내린 판단을 사람이 읽을 수 있는 단계로 정리한다 (계산 결과를 바꾸지 않음)."""
        st = r.get("status")
        if st == "typo":
            ty = r.get("typo", {})
            return [{"t": "질문 이해", "d": f"{ty.get('kind', '')} 이름 '{ty.get('typed', '')}'을(를) 목록에서 찾지 못했습니다."},
                    {"t": "오타 점검", "d": "글자 한두 개만 다른 이름을 찾아 후보로 제시했습니다: " +
                     ", ".join(o["label"] for o in ty.get("options", [])) + ". 사용자가 고르기 전에는 세지 않습니다."}]
        if st == "out_of_scope":
            return [{"t": "질문 이해", "d": "이 도구가 다루지 않는 요청(증상·응급·가까운 곳·진료시간)으로 판단했습니다."},
                    {"t": "대응", "d": "계산하지 않고 할 수 있는 일을 안내했습니다."}]
        c = r.get("conditions") or {}
        subj, groups, hosp = c.get("subject"), c.get("groups") or [], c.get("hospital_only")
        steps = []
        kind = {"single": "한 지역 조회", "compare": "지역 비교", "rank": "제주 권역별 비교"}.get(r.get("intent") or c.get("intent"), "조회")
        areas = c.get("areas") or []
        alab = ", ".join(a["label"] if isinstance(a, dict) else a for a in areas)
        if r.get("confirms"):
            alab = ", ".join([alab] if alab else [] + [cf["name"] + "(범위 확인 중)" for cf in r["confirms"]])
        alab = alab or ("제주 전체" if kind == "제주 권역별 비교" else "-")
        s1 = f"질문 유형: {kind} · 지역: {alab} · 과목: {subj or '지정 없음'}"
        if c.get("alias") and c["alias"] != subj:
            s1 += f" ('{c['alias']}' → 표준명 '{subj}')"
        steps.append({"t": "질문 이해" if from_question else "조건 적용", "d": s1})
        if subj:
            g = subject_group(subj)
            why = {"의과": "의과 과목이라 의원·병원과 보건기관을 기본 범위로", "치과": "치과 과목이라 치과 시설만",
                   "한방": "한방 과목이라 한의원·한방병원만"}[g]
            steps.append({"t": "집계 범위 결정", "d": f"{why} 셉니다 → {self.scope_label(groups, hosp)}"})
        else:
            steps.append({"t": "집계 범위 결정", "d": f"과목 지정이 없어 범위 안 시설 수를 셉니다 → {self.scope_label(groups, hosp)}"})
        if st == "confirm":
            steps.append({"t": "지역 범위 확인", "d": "같은 이름이 서로 다른 범위(법정동/행정동)로 해석되어, 바로 세지 않고 범위별 미리보기 건수와 함께 확인을 요청했습니다."})
            return steps
        if st != "ok":
            steps.append({"t": "추가 정보 필요", "d": r.get("message", "")})
            return steps
        area_notes = [a.get("note") for a in areas if isinstance(a, dict) and a.get("note")]
        if area_notes:
            steps.append({"t": "지역 범위 확인", "d": " / ".join(area_notes)})
        res = r.get("results") or []
        if r.get("intent") == "rank":
            z = [x for x in res if subj and x["registered"] == 0]
            steps.append({"t": "집계", "d": f"{len(res)}개 권역을 같은 기준으로 셌습니다. 등록 확인 0곳 권역 {len(z)}곳."})
            if z:
                steps.append({"t": "0곳 점검", "d": "0곳 권역마다 과목 정보가 없는 시설 수를 함께 표시해, '없음'으로 단정하지 않도록 했습니다."})
            return steps
        tot = sum(x["total"] for x in res)
        steps.append({"t": "집계", "d": " / ".join(f"{x['area']['label']}: 범위 안 {x['total']}곳 중 " +
                                                    (f"등록 확인 {x['registered']}곳" if subj else f"{x['total']}곳") for x in res)
                      + " (#859 원본 행 기준)"})
        if subj:
            zero = [x for x in res if x["registered"] == 0]
            if zero:
                d = []
                for x in zero:
                    d.append(f"{x['area']['label']}은(는) 등록 확인 0곳이지만 과목 정보 없는 시설 {x['unfilled']}곳이 있어 "
                             + ("'없음'이 아니라 '등록 확인 0곳'으로 표시했습니다." if x["unfilled"] else "등록 확인 0곳으로 표시했습니다."))
                d.append("제주 전체 권역별 비교를 다음 단계로 제안했습니다.")
                steps.append({"t": "0곳 점검", "d": " ".join(d)})
            elif any(x["unfilled"] for x in res):
                steps.append({"t": "누락 점검", "d": "과목 정보 없는 시설이 있어 결과 카드와 근거 목록에 따로 표시했습니다."})
        return steps

    def _ask(self, question=None, conditions=None):
        """question 또는 확정된 conditions를 받아 결과를 돌려준다."""
        if conditions is None:
            p = parse(question or "")
            if p["status"] in ("out_of_scope", "typo"):
                return p
            conditions = p
        c = conditions
        subject, groups = c.get("subject"), c.get("groups") or list(DEFAULT_GROUPS)
        hospital_only = bool(c.get("hospital_only"))
        intent = c.get("intent", "single")
        cond_out = {"subject": subject, "alias": c.get("alias"), "groups": groups, "hospital_only": hospital_only,
                    "intent": intent, "group_options": GROUP_ORDER}
        notes = []
        if c.get("alias") and c["alias"] != subject:
            notes.append(f"'{c['alias']}'을(를) 표준 과목명 '{subject}'(으)로 바꿔 찾았습니다.")

        if intent == "unknown":
            return {"status": "need_more", "conditions": cond_out,
                    "message": "어느 지역의 어떤 진료과목을 볼지 알려 주세요. 예: '한경면에 소아청소년과 있어?'"}
        if intent == "need_area":
            return {"status": "need_more", "conditions": cond_out,
                    "message": f"어느 지역의 {subject}를 볼까요? 지역 이름을 함께 적어 주세요. 예: '애월읍 {subject}'",
                    "suggestions": [{"label": f"제주 전체에서 {subject} 권역별로 보기", "conditions":
                                     {"intent": "rank", "subject": subject, "groups": groups, "hospital_only": hospital_only}}]}

        if intent == "rank":
            unit = c.get("unit", "eupmyeon_urban")
            if not subject:
                return {"status": "need_more", "conditions": cond_out,
                        "message": "어떤 진료과목의 분포를 볼지 알려 주세요. 예: '소아청소년과 등록 시설이 적은 지역은?'"}
            si_filter = None
            for a in c.get("areas", []):
                if a in ("제주시",):
                    si_filter = "제주시"
                if a in ("서귀포시", "서귀포"):
                    si_filter = "서귀포시"
            units = self.rank_units(unit)
            if si_filter:
                units = [u for u in units if u.members[0][0] == si_filter]
            res = [self.count_area(u, subject, groups, hospital_only) for u in units]
            desc = bool(c.get("order") == "desc")
            if desc:
                res.sort(key=lambda r: (-r["registered"], r["area"]["label"]))
            else:
                res.sort(key=lambda r: (r["registered"], -r["unfilled"], r["area"]["label"]))
            cond_out["order"] = "desc" if desc else "asc"
            cond_out["unit"] = unit
            cond_out["areas"] = [si_filter] if si_filter else []
            zero = [r["area"]["label"] for r in res if r["registered"] == 0]
            sents = []
            unit_txt = "읍·면 12곳과 동지역 2곳" if unit != "legal" else "읍·면과 법정동"
            if si_filter:
                unit_txt = si_filter + (" 읍·면과 동지역" if unit != "legal" else " 읍·면과 법정동")
            if zero:
                sents.append(f"{subject} 등록 시설이 한 곳도 확인되지 않은 지역은 {', '.join(zero)}입니다({unit_txt} 기준).")
            else:
                sents.append(f"{unit_txt} 모두에 {subject} 등록 시설이 1곳 이상 있습니다.")
            if desc:
                top = [r for r in res if r["registered"] > 0][:3]
                if top:
                    sents.append("등록 시설이 많은 지역은 " + ", ".join(f"{r['area']['label']} {r['registered']}곳" for r in top) + "입니다.")
            else:
                low = [r for r in res if r["registered"] > 0][:3]
                if low:
                    sents.append("등록 시설이 적은 지역은 " + ", ".join(f"{r['area']['label']} {r['registered']}곳" for r in low) + "입니다.")
            uz = [r for r in res if r["registered"] == 0 and r["unfilled"] > 0]
            if uz:
                tot = sum(r["unfilled"] for r in uz)
                sents.append(f"다만 등록 0곳인 지역에도 진료과목 정보가 없는 시설이 모두 {tot}곳 있어(지역별 표 참고), "
                             "실제로는 해당 진료를 할 수도 있습니다.")
            return {"status": "ok", "intent": "rank", "conditions": cond_out, "results": res,
                    "sentences": sents, "notes": notes + self.scope_notes(groups, hospital_only), "data_label": DATA_LABEL}

        # single / compare
        areas, confirms = [], []
        for name in c.get("areas", []):
            if isinstance(name, dict):  # 확인 질문에서 고른 단위
                areas.append(Area(name["label"], [tuple(m.split(" ", 1)) for m in name["members"]], name.get("kind", ""),
                                  name.get("note", "")))
                continue
            a, opts = resolve_area_token(name, self.facilities)
            if a:
                areas.append(a)
            elif opts:
                confirms.append({"name": name, "options": [o.to_dict() for o in opts]})
        if confirms:
            preview = []
            for cf in confirms:
                for o in cf["options"]:
                    ar = Area(o["label"], [tuple(m.split(" ", 1)) for m in o["members"]], o["kind"], o["note"])
                    r = self.count_area(ar, subject, groups, hospital_only)
                    o["preview"] = {"total": r["total"], "registered": r["registered"], "unfilled": r["unfilled"]}
            cond_out["areas"] = [a.to_dict() for a in areas]
            return {"status": "confirm", "conditions": cond_out, "confirms": confirms,
                    "message": "지역 이름이 여러 범위로 해석됩니다. 어느 범위로 셀지 골라 주세요."}
        if not areas:
            return {"status": "need_more", "conditions": cond_out,
                    "message": "지역 이름을 찾지 못했습니다. 읍·면이나 동 이름으로 물어봐 주세요. 예: '애월읍 정형외과'"}
        if not subject and c.get("needs_subject"):
            cond_out["areas"] = [a.to_dict() for a in areas]
            labs = ", ".join(a.label for a in areas)
            msg = (f"{labs}을(를) 찾으시는 것으로 이해했습니다. " +
                   ("이 서비스는 증상으로 진료과를 정하지 않습니다. " if c.get("symptom") else "어떤 진료과목을 볼지 알 수 없어 아직 세지 않았습니다. ") +
                   "찾으려는 진료과목을 입력하거나, 위 조건 칸에서 진료과목을 골라 [이 조건으로 다시 계산]을 눌러 주세요. 응급 상황이면 119.")
            return {"status": "need_more", "conditions": cond_out, "message": msg,
                    "suggestions": [{"label": f"{labs} 의료시설 전체 수 보기", "conditions":
                                     {"intent": intent, "subject": None, "groups": groups, "hospital_only": hospital_only,
                                      "areas": [a.to_dict() for a in areas]}}]}
        res = [self.count_area(a, subject, groups, hospital_only) for a in areas]
        cond_out["areas"] = [a.to_dict() for a in areas]
        for a in areas:
            if a.note:
                notes.append(a.note)
        sents = self.sentences(res, subject, groups, hospital_only)
        sugg = []
        if subject and any(r["registered"] == 0 for r in res):
            sugg.append({"label": f"제주 전체에서 {subject} 분포 보기", "conditions":
                         {"intent": "rank", "subject": subject, "groups": groups, "hospital_only": hospital_only}})
        return {"status": "ok", "intent": "compare" if len(res) > 1 else "single", "conditions": cond_out,
                "results": res, "sentences": sents, "notes": notes + self.scope_notes(groups, hospital_only),
                "suggestions": sugg, "data_label": DATA_LABEL}

    @staticmethod
    def scope_label(groups, hospital_only):
        s = "·".join(g if g != "의과" else "의원·병원" for g in GROUP_ORDER if g in groups)
        return s + (" (병원급만)" if hospital_only else "")

    def scope_notes(self, groups, hospital_only):
        return [f"집계 범위: {self.scope_label(groups, hospital_only)}. 진료과목은 기관이 등록(표방)한 과목이며, "
                "전문의 여부나 실제 진료 가능 여부와 다를 수 있습니다. 방문 전 기관에 확인하세요.",
                "'과목 정보 없음'은 진료과목 칸이 비어 있거나 과목명이 아닌 값(예: '보건지소')만 적힌 시설입니다. 원문은 근거 목록에 그대로 보여 줍니다."]

    def sentences(self, res, subject, groups, hospital_only):
        scope = self.scope_label(groups, hospital_only)
        out = []
        if subject:
            if len(res) == 1:
                r = res[0]
                lab = r["area"]["label"]
                if r["registered"] > 0:
                    names = ", ".join(x["시설명"] for x in r["registered_list"][:5])
                    more = f" 등 {r['registered']}곳" if r["registered"] > 5 else ""
                    out.append(f"{lab}에서 {subject}를 진료과목으로 등록한 시설은 {r['registered']}곳입니다({names}{more}).")
                else:
                    out.append(f"{lab}에서 {subject}를 진료과목으로 등록한 시설은 확인되지 않았습니다(등록 확인 0곳).")
                if r["unfilled"]:
                    out.append(f"같은 범위({scope}) 시설 {r['total']}곳 중 {r['unfilled']}곳은 진료과목 정보가 없어, "
                               "실제로는 해당 진료를 할 수도 있습니다.")
            else:
                parts = ", ".join(f"{r['area']['label']} {r['registered']}곳" for r in res)
                out.append(f"{subject} 등록 시설은 {parts}입니다({scope} 기준).")
                mx = max(res, key=lambda r: r["registered"])
                mn = min(res, key=lambda r: r["registered"])
                if mx["registered"] != mn["registered"]:
                    out.append(f"{mx['area']['label']}이(가) {mn['area']['label']}보다 {mx['registered'] - mn['registered']}곳 많습니다.")
                uf = [r for r in res if r["unfilled"]]
                if uf:
                    out.append("과목 정보가 없는 시설: " + ", ".join(f"{r['area']['label']} {r['unfilled']}곳" for r in uf) + ".")
        else:
            parts = ", ".join(f"{r['area']['label']} {r['total']}곳" for r in res)
            out.append(f"{scope} 시설 수는 {parts}입니다.")
        return out


if __name__ == "__main__":
    import json
    import sys
    e = Engine()
    q = " ".join(sys.argv[1:]) or "한경면에 소아청소년과 있어?"
    r = e.ask(q)
    for k in ("registered_list", "unfilled_list"):
        for x in r.get("results", []):
            x[k] = [y["시설명"] for y in x[k]]
    print(json.dumps(r, ensure_ascii=False, indent=1))
