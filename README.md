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

## Reproducir el análisis

Para reconstruir los resultados a partir de los datos crudos:

1. Colocá los CSV originales en `data/`, conservando su estructura de carpetas.
2. Ejecutá `notebooks/revision_fechas.ipynb` para crear `subte_fpca_work/formato_fechas_por_archivo.csv`.
3. Ejecutá todas las celdas de `notebooks/Proyecto_Subte_FPCA_2014-26.ipynb`. La primera ejecución puede tardar y requiere espacio adicional para la caché y los resultados.
4. Ejecutá `notebooks/creacion_dashboard.ipynb` para abrir el dashboard.

`notebooks/revision_fechas.ipynb` es una herramienta de auditoría previa; no es necesario ejecutarla para ver el dashboard si los resultados ya están preparados.

## Contenido

- `notebooks/Proyecto_Subte_FPCA_2014-26.ipynb`: preparación de datos, análisis funcional (FPCA), clustering y resultados.
- `notebooks/creacion_dashboard.ipynb`: aplicación interactiva de exploración de la red y sus patrones de demanda.
- `notebooks/revision_fechas.ipynb`: inspección de formatos de fecha en los archivos de entrada.
- `data/estaciones.geojson`: geometrías y ubicaciones de estaciones utilizadas en el mapa.
- `subte_fpca_work/resultados/`: archivos derivados utilizados por el dashboard y el análisis.
- `assets/` y `outputs/`: recursos gráficos y materiales de presentación.

## Publicación y datos

Los datos originales de `data/` ocupan aproximadamente 12 GB y las cachés locales de `subte_fpca_work/` más de 1 GB. No hace falta subir esos datos crudos ni las cachés para compartir una copia ejecutable del dashboard: incluí el GeoJSON y los seis resultados requeridos, y omití CSV originales, cachés y temporales. GitHub limita cada archivo individual a 100 MB y no es adecuado para almacenar conjuntos de datos de este tamaño.

Antes de publicar, verificá que la licencia y las condiciones de uso de los datos permitan redistribuir los resultados incluidos. Si los CSV derivados tampoco se pueden publicar, compartilos por un medio autorizado y colocalos en las rutas indicadas antes de abrir el notebook.

## Publicar en Render o Railway

La aplicación independiente está en `app.py`; el dashboard conserva los gráficos y controles del notebook. Para desplegarlo, subí a un repositorio de GitHub estos archivos y carpetas:

- `app.py`, `requirements.txt`, `Procfile` y `.python-version`
- `assets/`
- `data/estaciones.geojson`
- Los seis CSV enumerados en «Archivos necesarios para el dashboard»

No incluyas los CSV originales ni las cachés. Los archivos derivados que necesita la aplicación ya están versionados en este repositorio. Revisá igualmente que su licencia permita publicarlos.

### Render

1. En Render, elegí **New → Blueprint** y conectá el repositorio de GitHub. Render leerá `render.yaml`, instalará los paquetes y levantará el servicio web.
2. Cuando el despliegue termine, abrí la URL `*.onrender.com` que Render muestra en el servicio y compartila con los profesores.

También se puede crear un **Web Service** manualmente con el comando de construcción `pip install -r requirements.txt` y el comando de inicio `gunicorn app:server --bind 0.0.0.0:$PORT`.

### Railway

1. En Railway, elegí **New Project → Deploy from GitHub Repo** y seleccioná el repositorio. Railway instalará las dependencias de `requirements.txt` y usará el comando web de `Procfile`.
2. En la configuración del servicio, habilitá la generación de un dominio público (**Settings → Networking → Generate Domain**). Compartí el dominio que Railway asigne.

El primer despliegue tarda unos minutos mientras se instalan las dependencias. En el plan gratuito de Render, el servicio puede suspenderse tras un período sin actividad; el primer acceso posterior puede demorar mientras vuelve a iniciar.
