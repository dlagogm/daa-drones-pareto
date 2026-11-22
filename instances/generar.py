"""Genera instancias .json del problema de rutas de drones (mapa de 20 x 20 km).

Cada instancia contiene:
  vertices      hub (id 0), destinos, estaciones de recarga y waypoints (esquinas de las zonas no-fly
                desplazadas hacia fuera, como en un grafo de visibilidad)
  poligonos     zonas no-fly convexas
  zonas_riesgo  círculos sensibles (colegios, hospitales…) con un peso de riesgo
  viento        dirección en grados hacia la que sopla el viento
  bateria       capacidad en Wh
  aristas       [u, v, distancia_km, riesgo, consumo_Wh] solo entre pares visibles (grafo dirigido:
                el consumo depende del viento y no es simétrico)

Uso: python3 instances/generar.py            (genera n10, n15, n20 y n25)
"""
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.geometria import distancia, envolvente_convexa, punto_en_poligono, visible  # noqa: E402

LADO = 20.0
CONSUMO_KM = 20.0          # Wh por km sin viento
EFECTO_VIENTO = 0.25       # ±25 % según vuelo a favor o en contra
SEMILLA_BASE = 1000


def poligono_aleatorio(rnd, cx, cy, radio):
    """Polígono convexo: envolvente convexa de puntos aleatorios alrededor de (cx, cy)."""
    pts = []
    for _ in range(9):
        ang = rnd.uniform(0, 2 * math.pi)
        r = radio * rnd.uniform(0.6, 1.0)
        pts.append((round(cx + r * math.cos(ang), 3), round(cy + r * math.sin(ang), 3)))
    return [pts[i] for i in envolvente_convexa(pts)]


def libre(p, poligonos, margen=0.4):
    """El punto no está dentro ni demasiado cerca de ninguna zona no-fly."""
    for pol in poligonos:
        if punto_en_poligono(p, pol):
            return False
        if min(distancia(p, v) for v in pol) < margen:
            return False
    return True


def riesgo_segmento(a, b, zonas):
    """Riesgo = 0,05 por km de base + Σ peso_z · longitud del tramo dentro del círculo z (40 muestras)."""
    L = distancia(a, b)
    total = 0.05 * L
    muestras = 40
    for z in zonas:
        dentro = 0
        for k in range(muestras):
            t = (k + 0.5) / muestras
            x, y = a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])
            if (x - z['x']) ** 2 + (y - z['y']) ** 2 <= z['radio'] ** 2:
                dentro += 1
        total += z['peso'] * L * dentro / muestras
    return total


def consumo_segmento(a, b, viento_grados):
    L = distancia(a, b)
    if L == 0:
        return 0.0
    rumbo = math.atan2(b[1] - a[1], b[0] - a[0])
    factor = 1 - EFECTO_VIENTO * math.cos(rumbo - math.radians(viento_grados))
    return CONSUMO_KM * L * factor


def generar(n_destinos, semilla, n_poligonos=4, n_estaciones=4, n_zonas=4):
    rnd = random.Random(semilla)
    hub = (LADO / 2, LADO / 2)
    estaciones_fijas = [(4.0, 4.0), (16.0, 4.0), (16.0, 16.0), (4.0, 16.0)][:n_estaciones]

    poligonos = []
    while len(poligonos) < n_poligonos:
        cx, cy, radio = rnd.uniform(3, 17), rnd.uniform(3, 17), rnd.uniform(1.2, 2.2)
        pol = poligono_aleatorio(rnd, cx, cy, radio)
        centro_ok = all(distancia((cx, cy), p) > radio + 1.0 for p in [hub] + estaciones_fijas)
        separado = all(min(distancia(v, w) for v in pol for w in otro) > 0.8 for otro in poligonos)
        if centro_ok and separado and not any(punto_en_poligono((cx, cy), o) for o in poligonos):
            poligonos.append(pol)

    vertices = [{'id': 0, 'tipo': 'hub', 'x': hub[0], 'y': hub[1]}]
    puntos = [hub]
    while len(puntos) < 1 + n_destinos:
        p = (round(rnd.uniform(0.5, LADO - 0.5), 3), round(rnd.uniform(0.5, LADO - 0.5), 3))
        if libre(p, poligonos) and min(distancia(p, q) for q in puntos + estaciones_fijas) > 0.7:
            vertices.append({'id': len(vertices), 'tipo': 'destino', 'x': p[0], 'y': p[1]})
            puntos.append(p)
    for e in estaciones_fijas:
        vertices.append({'id': len(vertices), 'tipo': 'estacion', 'x': e[0], 'y': e[1]})
    for pol in poligonos:   # waypoints: esquinas desplazadas 0,3 km hacia fuera
        cx = sum(v[0] for v in pol) / len(pol); cy = sum(v[1] for v in pol) / len(pol)
        for (x, y) in pol:
            d = distancia((x, y), (cx, cy))
            w = (round(x + 0.3 * (x - cx) / d, 3), round(y + 0.3 * (y - cy) / d, 3))
            if libre(w, poligonos, margen=0.05) and 0 < w[0] < LADO and 0 < w[1] < LADO:
                vertices.append({'id': len(vertices), 'tipo': 'waypoint', 'x': w[0], 'y': w[1]})

    zonas = [{'x': round(rnd.uniform(3, 17), 2), 'y': round(rnd.uniform(3, 17), 2),
              'radio': round(rnd.uniform(1.5, 3.0), 2), 'peso': round(rnd.uniform(1.0, 3.0), 2)}
             for _ in range(n_zonas)]
    viento = rnd.choice([0, 45, 90, 135, 180, 225, 270, 315])

    coords = [(v['x'], v['y']) for v in vertices]
    aristas = []
    for u in range(len(vertices)):
        for v in range(len(vertices)):
            if u != v and visible(coords[u], coords[v], poligonos):
                aristas.append([u, v, round(distancia(coords[u], coords[v]), 4),
                                round(riesgo_segmento(coords[u], coords[v], zonas), 4),
                                round(consumo_segmento(coords[u], coords[v], viento), 3)])

    inst = {'nombre': f'n{n_destinos}', 'semilla': semilla, 'destinos': n_destinos,
            'vertices': vertices, 'poligonos': [[list(p) for p in pol] for pol in poligonos],
            'zonas_riesgo': zonas, 'viento_grados': viento, 'bateria_wh': None, 'aristas': aristas}

    # Batería: suficiente para ir de un cargador a cualquier destino y volver a un cargador (con 80 % de
    # margen), pero claramente menor que el consumo de la ruta completa, para que haya que recargar.
    from common.instancia import Instancia
    tmp = Instancia(inst | {'bateria_wh': 1.0})
    necesaria = max(min(tmp.C[s][b] for s in tmp.cargadores) + tmp.reserva[b] for b in tmp.destinos)
    inst['bateria_wh'] = round(1.8 * necesaria, 1)
    return inst


def main():
    carpeta = os.path.dirname(os.path.abspath(__file__))
    for n in (10, 15, 20, 25):
        inst = generar(n, SEMILLA_BASE + n)
        ruta = os.path.join(carpeta, f'n{n}.json')
        with open(ruta, 'w') as fh:
            json.dump(inst, fh, indent=1)
        print(f'{ruta}: {len(inst["vertices"])} vértices, {len(inst["aristas"])} aristas, '
              f'batería {inst["bateria_wh"]} Wh, viento {inst["viento_grados"]}°')


if __name__ == '__main__':
    main()
