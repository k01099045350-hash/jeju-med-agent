import json, math, sys
src, out = sys.argv[1], sys.argv[2]
d = json.load(open(src, encoding='utf-8'))
fs = [f for f in d['features'] if f['properties'].get('sidonm', '').startswith('제주')]
LAT0 = 33.4
K = math.cos(math.radians(LAT0))
def proj(lon, lat): return (lon * K, -lat)
def dp(pts, eps):
    if len(pts) < 3: return pts
    keep = [False] * len(pts); keep[0] = keep[-1] = True
    st = [(0, len(pts) - 1)]
    while st:
        a, b = st.pop()
        ax, ay = pts[a]; bx, by = pts[b]; dx, dy = bx - ax, by - ay; L = math.hypot(dx, dy) or 1e-12
        m, mi = 0, -1
        for i in range(a + 1, b):
            px, py = pts[i]; dist = (abs(dy * (px - ax) - dx * (py - ay)) / L) if L > 1e-9 else math.hypot(px - ax, py - ay)
            if dist > m: m, mi = dist, i
        if m > eps:
            keep[mi] = True; st.append((a, mi)); st.append((mi, b))
    return [p for p, k in zip(pts, keep) if k]
polys = []
for f in fs:
    g = f['geometry']; rings = []
    mp = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
    for poly in mp:
        ring = [proj(x, y) for x, y in poly[0]]
        rings.append(ring)
    polys.append((f['properties'], rings))
xs = [p[0] for _, rs in polys for r in rs for p in r]; ys = [p[1] for _, rs in polys for r in rs for p in r]
minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
W = 1000.0; S = W / (maxx - minx); H = (maxy - miny) * S
EPS = 0.6  # px
areas = []
for props, rings in polys:
    parts = []
    for r in rings:
        pts = [((x - minx) * S, (y - miny) * S) for x, y in r]
        # 아주 작은 섬 조각은 생략
        bw = max(p[0] for p in pts) - min(p[0] for p in pts); bh = max(p[1] for p in pts) - min(p[1] for p in pts)
        if bw < 3 and bh < 3 and len(rings) > 1: continue
        s = dp(pts, EPS)
        if len(s) < 4: continue
        parts.append('M' + 'L'.join(f'{x:.1f},{y:.1f}' for x, y in s) + 'Z')
    nm = props['adm_nm'].split()
    areas.append({'si': nm[1], 'name': nm[2], 'd': ''.join(parts)})
meta = {'source': '통계청 SGIS 행정동 경계 기반 vuski/admdongkor ver20250701 (공공누리 1유형, CC BY 4.0)',
        'w': W, 'h': round(H, 1), 'k': K, 'minx': minx, 'miny': miny, 's': S, 'areas': areas}
json.dump(meta, open(out, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print(len(areas), 'areas', 'H', round(H, 1), 'bytes', len(json.dumps(meta, ensure_ascii=False)))
