"""Experimentos: 4 instancias x 3 algoritmos x 5 réplicas.

Para cada ejecución se mide el tiempo de CPU (time.process_time) y se guarda la frontera. La memoria pico
se mide con tracemalloc en una ejecución adicional (para no alterar los tiempos). Después, por instancia,
se normalizan los objetivos con el ideal y el nadir de la unión de todas las fronteras y se calculan:
  - hipervolumen 3D (distancia, riesgo, recargas) respecto al punto de referencia (1,1; 1,1; 1,1)
  - diversidad: distancia media entre las soluciones de la frontera (objetivos normalizados)

Uso: python3 experiments/run.py [--limite 20] [--replicas 5]
"""
import argparse
import csv
import glob
import json
import os
import statistics
import sys
import time
import tracemalloc

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, RAIZ)
from common.instancia import Instancia  # noqa: E402
from common.pareto import diversidad, hipervolumen_3d, normalizar  # noqa: E402
from run import ejecutar  # noqa: E402

ALGS = ['bb', 'geo', 'mosa']
REF = (1.1, 1.1, 1.1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limite', type=float, default=20.0)
    ap.add_argument('--replicas', type=int, default=5)
    a = ap.parse_args()
    os.makedirs(os.path.join(RAIZ, 'results'), exist_ok=True)

    todo = {}
    for ruta in sorted(glob.glob(os.path.join(RAIZ, 'instances', 'n*.json')), key=lambda r: int(os.path.basename(r)[1:-5])):
        inst = Instancia.desde_json(ruta)
        for alg in ALGS:
            reps = []
            for k in range(a.replicas):
                t0 = time.process_time()
                frente, stats = ejecutar(inst, alg, semilla=k + 1, limite=a.limite)
                t = time.process_time() - t0
                reps.append({'tiempo_s': t, 'frente': [list(o) for o, _ in frente],
                             'ordenes': [s for _, s in frente], 'completo': stats.get('completo', True)})
            tracemalloc.start()
            ejecutar(inst, alg, semilla=1, limite=a.limite)
            pico = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()
            todo[(inst.nombre, alg)] = {'N': len(inst.destinos), 'reps': reps, 'memoria_kib': pico / 1024}
            print(f'{inst.nombre:4s} {alg:5s} t={statistics.mean(r["tiempo_s"] for r in reps):8.3f}s '
                  f'mem={pico / 1024:9.1f} KiB  |frente|={statistics.mean(len(r["frente"]) for r in reps):5.1f} '
                  f'completo={all(r["completo"] for r in reps)}', flush=True)

    filas = []
    for nombre in sorted({k[0] for k in todo}, key=lambda s: int(s[1:])):
        union = [p for alg in ALGS for r in todo[(nombre, alg)]['reps'] for p in r['frente']]
        ideal = [min(p[i] for p in union) for i in range(3)]
        nadir = [max(p[i] for p in union) for i in range(3)]
        for alg in ALGS:
            e = todo[(nombre, alg)]
            hvs, divs = [], []
            for r in e['reps']:
                pn = normalizar(r['frente'], ideal, nadir)
                r['hv'] = hipervolumen_3d(pn, REF); r['div'] = diversidad(pn)
                hvs.append(r['hv']); divs.append(r['div'])
            ts = [r['tiempo_s'] for r in e['reps']]
            filas.append({'instancia': nombre, 'N': e['N'], 'algoritmo': alg,
                          'tiempo_medio_s': f'{statistics.mean(ts):.4f}', 'tiempo_std_s': f'{statistics.pstdev(ts):.4f}',
                          'memoria_kib': f'{e["memoria_kib"]:.1f}',
                          'hv_medio': f'{statistics.mean(hvs):.4f}', 'hv_std': f'{statistics.pstdev(hvs):.4f}',
                          'diversidad_media': f'{statistics.mean(divs):.4f}', 'diversidad_std': f'{statistics.pstdev(divs):.4f}',
                          'tam_frente_medio': f'{statistics.mean(len(r["frente"]) for r in e["reps"]):.1f}',
                          'completo': all(r['completo'] for r in e['reps'])})
            e['ideal'], e['nadir'] = ideal, nadir

    with open(os.path.join(RAIZ, 'results', 'resumen.csv'), 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=filas[0].keys()); w.writeheader(); w.writerows(filas)
    with open(os.path.join(RAIZ, 'results', 'frentes.json'), 'w') as fh:
        json.dump({f'{k[0]}_{k[1]}': v for k, v in todo.items()}, fh)
    print('Resultados en results/resumen.csv y results/frentes.json')


if __name__ == '__main__':
    main()
