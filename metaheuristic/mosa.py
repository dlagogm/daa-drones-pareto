"""Recocido simulado multiobjetivo (MOSA) con archivo de Pareto acotado por crowding (NSGA-II).

- Refinamiento: el archivo inicial contiene las rutas de la heurística geométrica (si se pasan) más una
  ruta del vecino más cercano y 30 rutas aleatorias, y el recocido las refina.
- Representación: permutación de los destinos.
- Vecindario: inversión de un tramo (2-opt, 50 %), reubicación de un destino (30 %) o intercambio de dos
  destinos (20 %).
- Escalarización: en cada uno de los 10 ciclos se elige un vector de pesos aleatorio w en el símplex
  (distancia, riesgo, recargas) y se parte de una solución del archivo. Se acepta un vecino si mejora
  f_w = Σ w_i·f̂_i (objetivos normalizados) o, si empeora en Δ, con probabilidad exp(−Δ/T) (Metropolis).
  T baja geométricamente de T0 = 0,2 a Tf = 0,002 dentro de cada ciclo.
- Archivo: guarda todas las soluciones no dominadas encontradas; si supera 40, elimina la de menor
  distancia de crowding (la más «amontonada»), como en NSGA-II, para mantener la diversidad.

Coste: O(iteraciones · N · S), donde S es el número de cargadores (evaluar una ruta es O(N·S)).
"""
import math
import random

from common.evaluacion import evaluar
from common.pareto import crowding, insertar_en_archivo

MAX_ARCHIVO = 40
CICLOS = 10
T0, TF = 0.2, 0.002


def _vecino(orden, rnd):
    s = list(orden)
    n = len(s)
    x = rnd.random()
    i, j = sorted(rnd.sample(range(n), 2))
    if x < 0.5:
        s[i:j + 1] = reversed(s[i:j + 1])
    elif x < 0.8:
        v = s.pop(i); s.insert(j, v)
    else:
        s[i], s[j] = s[j], s[i]
    return s


def _vecino_mas_cercano(inst, rnd):
    pendientes = set(inst.destinos)
    actual, orden = inst.hub, []
    while pendientes:
        v = min(pendientes, key=lambda u: (inst.D[actual][u], rnd.random()))
        orden.append(v); pendientes.remove(v); actual = v
    return orden


def resolver(inst, semilla=0, iteraciones=None, archivo_inicial=None, **_):
    rnd = random.Random(semilla)
    n = len(inst.destinos)
    iteraciones = iteraciones or 4000 * n
    archivo = []

    # Muestra inicial para estimar los rangos de normalización
    muestra = [_vecino_mas_cercano(inst, rnd)] + [rnd.sample(inst.destinos, n) for _ in range(30)]
    muestra += [list(o) for _, o in (archivo_inicial or [])]
    objs = [evaluar(inst, s) for s in muestra]
    for o, s in zip(objs, muestra):
        insertar_en_archivo(archivo, o, s)
    lo = [min(o[k] for o in objs) for k in range(3)]
    hi = [max(o[k] for o in objs) for k in range(3)]
    rango = [max(h - l, 1e-9) for l, h in zip(lo, hi)]

    def escalar(o, w):
        return sum(wi * (oi - li) / ri for wi, oi, li, ri in zip(w, o, lo, rango))

    por_ciclo = iteraciones // CICLOS
    aceptados = 0
    for _ in range(CICLOS):
        w = [rnd.expovariate(1.0) for _ in range(3)]
        sw = sum(w); w = [x / sw for x in w]
        actual, f_act = None, None
        _, actual = rnd.choice(archivo)
        f_act = escalar(evaluar(inst, actual), w)
        for k in range(por_ciclo):
            T = T0 * (TF / T0) ** (k / max(por_ciclo - 1, 1))
            cand = _vecino(actual, rnd)
            o = evaluar(inst, cand)
            f = escalar(o, w)
            if f <= f_act or rnd.random() < math.exp(-(f - f_act) / T):
                actual, f_act = cand, f
                aceptados += 1
            if insertar_en_archivo(archivo, o, cand) and len(archivo) > MAX_ARCHIVO:
                cd = crowding([a[0] for a in archivo])
                archivo.pop(min(range(len(archivo)), key=lambda i: cd[i]))
    return sorted(archivo), {'iteraciones': iteraciones, 'aceptados': aceptados}
