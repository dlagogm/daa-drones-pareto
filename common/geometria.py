"""Primitivas de geometría computacional (tema 7): orientación, intersección de segmentos,
punto en polígono, visibilidad entre puntos y envolvente convexa."""
from math import hypot

EPS = 1e-9


def orientacion(p, q, r):
    """> 0 si p→q→r gira a la izquierda, < 0 a la derecha, 0 si son colineales (producto vectorial)."""
    return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])


def _en_segmento(p, q, r):
    """r está sobre el segmento pq (supuesto colineal)."""
    return (min(p[0], q[0]) - EPS <= r[0] <= max(p[0], q[0]) + EPS and
            min(p[1], q[1]) - EPS <= r[1] <= max(p[1], q[1]) + EPS)


def segmentos_se_cortan(p1, p2, q1, q2):
    """Test clásico de intersección de segmentos con orientaciones, incluidos los casos colineales.
    O(1)."""
    d1 = orientacion(q1, q2, p1)
    d2 = orientacion(q1, q2, p2)
    d3 = orientacion(p1, p2, q1)
    d4 = orientacion(p1, p2, q2)
    if ((d1 > EPS and d2 < -EPS) or (d1 < -EPS and d2 > EPS)) and \
       ((d3 > EPS and d4 < -EPS) or (d3 < -EPS and d4 > EPS)):
        return True
    if abs(d1) <= EPS and _en_segmento(q1, q2, p1): return True
    if abs(d2) <= EPS and _en_segmento(q1, q2, p2): return True
    if abs(d3) <= EPS and _en_segmento(p1, p2, q1): return True
    if abs(d4) <= EPS and _en_segmento(p1, p2, q2): return True
    return False


def punto_en_poligono(pt, poligono):
    """Ray casting: cuenta cuántas aristas cruza un rayo horizontal hacia la derecha. O(k)."""
    x, y = pt
    dentro = False
    k = len(poligono)
    for i in range(k):
        (x1, y1), (x2, y2) = poligono[i], poligono[(i + 1) % k]
        if (y1 > y) != (y2 > y):
            xc = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if xc > x:
                dentro = not dentro
    return dentro


def segmento_corta_poligono(a, b, poligono):
    """True si el segmento ab entra en el polígono: corta alguna arista o su punto medio está dentro
    (cubre el caso de un segmento que cruza el polígono pasando justo por dos vértices)."""
    k = len(poligono)
    for i in range(k):
        if segmentos_se_cortan(a, b, poligono[i], poligono[(i + 1) % k]):
            return True
    medio = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    return punto_en_poligono(medio, poligono)


def visible(a, b, poligonos):
    """a y b se ven si el segmento ab no atraviesa ninguna zona no-fly. O(Σ k_i)."""
    return not any(segmento_corta_poligono(a, b, pol) for pol in poligonos)


def distancia(a, b):
    return hypot(b[0] - a[0], b[1] - a[1])


def envolvente_convexa(puntos):
    """Cadena monótona de Andrew, O(n log n). Devuelve los índices en sentido antihorario."""
    idx = sorted(range(len(puntos)), key=lambda i: (puntos[i][0], puntos[i][1]))
    if len(idx) <= 2:
        return idx

    def construir(orden):
        cadena = []
        for i in orden:
            while len(cadena) >= 2 and orientacion(puntos[cadena[-2]], puntos[cadena[-1]], puntos[i]) <= 0:
                cadena.pop()
            cadena.append(i)
        return cadena

    inferior, superior = construir(idx), construir(reversed(idx))
    return inferior[:-1] + superior[:-1]
