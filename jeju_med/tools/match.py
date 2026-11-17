# -*- coding: utf-8 -*-
"""#859(집계 기준) 시설에 심평원 자료의 좌표를 붙인다. 이름+도로명주소(도로명+건물번호)가 양쪽에서 유일하게 일치할 때만."""
import csv, re, sys, json, collections
U = '/mnt/user-data/uploads/제주 AI Agent 개발 챌린지/01_data/raw_public/'
RAW859 = U + 'jeju_hospital_859_20261110.csv'
HIRA = U + 'hira_20260930/병원정보_제주_20260930.csv'

def nname(s):
    s = re.sub(r'\(.*?\)', '', s or '')
    s = re.sub(r'(의료법인|사회복지법인|재단법인|의료재단|사단법인|\(재\)|\(사\))', '', s)
    s = re.sub(r'[^가-힣A-Za-z0-9]', '', s)
    return s

def roadkey(addr):
    """'제주특별자치도 제주시 서광로 175, 3층 (용담일동)' → ('서광로', '175')"""
    a = re.sub(r'\(.*?\)', ' ', addr or '')
    a = a.replace('제주특별자치도', ' ')
    a = re.sub(r'(제주시|서귀포시)', ' ', a)
    a = a.split(',')[0]
    m = re.search(r'([가-힣A-Za-z0-9]+(?:로|길|대로))\s*(\d+(?:-\d+)?)', a)
    if not m: return None
    num = re.sub(r'-0$', '', m.group(2))
    return (m.group(1), num)

raw = [r for r in csv.DictReader(open(RAW859, encoding='utf-8-sig')) if r['openStatus'] == '영업/정상']
hira = list(csv.DictReader(open(HIRA, encoding='utf-8-sig')))
print('859 영업/정상', len(raw), '심평원 제주', len(hira))

hidx = collections.defaultdict(list)
for h in hira:
    k = roadkey(h['주소'])
    hidx[(nname(h['요양기관명']), k)].append(h)

out, stats = [], collections.Counter()
for r in raw:
    key = (nname(r['companyName']), roadkey(r['addressDoro']))
    cands = hidx.get(key, []) if key[1] else []
    res = {'name': r['companyName'], 'type': r['bizSmallType'], 'addr': r['addressDoro'] or r['addressJibun'], 'lon': None, 'lat': None, 'how': ''}
    if key[1] is None:
        stats['도로명주소 없음'] += 1; res['how'] = 'no_road'
    elif len(cands) == 1:
        h = cands[0]
        try:
            lon, lat = float(h['좌표(X)']), float(h['좌표(Y)'])
        except ValueError:
            lon = lat = None
        if lon and 126.0 < lon < 127.1 and 33.0 < lat < 34.1:
            res.update(lon=lon, lat=lat, how='name+road'); stats['일치'] += 1
        else:
            res['how'] = 'bad_coord'; stats['좌표 이상'] += 1
    elif len(cands) > 1:
        stats['후보 여러 곳'] += 1; res['how'] = 'multi'
    else:
        stats['일치 없음'] += 1; res['how'] = 'none'
    out.append(res)
print(dict(stats), '일치율', round(stats['일치'] / len(raw) * 100, 1), '%')
# 같은 이름+주소인 #859 중복 행 확인
dup = collections.Counter((nname(r['companyName']), roadkey(r['addressDoro'])) for r in raw)
print('859 안 중복 키', sum(1 for k, v in dup.items() if v > 1 and k[1]))
json.dump(out, open('match_result.json', 'w', encoding='utf-8'), ensure_ascii=False)
bytype = collections.defaultdict(collections.Counter)
for o in out: bytype[o['type']][o['how']] += 1
for t, c in sorted(bytype.items(), key=lambda x: -sum(x[1].values())): print(t, dict(c))
