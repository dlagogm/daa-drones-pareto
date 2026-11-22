"""Dominancia de Pareto, archivo de no dominadas, distancia de crowding (NSGA-II), hipervolumen y
diversidad. Todos los objetivos se minimizan."""
from itertools import combinations
from math import sqrt


def domina(a, b):
    """a domina a b si no es peor en ningún objetivo y es mejor en al menos uno."""
    return all(x <= y for x, y in zip(a, b)) and any(x < y for x, y in zip(a, b))


def domina_o_igual(a, b):
    return all(x <= y for x, y in zip(a, b))


def no_dominadas(soluciones):
    """soluciones: lista de (objetivos, orden). Devuelve las no dominadas sin vectores repetidos."""
    res = []
    vistos = set()
    for obj, sol in sorted(soluciones, key=lambda s: s[0]):
        clave = tuple(round(x, 9) for x in obj)
        if clave in vistos:
            continue
        if not any(domina_o_igual(o, obj) for o, _ in res):
            res = [(o, s) for o, s in res if not domina(obj, o)]
            res.append((obj, sol)); vistos.add(clave)
    return res


def insertar_en_archivo(archivo, obj, sol):
    """Inserta (obj, sol) si nadie del archivo lo domina o iguala. Devuelve True si entra."""
    if any(domina_o_igual(o, obj) for o, _ in archivo):
        return False
    archivo[:] = [(o, s) for o, s in archivo if not domina(obj, o)]
    archivo.append((obj, list(sol)))
    return True


def crowding(objetivos):
    """Distancia de crowding de NSGA-II: suma, en cada objetivo, del hueco entre los vecinos."""
    n = len(objetivos)
    dist = [0.0] * n
    if n <= 2:
        return [float('inf')] * n
    for m in range(len(objetivos[0])):
        orden = sorted(range(n), key=lambda i: objetivos[i][m])
        lo, hi = objetivos[orden[0]][m], objetivos[orden[-1]][m]
        dist[orden[0]] = dist[orden[-1]] = float('inf')
        if hi == lo:
            continue
        for k in range(1, n - 1):
            dist[orden[k]] += (objetivos[orden[k + 1]][m] - objetivos[orden[k - 1]][m]) / (hi - lo)
    return dist


def normalizar(puntos, ideal, nadir):
    res = []
    for p in puntos:
        res.append(tuple((x - lo) / (hi - lo) if hi > lo else 0.0 for x, lo, hi in zip(p, ideal, nadir)))
    return res


def hipervolumen_2d(puntos, ref):
    pts = sorted(p for p in puntos if p[0] < ref[0] and p[1] < ref[1])
    hv, mejor_y = 0.0, ref[1]
    for x, y in pts:
        if y < mejor_y:
            hv += (ref[0] - x) * (mejor_y - y)
            mejor_y = y
    return hv


def hipervolumen_3d(puntos, ref):
    """Hipervolumen exacto en 3D por cortes en el tercer objetivo: entre dos valores consecutivos de f3
    el volumen es el área 2D dominada por los puntos con f3 menor o igual, por el grosor del corte."""
    pts = [p for p in puntos if all(x < r for x, r in zip(p, ref))]
    niveles = sorted(set(p[2] for p in pts))
    hv = 0.0
    for i, z in enumerate(niveles):
        siguiente = niveles[i + 1] if i + 1 < len(niveles) else ref[2]
        area = hipervolumen_2d([(p[0], p[1]) for p in pts if p[2] <= z], ref[:2])
        hv += area * (siguiente - z)
    return hv


def diversidad(puntos):
    """Distancia euclídea media entre todos los pares de soluciones (objetivos normalizados)."""
    if len(puntos) < 2:
        return 0.0
    pares = list(combinations(puntos, 2))
    return sum(sqrt(sum((a - b) ** 2 for a, b in zip(p, q))) for p, q in pares) / len(pares)
