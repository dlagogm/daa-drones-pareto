"""Carga de instancias y caminos mínimos factibles entre todos los pares (Floyd-Warshall).

El grafo de la instancia solo tiene aristas entre puntos que se ven (sin atravesar zonas no-fly).
Para ir entre dos puntos que no se ven, el dron rodea el obstáculo por los waypoints: se usa el camino
de menor distancia en el grafo de visibilidad, acumulando su riesgo y su consumo.
"""
import json

INF = float('inf')


class Instancia:
    def __init__(self, datos):
        self.datos = datos
        self.nombre = datos['nombre']
        self.vertices = datos['vertices']
        self.coords = [(v['x'], v['y']) for v in self.vertices]
        self.poligonos = [[tuple(p) for p in pol] for pol in datos['poligonos']]
        self.bateria = float(datos['bateria_wh'])
        self.hub = 0
        self.destinos = [v['id'] for v in self.vertices if v['tipo'] == 'destino']
        self.estaciones = [v['id'] for v in self.vertices if v['tipo'] == 'estacion']
        self.cargadores = [self.hub] + self.estaciones
        n = len(self.vertices)
        D = [[INF] * n for _ in range(n)]
        R = [[0.0] * n for _ in range(n)]
        C = [[0.0] * n for _ in range(n)]
        sig = [[None] * n for _ in range(n)]
        for i in range(n):
            D[i][i] = 0.0; sig[i][i] = i
        for u, v, d, r, c in datos['aristas']:
            D[u][v], R[u][v], C[u][v], sig[u][v] = d, r, c, v
        # Floyd-Warshall sobre la distancia, O(V^3); riesgo y consumo se acumulan sobre el mismo camino
        for k in range(n):
            Dk, Rk, Ck = D[k], R[k], C[k]
            for i in range(n):
                dik = D[i][k]
                if dik == INF:
                    continue
                Di, Ri, Ci, si = D[i], R[i], C[i], sig[i]
                rik, cik, sik = R[i][k], C[i][k], sig[i][k]
                for j in range(n):
                    nd = dik + Dk[j]
                    if nd < Di[j] - 1e-12:
                        Di[j] = nd; Ri[j] = rik + Rk[j]; Ci[j] = cik + Ck[j]; si[j] = sik
        self.D, self.R, self.C, self.sig = D, R, C, sig
        for a in [self.hub] + self.destinos:
            for b in [self.hub] + self.destinos:
                if D[a][b] == INF:
                    raise ValueError(f'{self.nombre}: no hay camino factible de {a} a {b}')
        # reserva[b]: energía mínima para llegar desde b al cargador más cercano
        self.reserva = [min(C[b][s] for s in self.cargadores) for b in range(n)]

    @classmethod
    def desde_json(cls, ruta):
        with open(ruta) as fh:
            return cls(json.load(fh))

    def camino(self, a, b):
        """Secuencia de vértices del camino mínimo factible de a a b (para dibujar la ruta)."""
        res = [a]
        while a != b:
            a = self.sig[a][b]
            res.append(a)
        return res
