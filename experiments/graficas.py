"""Gráficas a partir de results/resumen.csv y results/frentes.json (requiere matplotlib)."""
import csv
import json
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, Polygon  # noqa: E402

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, RAIZ)
from common.evaluacion import evaluar  # noqa: E402
from common.instancia import Instancia  # noqa: E402

OUT = os.path.join(RAIZ, 'results')
ESTILO = {'bb': ('Branch-and-Bound', '#c0392b', 'o'), 'geo': ('Heurística geométrica', '#2471a3', 's'),
          'mosa': ('Recocido simulado MO', '#1e8449', '^')}


def resumen():
    filas = list(csv.DictReader(open(os.path.join(OUT, 'resumen.csv'))))
    datos = {}
    for f in filas:
        datos.setdefault(f['algoritmo'], []).append(f)
    return datos


def guardar(fig, nombre):
    fig.tight_layout(); fig.savefig(os.path.join(OUT, nombre), dpi=200); plt.close(fig)


def tiempo(datos):
    fig, ax = plt.subplots(figsize=(5.0, 3.3))
    for alg, filas in datos.items():
        et, c, m = ESTILO[alg]
        ax.errorbar([int(f['N']) for f in filas], [float(f['tiempo_medio_s']) for f in filas],
                    yerr=[float(f['tiempo_std_s']) for f in filas], marker=m, color=c, label=et, capsize=3)
    ax.set_yscale('log'); ax.set_xlabel('Número de destinos N'); ax.set_ylabel('Tiempo medio de CPU (s)')
    ax.set_xticks([10, 15, 20, 25]); ax.grid(True, which='both', alpha=0.3); ax.legend(fontsize=8)
    ax.set_title('Tiempo frente a N (escala logarítmica)', fontsize=10)
    guardar(fig, 'tiempo_vs_n.png')


def barras(datos, clave, std, ylabel, titulo, nombre):
    fig, ax = plt.subplots(figsize=(5.0, 3.3))
    ns = [10, 15, 20, 25]
    ancho = 0.26
    for k, (alg, filas) in enumerate(sorted(datos.items())):
        et, c, _ = ESTILO[alg]
        ax.bar([i + (k - 1) * ancho for i in range(4)], [float(f[clave]) for f in filas], ancho,
               yerr=[float(f[std]) for f in filas], color=c, label=et, capsize=3)
    ax.set_xticks(range(4)); ax.set_xticklabels([f'N={n}' for n in ns])
    ax.set_ylabel(ylabel); ax.set_title(titulo, fontsize=10); ax.grid(True, axis='y', alpha=0.3); ax.legend(fontsize=8)
    guardar(fig, nombre)


def frentes(nombre_inst):
    fr = json.load(open(os.path.join(OUT, 'frentes.json')))
    fig, ax = plt.subplots(figsize=(5.0, 3.3))
    for alg in ('bb', 'geo', 'mosa'):
        et, c, m = ESTILO[alg]
        e = fr[f'{nombre_inst}_{alg}']
        mejor = max(e['reps'], key=lambda r: r['hv'])
        pts = sorted(mejor['frente'])
        ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=[18 + 10 * p[2] for p in pts], color=c,
                   marker=m, alpha=0.75, label=et)
        for p in pts:
            ax.annotate(str(int(p[2])), (p[0], p[1]), fontsize=6, xytext=(3, 3), textcoords='offset points')
    ax.set_xlabel('Distancia total (km)'); ax.set_ylabel('Riesgo acumulado')
    ax.set_title(f'Fronteras aproximadas, instancia {nombre_inst} (número = recargas)', fontsize=9)
    ax.grid(True, alpha=0.3); ax.legend(fontsize=7)
    guardar(fig, f'frentes_{nombre_inst}.png')


def mapa(nombre_inst):
    inst = Instancia.desde_json(os.path.join(RAIZ, 'instances', f'{nombre_inst}.json'))
    fr = json.load(open(os.path.join(OUT, 'frentes.json')))
    e = fr[f'{nombre_inst}_mosa']
    mejor = max(e['reps'], key=lambda r: r['hv'])
    # solución «rodilla»: la más cercana al ideal en objetivos normalizados
    ideal, nadir = e['ideal'], e['nadir']
    def dist_ideal(p):
        return sum(((x - lo) / (hi - lo) if hi > lo else 0) ** 2 for x, lo, hi in zip(p, ideal, nadir))
    k = min(range(len(mejor['frente'])), key=lambda i: dist_ideal(mejor['frente'][i]))
    orden = mejor['ordenes'][k]
    obj, paradas = evaluar(inst, orden, detalle=True)
    fig, ax = plt.subplots(figsize=(5.0, 5.0))
    for z in inst.datos['zonas_riesgo']:
        ax.add_patch(Circle((z['x'], z['y']), z['radio'], color='#f5b041', alpha=0.25 + 0.08 * z['peso']))
    for pol in inst.poligonos:
        ax.add_patch(Polygon(pol, closed=True, color='#922b21', alpha=0.75))
    xs, ys = [], []
    for a, b in zip(paradas, paradas[1:]):
        for v in inst.camino(a, b):
            xs.append(inst.coords[v][0]); ys.append(inst.coords[v][1])
    ax.plot(xs, ys, color='#1f618d', linewidth=1.3, zorder=3)
    for v in inst.vertices:
        if v['tipo'] == 'destino':
            ax.plot(v['x'], v['y'], 'o', color='#1e8449', markersize=5, zorder=4)
        elif v['tipo'] == 'estacion':
            ax.plot(v['x'], v['y'], 's', color='#7d3c98', markersize=7, zorder=4)
    ax.plot(*inst.coords[0], '*', color='black', markersize=13, zorder=5)
    ax.set_xlim(0, 20); ax.set_ylim(0, 20); ax.set_aspect('equal')
    ax.set_title(f'{nombre_inst}: ruta de compromiso ({obj[0]:.1f} km, riesgo {obj[1]:.1f}, {int(obj[2])} recargas)',
                 fontsize=8)
    ax.set_xlabel('km'); ax.set_ylabel('km')
    guardar(fig, f'mapa_{nombre_inst}.png')


def main():
    d = resumen()
    tiempo(d)
    barras(d, 'hv_medio', 'hv_std', 'Hipervolumen (normalizado)', 'Hipervolumen dominado (media ± desv.)', 'hipervolumen.png')
    barras(d, 'diversidad_media', 'diversidad_std', 'Distancia media entre soluciones',
           'Diversidad de la frontera (media ± desv.)', 'diversidad.png')
    frentes('n15')
    mapa('n15')
    print('Gráficas en results/')


if __name__ == '__main__':
    main()
