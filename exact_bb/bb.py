"""Ramificación y poda multiobjetivo con poda guiada por cotas heurísticas.

Árbol de búsqueda: cada nivel fija el siguiente destino de la ruta (permutaciones, O(N!) en el peor caso).
Para cada nodo se calcula un vector de cotas inferiores
    LB = (dist_actual + Σ_{v pendiente} min_entrada_dist(v) + min_entrada_dist(hub),
          riesgo_actual + Σ_{v pendiente} min_entrada_riesgo(v) + min_entrada_riesgo(hub),
          recargas_actuales)
que es válida porque todo destino pendiente (y el hub) tendrá que recibir una arista de entrada y, por
la desigualdad triangular de los caminos mínimos, un desvío a un cargador nunca cuesta menos que el
tramo directo. Si alguna solución del archivo domina o iguala a LB, ninguna ruta del subárbol puede
entrar en la frontera de Pareto y se poda.

Poda guiada por heurística: el archivo se inicializa con las rutas de la heurística geométrica y los
hijos se exploran en orden creciente de distancia + riesgo normalizados (los mejores primero), lo que
acerca antes la frontera y aumenta las podas.

Si se agota el tiempo límite, devuelve la frontera encontrada hasta entonces (algoritmo «anytime»)
e indica completo=False.
"""
import time

from common.evaluacion import paso
from common.pareto import domina_o_igual, insertar_en_archivo


def resolver(inst, limite_s=20.0, archivo_inicial=None, **_):
    nodos = [inst.hub] + inst.destinos
    D, R = inst.D, inst.R
    min_d = {v: min(D[u][v] for u in nodos if u != v) for v in nodos}
    min_r = {v: min(R[u][v] for u in nodos if u != v) for v in nodos}
    md = sum(D[a][b] for a in nodos for b in nodos if a != b) / (len(nodos) * (len(nodos) - 1))
    mr = sum(R[a][b] for a in nodos for b in nodos if a != b) / (len(nodos) * (len(nodos) - 1))

    archivo = []
    for obj, orden in (archivo_inicial or []):
        insertar_en_archivo(archivo, obj, orden)

    inicio = time.perf_counter()
    stats = {'nodos': 0, 'podas': 0, 'completo': True}
    ruta = []

    def dfs(actual, bateria, dist, riesgo, rec, pendientes, lb_d, lb_r):
        stats['nodos'] += 1
        if stats['nodos'] % 2000 == 0 and time.perf_counter() - inicio > limite_s:
            stats['completo'] = False
            raise TimeoutError
        if not pendientes:
            r = paso(inst, bateria, actual, inst.hub)
            if r is not None:
                insertar_en_archivo(archivo, (dist + r[1], riesgo + r[2], rec + r[3]), ruta)
            return
        hijos = sorted(pendientes, key=lambda v: D[actual][v] / md + R[actual][v] / mr)
        for v in hijos:
            r = paso(inst, bateria, actual, v)
            if r is None:
                continue
            nb, d, rg, rc, _ = r
            nlb_d, nlb_r = lb_d - min_d[v], lb_r - min_r[v]
            cota = (dist + d + nlb_d, riesgo + rg + nlb_r, rec + rc)
            if any(domina_o_igual(o, cota) for o, _ in archivo):
                stats['podas'] += 1
                continue
            ruta.append(v); pendientes.remove(v)
            dfs(v, nb, dist + d, riesgo + rg, rec + rc, pendientes, nlb_d, nlb_r)
            pendientes.add(v); ruta.pop()

    lb_d0 = sum(min_d[v] for v in inst.destinos) + min_d[inst.hub]
    lb_r0 = sum(min_r[v] for v in inst.destinos) + min_r[inst.hub]
    try:
        dfs(inst.hub, inst.bateria, 0.0, 0.0, 0, set(inst.destinos), lb_d0, lb_r0)
    except TimeoutError:
        pass
    stats['tiempo_busqueda_s'] = time.perf_counter() - inicio
    return sorted(archivo), stats
