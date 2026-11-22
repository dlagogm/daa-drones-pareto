"""Heurística geométrica rápida basada en visibilidad e intersección de segmentos.

1. Grafo de visibilidad: dos puntos se conectan solo si el segmento no corta ninguna zona no-fly
   (test de intersección de segmentos, common/geometria.py). Los caminos entre puntos que no se ven
   rodean los obstáculos por los waypoints (Floyd-Warshall, common/instancia.py).
2. Construcción por inserción desde la envolvente convexa: se parte del circuito formado por los puntos
   de la envolvente convexa (hub y destinos) y se insertan los demás donde menos aumentan el coste.
3. Mejora 2-opt: se invierten tramos mientras mejore el coste. En el plano, 2-opt elimina los cruces de
   la ruta consigo misma, que siempre son subóptimos para la distancia euclídea.
4. Multiobjetivo: se repiten 2–3 con 11 pesos λ ∈ {0; 0,1; …; 1} sobre el coste
   λ·distancia + (1−λ)·riesgo (normalizados) y se filtran las rutas no dominadas.

Coste: O(N² ) por inserción y O(N³) por pasada de 2-opt (el grafo es dirigido por el viento, así que al
invertir un tramo se recalcula su coste), por cada uno de los 11 pesos.
"""
from common.evaluacion import evaluar
from common.geometria import envolvente_convexa
from common.pareto import no_dominadas

PESOS = [i / 10 for i in range(11)]


def _matriz_coste(inst, lam):
    nodos = [inst.hub] + inst.destinos
    md = sum(inst.D[a][b] for a in nodos for b in nodos if a != b) / (len(nodos) * (len(nodos) - 1))
    mr = sum(inst.R[a][b] for a in nodos for b in nodos if a != b) / (len(nodos) * (len(nodos) - 1))
    return {(a, b): lam * inst.D[a][b] / md + (1 - lam) * inst.R[a][b] / mr for a in nodos for b in nodos}


def _coste_circuito(W, circ):
    return sum(W[circ[i], circ[(i + 1) % len(circ)]] for i in range(len(circ)))


def _insercion_envolvente(inst, W):
    nodos = [inst.hub] + inst.destinos
    pts = [inst.coords[v] for v in nodos]
    circ = [nodos[i] for i in envolvente_convexa(pts)]
    if inst.hub not in circ:                       # el hub siempre en el circuito inicial
        mejor = min(range(len(circ)), key=lambda i: W[circ[i], inst.hub] + W[inst.hub, circ[(i + 1) % len(circ)]]
                    - W[circ[i], circ[(i + 1) % len(circ)]])
        circ.insert(mejor + 1, inst.hub)
    pendientes = [v for v in nodos if v not in circ]
    while pendientes:                              # inserción más barata
        mejor = None
        for v in pendientes:
            for i in range(len(circ)):
                a, b = circ[i], circ[(i + 1) % len(circ)]
                delta = W[a, v] + W[v, b] - W[a, b]
                if mejor is None or delta < mejor[0]:
                    mejor = (delta, v, i)
        _, v, i = mejor
        circ.insert(i + 1, v); pendientes.remove(v)
    k = circ.index(inst.hub)
    return circ[k:] + circ[:k]                     # empieza en el hub


def _dos_opt(W, ruta):
    """ruta empieza por el hub; se invierten tramos ruta[i..j] con 1 ≤ i < j."""
    ruta = list(ruta)
    n = len(ruta)
    mejora = True
    while mejora:
        mejora = False
        coste = _coste_circuito(W, ruta)
        for i in range(1, n - 1):
            for j in range(i + 1, n):
                nueva = ruta[:i] + ruta[i:j + 1][::-1] + ruta[j + 1:]
                c = _coste_circuito(W, nueva)
                if c < coste - 1e-12:
                    ruta, coste, mejora = nueva, c, True
    return ruta


def resolver(inst, **_):
    soluciones = []
    for lam in PESOS:
        W = _matriz_coste(inst, lam)
        ruta = _dos_opt(W, _insercion_envolvente(inst, W))
        orden = ruta[1:]
        soluciones.append((evaluar(inst, orden), orden))
    return no_dominadas(soluciones), {'pesos': len(PESOS)}
