PY ?= python3
LIMITE ?= 20

.PHONY: run test instancias experimentos graficas demo limpiar

## make run: genera las instancias si faltan, ejecuta las pruebas, los experimentos y las gráficas
run: instancias test experimentos graficas

instancias:
	@ls instances/n10.json >/dev/null 2>&1 || $(PY) instances/generar.py

test:
	$(PY) -m unittest discover -s tests -t . -v

experimentos:
	$(PY) experiments/run.py --limite $(LIMITE)

graficas:
	$(PY) experiments/graficas.py

## make demo: los tres algoritmos sobre la instancia n10
demo:
	$(PY) run.py instances/n10.json --algoritmo geo
	$(PY) run.py instances/n10.json --algoritmo mosa --semilla 1
	$(PY) run.py instances/n10.json --algoritmo bb --limite $(LIMITE)

limpiar:
	rm -f results/*.csv results/*.json results/*.png
