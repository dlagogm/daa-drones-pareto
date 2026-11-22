# Planificación multiobjetivo de rutas de drones

Actividad 2 de *Diseño Avanzado de Algoritmos* (UNIPRO). Un dron sale del hub central, visita una vez cada destino y vuelve al hub (circuito hamiltoniano), sin atravesar zonas no-fly. Se minimizan tres objetivos a la vez:

1. distancia total (km)
2. riesgo acumulado sobre zonas sensibles
3. paradas de recarga

La batería es limitada, así que en algunos tramos el dron tiene que desviarse a una estación de recarga.

## Algoritmos

| Carpeta | Algoritmo | Idea |
|---|---|---|
| `exact_bb/` | Ramificación y poda multiobjetivo | Recorre las permutaciones en profundidad. Poda un subárbol cuando una solución del archivo de Pareto domina el vector de cotas inferiores. El archivo inicial y el orden de exploración vienen de la heurística geométrica. Es exacto si termina antes del tiempo límite; si no, devuelve la mejor frontera encontrada. |
| `geo_heuristic/` | Heurística geométrica | Construye el grafo de visibilidad con tests de intersección de segmentos y rodea los obstáculos por sus esquinas. Inserta los destinos a partir de la envolvente convexa y mejora la ruta con 2-opt. Repite el proceso con 11 pesos para distancia y riesgo y filtra las rutas no dominadas. |
| `metaheuristic/` | Recocido simulado multiobjetivo (MOSA) | Usa vecindarios 2-opt, de reubicación y de intercambio, con pesos aleatorios en cada ciclo y aceptación de Metropolis. Mantiene un archivo de Pareto que se recorta por distancia de *crowding*, como NSGA-II. |

El código común está en `common/`:

| Fichero | Contenido |
|---|---|
| `geometria.py` | Orientación, intersección de segmentos, punto en polígono y envolvente convexa |
| `instancia.py` | Carga de instancias y caminos mínimos factibles con Floyd-Warshall |
| `evaluacion.py` | Simulación de la batería y cálculo de los objetivos |
| `pareto.py` | Dominancia, *crowding*, hipervolumen 3D y diversidad |

## Requisitos y ejecución

Hace falta Python 3.10 o posterior, `make` y `matplotlib` (solo para las gráficas): `pip install -r requirements.txt`.

```bash
make run
```

`make run` lo hace todo: genera las instancias si faltan, ejecuta las pruebas, los experimentos y las gráficas. Tarda unos 8 minutos, sobre todo por el tiempo límite de ramificación y poda.

| Comando | Qué hace |
|---|---|
| `make test` | 8 pruebas: geometría, hipervolumen, factibilidad de rutas, ramificación y poda frente a fuerza bruta en una instancia de 7 destinos, y que las heurísticas no «mejoran» al óptimo |
| `make demo` | Ejecuta los tres algoritmos sobre `instances/n10.json` |
| `make experimentos LIMITE=20` | 4 instancias × 3 algoritmos × 5 réplicas. Guarda `results/resumen.csv` y `results/frentes.json` |
| `make graficas` | Tiempo frente a N, hipervolumen, diversidad, fronteras y mapa de una ruta |
| `python3 run.py <instancia.json> --algoritmo {bb,geo,mosa} [--semilla S] [--limite s] [--salida f.json]` | Ejecuta un algoritmo sobre cualquier instancia `.json` |

## Instancias (`instances/`)

`instances/generar.py` crea `n10.json`, `n15.json`, `n20.json` y `n25.json` con semillas fijas. Cada fichero contiene:

- un mapa de 20 × 20 km con el hub en el centro;
- N destinos y 4 estaciones de recarga;
- 4 zonas no-fly poligonales y sus esquinas como *waypoints*;
- 4 zonas de riesgo circulares;
- la dirección del viento y la capacidad de batería;
- la lista de aristas dirigidas `[u, v, distancia_km, riesgo, consumo_Wh]`, solo entre puntos visibles. El consumo depende del viento, así que el grafo no es simétrico.
