#!/usr/bin/env python3
"""Fond de carte des départements de France métropolitaine (page Zones d'intervention).

Produit `_src/partials/carte-departements.json` : le cadre (viewBox) et un tracé SVG compact par département.
Les noms et les zones climatiques ne sont pas dans ce fichier : build.py les ajoute (DEPTS, zone_of).

Source des tracés : IGN, ADMIN EXPRESS COG 2018 (Licence Ouverte), version simplifiée publiée par France GeoJSON :
  https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements-version-simplifiee.geojson

Usage : python3 _src/carte.py departements-version-simplifiee.geojson [--tolerance 1000] [--iles 8]

Projection Lambert-93, puis simplification (Douglas-Peucker) frontière par frontière : une limite commune à deux
départements est simplifiée une seule fois, ce qui évite les trous et les chevauchements entre voisins.
"""
import argparse
import json
import math
import os

ICI = os.path.dirname(os.path.abspath(__file__))
SORTIE = os.path.join(ICI, 'partials', 'carte-departements.json')
LARGEUR = 1000   # largeur du cadre, en unités SVG (une unité ≈ 1,2 km)
MARGE = 4

# Lambert-93 (EPSG:2154) : conique conforme sécante, ellipsoïde GRS80
A, F = 6378137.0, 1 / 298.257222101
E = math.sqrt(2 * F - F * F)
PHI0, PHI1, PHI2, LAM0 = map(math.radians, (46.5, 49.0, 44.0, 3.0))
X0, Y0 = 700000.0, 6600000.0


def _m(p):
    return math.cos(p) / math.sqrt(1 - (E * math.sin(p)) ** 2)


def _t(p):
    return math.tan(math.pi / 4 - p / 2) / ((1 - E * math.sin(p)) / (1 + E * math.sin(p))) ** (E / 2)


N = (math.log(_m(PHI1)) - math.log(_m(PHI2))) / (math.log(_t(PHI1)) - math.log(_t(PHI2)))
FF = _m(PHI1) / (N * _t(PHI1) ** N)
RHO0 = A * FF * _t(PHI0) ** N


def lambert93(lon, lat):
    rho = A * FF * _t(math.radians(lat)) ** N
    theta = N * (math.radians(lon) - LAM0)
    return X0 + rho * math.sin(theta), Y0 + RHO0 - rho * math.cos(theta)


def aire(pts):
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))) / 2


def douglas_peucker(pts, tol, garder_milieu=False):
    """Simplifie une ligne ouverte en gardant ses extrémités (et, au besoin, son point le plus éloigné)."""
    if len(pts) <= 2:
        return pts
    garde = [False] * len(pts)
    garde[0] = garde[-1] = True
    pile = [(0, len(pts) - 1)]
    premier = True
    while pile:
        i, j = pile.pop()
        (x0, y0), (x1, y1) = pts[i], pts[j]
        dx, dy = x1 - x0, y1 - y0
        long2 = dx * dx + dy * dy
        dmax, kmax = -1.0, None
        for k in range(i + 1, j):
            px, py = pts[k]
            if long2 == 0:
                d = math.hypot(px - x0, py - y0)
            else:
                u = max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / long2))
                d = math.hypot(px - x0 - u * dx, py - y0 - u * dy)
            if d > dmax:
                dmax, kmax = d, k
        if kmax is not None and (dmax > tol or (premier and garder_milieu)):
            garde[kmax] = True
            pile += [(i, kmax), (kmax, j)]
        premier = False
    return [p for p, g in zip(pts, garde) if g]


def lire(source, iles_km2):
    """Anneaux par département, en sommets (lon, lat) exacts : les sommets communs servent à repérer les frontières."""
    data = json.load(open(source, encoding='utf-8'))
    deps = {}
    for f in data['features']:
        g = f['geometry']
        polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
        polys = [[[tuple(p) for p in ring[:-1]] for ring in poly] for poly in polys]
        deps[f['properties']['code']] = polys
    # segments de chaque anneau extérieur, pour reconnaître les îles (aucune frontière commune)
    seg = {}
    for code, polys in deps.items():
        for poly in polys:
            for ring in poly:
                for a, b in zip(ring, ring[1:] + ring[:1]):
                    seg.setdefault((min(a, b), max(a, b)), set()).add(code)
    for code, polys in deps.items():
        if len(polys) == 1:
            continue
        gardes = []
        for poly in polys:
            ext = poly[0]
            isolee = all(len(seg[(min(a, b), max(a, b))]) == 1 for a, b in zip(ext, ext[1:] + ext[:1]))
            km2 = aire([lambert93(*p) for p in ext]) / 1e6
            if not isolee or km2 >= iles_km2:
                gardes.append(poly)
        deps[code] = gardes
    return deps


def simplifier(deps, tol):
    anneaux = [(code, ring) for code, polys in deps.items() for poly in polys for ring in poly]
    # propriétaires de chaque segment (indices d'anneaux)
    seg = {}
    for r, (_, ring) in enumerate(anneaux):
        for a, b in zip(ring, ring[1:] + ring[:1]):
            seg.setdefault((min(a, b), max(a, b)), set()).add(r)
    proprio = lambda a, b: frozenset(seg[(min(a, b), max(a, b))])
    # nœuds : sommets où l'on passe d'une frontière à une autre
    noeuds = set()
    for _, ring in anneaux:
        n = len(ring)
        for i in range(n):
            if proprio(ring[i - 1], ring[i]) != proprio(ring[i], ring[(i + 1) % n]):
                noeuds.add(ring[i])
    for _, ring in anneaux:   # boucle sans nœud (île, enclave) : deux nœuds choisis de la même façon pour tous
        if not any(p in noeuds for p in ring):
            noeuds.update((min(ring), max(ring)))
    # découpage en arcs, de nœud à nœud
    decoupe = []
    for code, ring in anneaux:
        i0 = next(i for i, p in enumerate(ring) if p in noeuds)
        ring = ring[i0:] + ring[:i0]
        arcs, cur = [], [ring[0]]
        for p in ring[1:] + [ring[0]]:
            cur.append(p)
            if p in noeuds:
                arcs.append(tuple(cur))
                cur = [p]
        decoupe.append((code, arcs))
    canon = lambda arc: min(arc, arc[::-1])
    peu = {canon(a) for _, arcs in decoupe if len(arcs) <= 3 for a in arcs}   # petits anneaux : ne pas les écraser
    cache = {}
    for _, arcs in decoupe:
        for a in arcs:
            c = canon(a)
            if c not in cache:
                cache[c] = douglas_peucker([lambert93(*p) for p in c], tol, garder_milieu=c in peu)
    out = {}
    for code, arcs in decoupe:
        pts = []
        for a in arcs:
            c = canon(a)
            s = cache[c] if c == a else cache[c][::-1]
            pts += s[:-1]
        if len(pts) >= 3:
            out.setdefault(code, []).append(pts)
    return out


def trace(rings, conv):
    """Tracé SVG : premier point absolu, puis déplacements relatifs entiers ; un sous-tracé par anneau."""
    out = []
    for ring in rings:
        pts = []
        for x, y in ring:
            p = conv(x, y)
            if not pts or p != pts[-1]:
                pts.append(p)
        if len(pts) > 1 and pts[0] == pts[-1]:
            pts.pop()
        if len(pts) < 3:
            continue
        nums = ['M%d' % pts[0][0], str(pts[0][1]), 'l']
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            nums += [str(x1 - x0), str(y1 - y0)]
        s = ''
        for n in nums:
            # séparateur seulement si nécessaire (un signe moins ou une lettre suffit)
            s += n if (not s or n[0] in '-l' or s[-1] == 'l') else ' ' + n
        out.append(s + 'z')
    return ''.join(out)


PETITE_COURONNE = ('75', '92', '93', '94')
CADRE_ENCART = (MARGE, MARGE, 190, 150)   # encadré agrandi, dans la mer au nord-ouest : x, y, largeur, hauteur


def bornes(rings):
    xs = [x for rs in rings.values() for r in rs for x, _ in r]
    ys = [y for rs in rings.values() for r in rs for _, y in r]
    return min(xs), max(xs), min(ys), max(ys)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('source', help='GeoJSON des départements (WGS 84)')
    ap.add_argument('--tolerance', type=float, default=1200, help='tolérance de simplification, en mètres')
    ap.add_argument('--tolerance-encart', type=float, default=120, help='idem pour l’encadré de Paris, en mètres')
    ap.add_argument('--iles', type=float, default=8, help='surface minimale des îles conservées, en km²')
    a = ap.parse_args()
    deps = lire(a.source, a.iles)
    rings = simplifier(deps, a.tolerance)
    x0, x1, y0, y1 = bornes(rings)
    k = (LARGEUR - 2 * MARGE) / (x1 - x0)
    hauteur = round((y1 - y0) * k) + 2 * MARGE
    conv = lambda x, y: (round((x - x0) * k) + MARGE, round((y1 - y) * k) + MARGE)
    traces = {code: trace(rs, conv) for code, rs in sorted(rings.items())}

    # encadré : Paris et petite couronne, agrandis et moins simplifiés
    enc = simplifier({c: deps[c] for c in PETITE_COURONNE}, a.tolerance_encart)
    ex0, ex1, ey0, ey1 = bornes(enc)
    bx, by, bw, bh = CADRE_ENCART
    ke = min((bw - 28) / (ex1 - ex0), (bh - 28) / (ey1 - ey0))
    ox, oy = bx + (bw - (ex1 - ex0) * ke) / 2, by + (bh - (ey1 - ey0) * ke) / 2
    conv_e = lambda x, y: (round(ox + (x - ex0) * ke), round(oy + (ey1 - y) * ke))
    (rx0, ry0), (rx1, ry1) = conv(ex0, ey1), conv(ex1, ey0)
    encart = {'cadre': list(CADRE_ENCART), 'repere': [rx0 - 3, ry0 - 3, rx1 - rx0 + 6, ry1 - ry0 + 6],
              'paths': {code: trace(rs, conv_e) for code, rs in sorted(enc.items())}}

    json.dump({'viewBox': '0 0 %d %d' % (LARGEUR, hauteur),
               'source': 'IGN, ADMIN EXPRESS COG 2018, Licence Ouverte (via France GeoJSON)',
               'paths': traces, 'encart': encart},
              open(SORTIE, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('%d départements, %d points, %d octets → %s' % (
        len(traces), sum(len(r) for rs in rings.values() for r in rs), os.path.getsize(SORTIE), SORTIE))


if __name__ == '__main__':
    main()
