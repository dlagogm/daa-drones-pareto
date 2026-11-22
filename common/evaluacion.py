"""Evaluación de una ruta: orden de visita de los destinos → vector de objetivos.

Objetivos (todos a minimizar):  f1 = distancia total (km),  f2 = riesgo acumulado,  f3 = paradas de recarga.

La ruta es un circuito hub → d1 → … → dk → hub (circuito hamiltoniano sobre los destinos). La batería se
simula tramo a tramo: antes de volar de a a b se exige llegar a b con energía suficiente para alcanzar
después algún cargador (reserva). Si no es posible, se busca la secuencia de recargas a → s1 → … → b de
menor distancia (normalmente un solo cargador), se recarga al 100 % en cada uno y se cuenta cada parada.
La decisión de dónde recargar es determinista, así que el espacio de búsqueda son las permutaciones.
"""

EPS = 1e-9


def paso(inst, bateria, a, b):
    """Vuela de a a b con la batería dada. Devuelve (batería_final, dist, riesgo, recargas, cargadores)
    o None si es imposible.

    Si el tramo directo no es viable, busca con Dijkstra (sobre los pocos cargadores) la secuencia de
    recargas a → s1 → … → sk → b de menor distancia en la que cada salto cabe en la batería."""
    C, D, R, B = inst.C, inst.D, inst.R, inst.bateria
    if bateria - C[a][b] >= inst.reserva[b] - EPS:
        return bateria - C[a][b], D[a][b], R[a][b], 0, ()
    cache = inst.__dict__.setdefault('_cache_desvios', {})
    clave = (a, b, round(bateria, 6))
    if clave in cache:
        return cache[clave]
    # Dijkstra: estado = cargador en el que se acaba de recargar (batería llena)
    mejor_d = {s: (D[a][s], R[a][s], (s,)) for s in inst.cargadores if s != a and bateria - C[a][s] >= -EPS}
    hechos = set()
    resultado = None
    while True:
        pend = [s for s in mejor_d if s not in hechos]
        if not pend:
            break
        s = min(pend, key=lambda x: mejor_d[x][0])
        hechos.add(s)
        d_s, r_s, cam = mejor_d[s]
        if resultado is not None and d_s >= resultado[1]:
            break
        if B - C[s][b] >= inst.reserva[b] - EPS:
            total = d_s + D[s][b]
            if resultado is None or total < resultado[1]:
                resultado = (B - C[s][b], total, r_s + R[s][b], len(cam), cam)
        for t in inst.cargadores:
            if t not in hechos and t != s and C[s][t] <= B + EPS:
                nd = d_s + D[s][t]
                if t not in mejor_d or nd < mejor_d[t][0]:
                    mejor_d[t] = (nd, r_s + R[s][t], cam + (t,))
    cache[clave] = resultado
    return resultado


def evaluar(inst, orden, detalle=False):
    """orden: lista con los destinos en el orden de visita. Devuelve (dist, riesgo, recargas)
    y, si detalle=True, también la secuencia de paradas (incluidos los cargadores)."""
    bateria = inst.bateria
    dist = riesgo = 0.0
    recargas = 0
    actual = inst.hub
    paradas = [inst.hub]
    for b in list(orden) + [inst.hub]:
        r = paso(inst, bateria, actual, b)
        if r is None:
            inf = float('inf')
            return ((inf, inf, inf), paradas) if detalle else (inf, inf, inf)
        bateria, d, rg, rc, cargadores = r
        dist += d; riesgo += rg; recargas += rc
        paradas.extend(cargadores)
        paradas.append(b)
        actual = b
    obj = (dist, riesgo, recargas)
    return (obj, paradas) if detalle else obj
