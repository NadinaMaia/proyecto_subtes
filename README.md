# Análisis de demanda de la red de Subte de Buenos Aires

Proyecto de análisis de demanda por estación y tipo de día, con perfiles horarios, FPCA, clustering y un dashboard interactivo hecho con Plotly Dash.

## Ver el dashboard

GitHub muestra los notebooks como documentos estáticos: **no ejecuta la aplicación Dash ni sus controles interactivos**. Para usar el dashboard en una computadora:

1. Cloná o descargá el repositorio y abrilo en VS Code.
2. Creá un entorno virtual e instalá las dependencias:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install -r requirements_subte_vscode.txt
   ```

   En Windows, activá el entorno con `.venv\Scripts\activate`.
3. Abrí `notebooks/creacion_dashboard.ipynb`, seleccioná el kernel de `.venv` y ejecutá las celdas en orden. La última celda inicia Dash; abrí la dirección local que indique (por defecto, `http://127.0.0.1:8050`).

Para ejecutar el dashboard **no hace falta volver a procesar los CSV originales ni correr el análisis FPCA**, siempre que el repositorio incluya los seis archivos de resultados indicados más abajo.

También se puede iniciar como aplicación independiente, sin abrir Jupyter:

```bash
python -m pip install -r requirements.txt
python app.py
```

Abrí `http://127.0.0.1:8050`. En Render y Railway se usa Gunicorn para iniciar la misma aplicación.

## Archivos necesarios para el dashboard

Además de los notebooks, dependencias y recursos visuales, el dashboard necesita:

- `data/estaciones.geojson`
- `subte_fpca_work/resultados/metricas_priorizacion_operativa.csv`
- `subte_fpca_work/resultados/mapa_estaciones_perfil_tipico.csv`
- `subte_fpca_work/resultados/perfiles_suavizados_segmentados.csv`
- `subte_fpca_work/resultados/scores_fpca_clusters_segmentados.csv`
- `subte_fpca_work/resultados/serie_diaria_red.csv`
- `subte_fpca_work/resultados/mapa_estaciones_georreferenciadas.csv`

Estos CSV son resultados derivados del análisis y permiten abrir el dashboard sin los datos crudos. Si no están disponibles, primero hay que generarlos ejecutando el análisis.

## Contenido

- `notebooks/Proyecto_Subte_FPCA_2014-26.ipynb`: preparación de datos, análisis funcional (FPCA), clustering y resultados.
- `notebooks/creacion_dashboard.ipynb`: aplicación interactiva de exploración de la red y sus patrones de demanda.
- `notebooks/revision_fechas.ipynb`: inspección de formatos de fecha en los archivos de entrada.
- `data/estaciones.geojson`: geometrías y ubicaciones de estaciones utilizadas en el mapa.
- `subte_fpca_work/resultados/`: archivos derivados utilizados por el dashboard y el análisis.
- `assets/` y `outputs/`: recursos gráficos y materiales de presentación.
