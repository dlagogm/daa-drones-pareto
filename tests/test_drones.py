"""Pruebas: python3 -m unittest discover -s tests -t ."""
import itertools
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from common.evaluacion import evaluar  # noqa: E402
from common.geometria import envolvente_convexa, punto_en_poligono, segmentos_se_cortan, visible  # noqa: E402
from common.instancia import Instancia  # noqa: E402
from common.pareto import diversidad, domina, hipervolumen_2d, hipervolumen_3d, no_dominadas  # noqa: E402
from exact_bb import bb  # noqa: E402
from geo_heuristic import geo  # noqa: E402
from instances.generar import generar  # noqa: E402
from metaheuristic import mosa  # noqa: E402


class TestGeometria(unittest.TestCase):
    def test_interseccion_segmentos(self):
        self.assertTrue(segmentos_se_cortan((0, 0), (2, 2), (0, 2), (2, 0)))     # cruce en X
        self.assertFalse(segmentos_se_cortan((0, 0), (1, 1), (2, 2), (3, 0)))
        self.assertTrue(segmentos_se_cortan((0, 0), (2, 0), (1, 0), (3, 0)))     # colineales solapados
        self.assertTrue(segmentos_se_cortan((0, 0), (2, 0), (2, 0), (3, 1)))     # se tocan en un extremo
        self.assertFalse(segmentos_se_cortan((0, 0), (1, 0), (2, 0), (3, 0)))    # colineales separados

    def test_punto_en_poligono_y_visibilidad(self):
        cuadrado = [(1, 1), (3, 1), (3, 3), (1, 3)]
        self.assertTrue(punto_en_poligono((2, 2), cuadrado))
        self.assertFalse(punto_en_poligono((4, 2), cuadrado))
        self.assertFalse(visible((0, 2), (4, 2), [cuadrado]))                   # atraviesa el cuadrado
        self.assertTrue(visible((0, 0), (4, 0), [cuadrado]))
        self.assertFalse(visible((0, 0), (4, 4), [cuadrado]))                   # pasa por dos vértices

    def test_envolvente(self):
        pts = [(0, 0), (2, 0), (2, 2), (0, 2), (1, 1), (1, 0.5)]
        self.assertEqual(sorted(envolvente_convexa(pts)), [0, 1, 2, 3])


class TestPareto(unittest.TestCase):
    def test_dominancia_y_filtro(self):
        self.assertTrue(domina((1, 1, 0), (1, 2, 0)))
        self.assertFalse(domina((1, 2, 0), (2, 1, 0)))
        nd = no_dominadas([((1, 3, 0), 'a'), ((2, 2, 0), 'b'), ((3, 3, 0), 'c'), ((2, 2, 0), 'd')])
        self.assertEqual(sorted(o for o, _ in nd), [(1, 3, 0), (2, 2, 0)])

    def test_hipervolumen(self):
        self.assertAlmostEqual(hipervolumen_2d([(0, 0)], (1, 1)), 1.0)
        self.assertAlmostEqual(hipervolumen_2d([(0, 0.5), (0.5, 0)], (1, 1)), 0.75)
        self.assertAlmostEqual(hipervolumen_3d([(0, 0, 0)], (1, 1, 1)), 1.0)
        self.assertAlmostEqual(hipervolumen_3d([(0, 0, 0.5), (0.5, 0.5, 0)], (1, 1, 1)), 0.5 * 0.25 + 0.5 * 1.0)
        self.assertAlmostEqual(diversidad([(0, 0), (3, 4)]), 5.0)


class TestAlgoritmos(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inst = Instancia(generar(7, semilla=11))   # instancia pequeña: 7! = 5040 rutas

    def frente_fuerza_bruta(self):
        sols = [(evaluar(self.inst, list(p)), list(p)) for p in itertools.permutations(self.inst.destinos)]
        return sorted(o for o, _ in no_dominadas(sols))

    def test_todas_las_rutas_son_factibles(self):
        rnd = random.Random(0)
        for _ in range(50):
            o = evaluar(self.inst, rnd.sample(self.inst.destinos, len(self.inst.destinos)))
            self.assertTrue(all(x < float('inf') for x in o))

    def test_bb_es_exacto(self):
        frente, stats = bb.resolver(self.inst, limite_s=60)
        self.assertTrue(stats['completo'])
        esperado = self.frente_fuerza_bruta()
        obtenido = sorted(o for o, _ in frente)
        self.assertEqual(len(esperado), len(obtenido))
        for a, b in zip(esperado, obtenido):
            for x, y in zip(a, b):
                self.assertAlmostEqual(x, y, places=6)

    def test_heuristicas_no_dominan_al_optimo(self):
        exacto = self.frente_fuerza_bruta()
        for frente in (geo.resolver(self.inst)[0], mosa.resolver(self.inst, semilla=1)[0]):
            for o, orden in frente:
                self.assertEqual(sorted(orden), sorted(self.inst.destinos))   # visita todos una vez
                self.assertFalse(any(domina(o, e) for e in exacto))


if __name__ == '__main__':
    unittest.main()
