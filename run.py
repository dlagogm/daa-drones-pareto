"""Ejecuta un algoritmo sobre una instancia .json y muestra la frontera de Pareto obtenida.

  python3 run.py instances/n10.json --algoritmo geo
  python3 run.py instances/n10.json --algoritmo bb --limite 20
  python3 run.py instances/n15.json --algoritmo mosa --semilla 3 --salida results/frente.json
"""
import argparse
import json
import time

from common.instancia import Instancia
from exact_bb import bb
from geo_heuristic import geo
from metaheuristic import mosa

ALGORITMOS = {'bb': 'Branch-and-Bound (exact_bb)', 'geo': 'Heurística geométrica (geo_heuristic)',
              'mosa': 'Recocido simulado multiobjetivo (metaheuristic)'}


def ejecutar(inst, algoritmo, semilla=0, limite=20.0):
    if algoritmo == 'geo':
        return geo.resolver(inst)
    if algoritmo == 'mosa':
        inicial, _ = geo.resolver(inst)          # el recocido refina las rutas de la heurística geométrica
        return mosa.resolver(inst, semilla=semilla, archivo_inicial=inicial)
    if algoritmo == 'bb':
        inicial, _ = geo.resolver(inst)          # cotas iniciales de la heurística geométrica
        return bb.resolver(inst, limite_s=limite, archivo_inicial=inicial)
    raise ValueError(algoritmo)


def main():
    ap = argparse.ArgumentParser(description='Rutas multiobjetivo de drones')
    ap.add_argument('instancia', help='fichero .json de la instancia')
    ap.add_argument('--algoritmo', choices=ALGORITMOS, default='geo')
    ap.add_argument('--semilla', type=int, default=0, help='semilla de la metaheurística')
    ap.add_argument('--limite', type=float, default=20.0, help='tiempo límite de B&B en segundos')
    ap.add_argument('--salida', help='guarda la frontera en este .json')
    a = ap.parse_args()

    inst = Instancia.desde_json(a.instancia)
    t0 = time.perf_counter()
    frente, stats = ejecutar(inst, a.algoritmo, a.semilla, a.limite)
    t = time.perf_counter() - t0
    print(f'{ALGORITMOS[a.algoritmo]} sobre {inst.nombre} ({len(inst.destinos)} destinos): '
          f'{len(frente)} soluciones no dominadas en {t:.2f} s  {stats}')
    print(f'{"distancia (km)":>15} {"riesgo":>10} {"recargas":>9}  ruta')
    for (d, r, c), orden in frente:
        print(f'{d:15.2f} {r:10.2f} {int(c):9d}  {orden}')
    if a.salida:
        with open(a.salida, 'w') as fh:
            json.dump({'instancia': inst.nombre, 'algoritmo': a.algoritmo, 'tiempo_s': t,
                       'frente': [{'objetivos': list(o), 'orden': s} for o, s in frente]}, fh, indent=1)


if __name__ == '__main__':
    main()
