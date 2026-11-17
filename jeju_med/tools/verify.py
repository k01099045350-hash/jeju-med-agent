import json, sys, csv, collections
sys.path.insert(0, '/home/claude/app/jeju_med')
from engine import Engine, ADMIN_DONG, EUPMYEON
d = json.load(open('/home/claude/geo/dl/hjd_20250701.geojson', encoding='utf-8'))
fs = [f for f in d['features'] if f['properties'].get('sidonm', '').startswith('제주')]
def pip(x, y, ring):
    ins = False; n = len(ring); j = n - 1
    for i in range(n):
        xi, yi = ring[i]; xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-15) + xi: ins = not ins
        j = i
    return ins
def which(lon, lat):
    for f in fs:
        g = f['geometry']; mp = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
        for poly in mp:
            if pip(lon, lat, poly[0]) and not any(pip(lon, lat, h) for h in poly[1:]):
                return f['properties']['adm_nm'].split()[-1]
    return None
m = json.load(open('match_result.json', encoding='utf-8'))
e = Engine()
# engine facilities are in same order as raw 영업/정상 rows? verify by name
assert [f.name for f in e.facilities] == [x['name'] for x in m], 'order mismatch'
ok = bad = out = 0; bads = []
for f, x in zip(e.facilities, m):
    if x['lon'] is None: continue
    adm = which(x['lon'], x['lat'])
    if f.area.endswith(('읍', '면')):
        expect = {f.area}
    else:
        expect = {a for a, ms in ADMIN_DONG[f.si].items() if f.area in [s.rstrip('*') for s in ms]}
    if adm is None: out += 1; bads.append((f.name, f.area, '경계 밖(바다 등)', x['addr']))
    elif adm in expect: ok += 1
    else: bad += 1; bads.append((f.name, f.area, adm, x['addr']))
print('지역 일치', ok, '불일치', bad, '경계 밖', out)
for b in bads: print(' ', b)
