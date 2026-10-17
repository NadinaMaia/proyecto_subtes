from pathlib import Path
import os
import re

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from dash import Dash, Input, Output, State, ctx, dcc, html, no_update

ROOT = Path(__file__).resolve().parent
if not (ROOT / 'data').is_dir() or not (ROOT / 'subte_fpca_work').is_dir():
    raise FileNotFoundError('No se encontró la raíz del proyecto (data y subte_fpca_work).')
OUTDIR = ROOT / 'subte_fpca_work' / 'resultados'
INTERVALO_MIN = 15
SEGMENTOS = ['Laborable', 'Sábado', 'Domingo/Feriado']
HORARIOS_HABITUALES = {
    'Laborable': (5*60 + 30, 23*60 + 30),
    'Sábado': (6*60, 23*60 + 45),
    'Domingo/Feriado': (8*60, 22*60),
}
COLORES_LINEA = {
    'A': '#00A7D1', 'B': '#E52421', 'C': '#0A67B5',
    'D': '#008C58', 'E': '#A6268E', 'H': '#FFD100',
}
ORDEN_ESTACIONES = {
    'A': ['PLAZA DE MAYO', 'PERU', 'PIEDRAS', 'LIMA', 'SAENZ PEÑA', 'CONGRESO', 'PASCO', 'ALBERTI', 'PLAZA MISERERE', 'LORIA', 'CASTRO BARROS', 'RIO DE JANEIRO', 'ACOYTE', 'PRIMERA JUNTA', 'PUAN', 'CARABOBO', 'FLORES', 'SAN PEDRITO'],
    'B': ['LEANDRO N. ALEM', 'FLORIDA', 'CARLOS PELLEGRINI', 'URUGUAY', 'CALLAO', 'PASTEUR', 'PUEYRREDON', 'CARLOS GARDEL', 'MEDRANO', 'ANGEL GALLARDO', 'MALABIA', 'DORREGO', 'FEDERICO LACROZE', 'TRONADOR', 'LOS INCAS', 'ECHEVERRIA', 'ROSAS'],
    'C': ['RETIRO', 'GENERAL SAN MARTIN', 'LAVALLE', 'DIAGONAL NORTE', 'AVENIDA DE MAYO', 'MARIANO MORENO', 'INDEPENDENCIA', 'SAN JUAN', 'CONSTITUCION'],
    'D': ['CATEDRAL', '9 DE JULIO', 'TRIBUNALES', 'CALLAO', 'FACULTAD DE MEDICINA', 'PUEYRREDON', 'AGÜERO', 'BULNES', 'SCALABRINI ORTIZ', 'PLAZA ITALIA', 'PALERMO', 'MINISTRO CARRANZA', 'OLLEROS', 'JOSE HERNANDEZ', 'JURAMENTO', 'CONGRESO DE TUCUMAN'],
    'E': ['RETIRO', 'CATALINAS', 'CORREO CENTRAL', 'BOLIVAR', 'GENERAL BELGRANO', 'INDEPENDENCIA', 'SAN JOSE', 'ENTRE RIOS', 'PICHINCHA', 'JUJUY', 'URQUIZA', 'BOEDO', 'AVENIDA LA PLATA', 'JOSE MARIA MORENO', 'EMILIO MITRE', 'MEDALLA MILAGROSA', 'VARELA', 'PZA. DE LOS VIRREYES'],
    'H': ['FACULTAD DE DERECHO', 'LAS HERAS', 'SANTA FE', 'CORDOBA', 'CORRIENTES', 'ONCE', 'VENEZUELA', 'HUMBERTO I', 'INCLAN', 'CASEROS', 'PATRICIOS', 'HOSPITALES'],
}
MAPA_CENTRO = {'lat': -34.610, 'lon': -58.410}
MAPA_ZOOM = 10.55
# Base OpenStreetMap deliberadamente desaturada: mantiene calles y barrios
# como contexto, sin competir visualmente con la red y la demanda.
MAPA_ESTILO_SUAVE = {
    'version': 8,
    'sources': {'osm-suave': {'type': 'raster', 'tiles': ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'], 'tileSize': 256,
                               'attribution': '© OpenStreetMap contributors'}},
    'layers': [
        {'id': 'fondo', 'type': 'background', 'paint': {'background-color': '#f7f8fa'}},
        {'id': 'osm-suave', 'type': 'raster', 'source': 'osm-suave',
         'paint': {'raster-opacity': .43, 'raster-saturation': -.78, 'raster-contrast': -.12, 'raster-brightness-max': .94}},
    ],
}
COLOR_TEXTO = '#183153'
COLOR_TEXTO_SEC = '#607086'
COLOR_FONDO = '#f3f6fa'
COLOR_PRIMARIO = '#24557a'
COLOR_ACENTO = '#0f766e'
ESCALA_INTENSIDAD = ['#fff7ec', '#fee8c8', '#fdbb84', '#fc8d59', '#e34a33', '#b30000']
PALETA_CATEGORICA = ['#0072B2', '#E69F00', '#009E73', '#CC79A7', '#56B4E9', '#D55E00', '#7A5195', '#4D4D4D']

def limites_horario(segmento):
    return HORARIOS_HABITUALES.get(segmento, (0, 23*60 + 45))

def es_horario_habitual(segmento, minuto):
    inicio, fin = limites_horario(segmento)
    return inicio <= int(minuto) <= fin

def marcas_horario(segmento):
    inicio, fin = limites_horario(segmento)
    candidatos = [inicio] + list(range(((inicio + 119) // 120) * 120, fin + 1, 120)) + [fin]
    return {int(m): f'{m//60:02d}:{m%60:02d}' for m in sorted(set(candidatos))}
PLOT_TEMPLATE = go.layout.Template(layout={
    'font': {'family': 'Inter, Arial, sans-serif', 'color': COLOR_TEXTO, 'size': 13},
    'paper_bgcolor': 'white', 'plot_bgcolor': 'white', 'colorway': PALETA_CATEGORICA,
    'title': {'font': {'size': 19, 'color': COLOR_TEXTO}, 'x': .02, 'xanchor': 'left'},
    'xaxis': {'gridcolor': '#e8eef5', 'zerolinecolor': '#d5dfeb', 'linecolor': '#c7d2df', 'automargin': True},
    'yaxis': {'gridcolor': '#e8eef5', 'zerolinecolor': '#d5dfeb', 'linecolor': '#c7d2df', 'automargin': True},
    'legend': {'bgcolor': 'rgba(255,255,255,.85)', 'bordercolor': '#dbe3ec', 'borderwidth': 1},
    'hoverlabel': {'bgcolor': '#102a43', 'font': {'color': 'white', 'family': 'Inter, Arial, sans-serif'}},
    'coloraxis': {'colorbar': {'outlinewidth': 0, 'tickfont': {'color': COLOR_TEXTO_SEC}}},
})

print('Resultados:', OUTDIR)

ARCHIVOS = {
    'metricas': OUTDIR / 'metricas_priorizacion_operativa.csv',
    'mapa': OUTDIR / 'mapa_estaciones_perfil_tipico.csv',
    'perfiles': OUTDIR / 'perfiles_suavizados_segmentados.csv',
    'scores': OUTDIR / 'scores_fpca_clusters_segmentados.csv',
    'diaria': OUTDIR / 'serie_diaria_red.csv',
    'geo_catalogo': OUTDIR / 'mapa_estaciones_georreferenciadas.csv',
    'geojson_oficial': ROOT / 'data' / 'estaciones.geojson',
}
faltantes = [str(p) for p in ARCHIVOS.values() if not p.exists()]
if faltantes:
    raise FileNotFoundError('Faltan resultados o insumos del dashboard:\n' + '\n'.join(faltantes))

def leer_puntos_geojson_rtf(ruta):
    """Lee el GeoJSON oficial incluso si macOS lo guardó accidentalmente como RTF."""
    texto = Path(ruta).read_text(encoding='latin1')
    filas = []
    for linea_txt in texto.splitlines():
        if '"type": "Feature"' not in linea_txt:
            continue
        limpia = re.sub(r"\\'([0-9a-fA-F]{2})", lambda m: bytes.fromhex(m.group(1)).decode('cp1252'), linea_txt)
        id_m = re.search(r'"id":\s*(\d+)', limpia)
        estacion_m = re.search(r'"estacion":\s*"([^"]+)"', limpia)
        linea_m = re.search(r'"linea":\s*"([^"]+)"', limpia)
        coord_m = re.search(r'"coordinates":\s*\[\s*([-\d.]+)\s*,\s*([-\d.]+)', limpia)
        if all([id_m, estacion_m, linea_m, coord_m]):
            filas.append({
                'id_oficial': int(id_m.group(1)), 'nombre_geojson': estacion_m.group(1), 'linea_geojson': linea_m.group(1),
                'longitud': float(coord_m.group(1)), 'latitud': float(coord_m.group(2)),
            })
    salida = pd.DataFrame(filas)
    if len(salida) != 90 or salida['id_oficial'].duplicated().any():
        raise ValueError(f'El archivo geográfico oficial no contiene 90 estaciones únicas: {ruta}')
    return salida

metricas = pd.read_csv(ARCHIVOS['metricas'])
perfiles = pd.read_csv(ARCHIVOS['perfiles'])
scores = pd.read_csv(ARCHIVOS['scores'])
diaria = pd.read_csv(ARCHIVOS['diaria'], parse_dates=['fecha'])
mapa = pd.read_csv(ARCHIVOS['mapa'], usecols=[
    'anio', 'segmento_dia', 'slot_min', 'linea', 'estacion', 'estacion_id',
    'pax_slot_mediano', 'pax_dia_tipico', 'participacion_estacion_pct', 'dias_utilizados',
    'latitud', 'longitud', 'nombre_oficial'
])
geo_catalogo = pd.read_csv(ARCHIVOS['geo_catalogo'], usecols=['linea', 'estacion', 'estacion_id', 'nombre_oficial', 'id_oficial'])
geo_oficial = leer_puntos_geojson_rtf(ARCHIVOS['geojson_oficial'])
estaciones_geo = geo_catalogo.merge(geo_oficial, on='id_oficial', how='inner', validate='one_to_one')
if len(estaciones_geo) != 90:
    raise ValueError('No fue posible vincular las 90 estaciones analíticas con el GeoJSON oficial')
mapa = mapa.drop(columns=['latitud', 'longitud', 'nombre_oficial']).merge(
    estaciones_geo[['estacion_id', 'latitud', 'longitud', 'nombre_oficial']], on='estacion_id', how='left', validate='many_to_one'
)

for df in [metricas, perfiles, scores, mapa]:
    df['anio'] = pd.to_numeric(df['anio'], errors='coerce').astype('Int64')
for df in [metricas, perfiles, scores]:
    if 'anio_parcial' in df:
        df['anio_parcial'] = df['anio_parcial'].astype(str).str.lower().isin(['true', '1'])

slot_cols = sorted([c for c in perfiles.columns if c.startswith('slot_')])
slot_min = np.array([int(c.split('_')[1]) for c in slot_cols])
slot_hora = np.array([f'{m//60:02d}:{m%60:02d}' for m in slot_min])

# Alcance del producto: operación habitual, no extensiones por eventos.
# Dentro de cada ventana se conserva todo el dato disponible, sin umbral
# adicional de cobertura; fuera de la ventana habitual se fuerza a cero.
mapa['en_horario_habitual'] = [es_horario_habitual(s, m) for s, m in zip(mapa['segmento_dia'], mapa['slot_min'])]
mapa['slot_tipico'] = mapa['en_horario_habitual']
mapa.loc[~mapa['slot_tipico'], 'pax_slot_mediano'] = 0.0
mapa['pax_dia_tipico'] = mapa.groupby(['anio', 'segmento_dia', 'estacion_id'], observed=True)['pax_slot_mediano'].transform('sum')
mapa['participacion_estacion_pct'] = np.where(mapa['pax_dia_tipico'].gt(0), 100 * mapa['pax_slot_mediano'] / mapa['pax_dia_tipico'], 0.0)

# Las curvas que alimentan heatmaps y perfiles respetan las mismas ventanas.
for segmento, (inicio, fin) in HORARIOS_HABITUALES.items():
    fuera = [c for c, m in zip(slot_cols, slot_min) if not (inicio <= m <= fin)]
    perfiles.loc[perfiles['segmento_dia'].eq(segmento), fuera] = 0.0
suma_forma = perfiles[slot_cols].sum(axis=1).replace(0, np.nan)
perfiles[slot_cols] = perfiles[slot_cols].div(suma_forma, axis=0).mul(100).fillna(0)
perfiles = perfiles.copy()  # compacta bloques internos después del ajuste de 96 slots

# Para volúmenes y rankings del dashboard se usa la suma habitual de medianas
# horarias. Se conserva el volumen original para trazabilidad.
volumen_habitual = mapa.groupby(['anio', 'segmento_dia', 'linea', 'estacion_id'], observed=True)['pax_slot_mediano'].sum().rename('pax_diarios_habitual').reset_index()
def aplicar_volumen_habitual(tabla):
    salida = tabla.merge(volumen_habitual.drop(columns='linea'), on=['anio', 'segmento_dia', 'estacion_id'], how='left', validate='one_to_one')
    salida['pax_diarios_mediana_original'] = salida['pax_diarios_mediana']
    salida['pax_diarios_mediana'] = salida['pax_diarios_habitual'].fillna(salida['pax_diarios_mediana'])
    return salida
metricas = aplicar_volumen_habitual(metricas)
perfiles = aplicar_volumen_habitual(perfiles)
scores = aplicar_volumen_habitual(scores)
if 'pax_pico_60_estimado' in metricas:
    metricas['pax_pico_60_estimado'] = metricas['pax_diarios_mediana'] * metricas['participacion_pico_60_pct'] / 100
anios = sorted(metricas['anio'].dropna().astype(int).unique().tolist())
anios_completos = sorted(metricas.loc[~metricas['anio_parcial'], 'anio'].dropna().astype(int).unique().tolist())
anio_principal_default = anios_completos[-1] if anios_completos else anios[-1]
anio_base_default = 2019 if 2019 in anios else anios[0]
lineas = sorted(metricas['linea'].dropna().astype(str).unique().tolist())
estaciones_validas = set(metricas['estacion_id'].dropna().astype(str)) | set(estaciones_geo['estacion_id'].dropna().astype(str))
orden_declarado = {f'{linea} | {estacion}' for linea, estaciones in ORDEN_ESTACIONES.items() for estacion in estaciones}
faltan_en_orden = sorted(set(estaciones_geo['estacion_id']) - orden_declarado)
if faltan_en_orden:
    raise ValueError('Faltan estaciones en ORDEN_ESTACIONES: ' + ', '.join(faltan_en_orden))

print(f'Métricas: {len(metricas):,} filas')
print(f'Mapa horario: {len(mapa):,} filas')
print(f'Perfiles: {len(perfiles):,} | Scores FPCA: {len(scores):,}')
print(f'Años: {anios[0]}–{anios[-1]} | Año principal inicial: {anio_principal_default}')

CARD_STYLE = {
    'background': 'white', 'border': '1px solid #dce5ef', 'borderRadius': '14px',
    'padding': '16px 18px', 'boxShadow': '0 6px 18px rgba(31,55,85,.07)',
    'minHeight': '108px',
}
PANEL_STYLE = {
    'background': 'white', 'border': '1px solid #dce5ef', 'borderRadius': '16px',
    'padding': '12px', 'boxShadow': '0 8px 24px rgba(31,55,85,.065)',
}
TAB_STYLE = {'padding': '13px 18px', 'fontWeight': 600, 'color': COLOR_TEXTO_SEC, 'background': '#eef3f8', 'border': 'none'}
TAB_SELECTED_STYLE = {**TAB_STYLE, 'color': COLOR_PRIMARIO, 'background': 'white', 'borderTop': f'3px solid {COLOR_ACENTO}'}

def color_texto_linea(linea):
    return '#111111' if str(linea) == 'H' else 'white'

def insignia_linea(linea, tamanio=34):
    return html.Div(str(linea), title=f'Línea {linea}', style={
        'width': f'{tamanio}px', 'height': f'{tamanio}px', 'borderRadius': '50%',
        'display': 'inline-flex', 'alignItems': 'center', 'justifyContent': 'center',
        'background': COLORES_LINEA[str(linea)], 'color': color_texto_linea(linea),
        'fontWeight': 800, 'fontSize': f'{int(tamanio * .58)}px', 'border': 'none',
        'boxShadow': 'none', 'lineHeight': 1,
    })

def etiqueta_linea(linea, tamanio=30):
    return html.Div([insignia_linea(linea, tamanio), html.Span(f'Línea {linea}')],
                    style={'display': 'flex', 'alignItems': 'center', 'gap': '9px'})

def marca_demanda_subte():
    return html.Img(src='/assets/demanda-subte.png', alt='Demanda Subte — Buenos Aires Ciudad',
                    style={'width': '126px', 'height': '126px', 'minWidth': '126px', 'objectFit': 'contain',
                           'filter': 'drop-shadow(0 7px 10px rgba(17,17,17,.16))'})

def filtrar_lineas(df, seleccion):
    if not seleccion:
        return df.iloc[0:0].copy()
    return df[df['linea'].astype(str).isin([str(x) for x in seleccion])].copy()

def filtrar_estaciones(df, seleccion):
    if seleccion is None:
        return df.copy()
    return df[df['estacion_id'].astype(str).isin([str(x) for x in seleccion])].copy()

def combinar_selecciones(selecciones_por_grafico):
    activas = [set(v) for v in (selecciones_por_grafico or {}).values() if v]
    if not activas:
        return None
    return sorted(set.intersection(*activas))

def es_reset_vista(relayout, grafico_id):
    if not relayout:
        return False
    if any(str(k).endswith('.autorange') and v is True for k, v in relayout.items()):
        return True
    if grafico_id == 'mapa-graph':
        zoom = relayout.get('map.zoom', relayout.get('mapbox.zoom'))
        centro = relayout.get('map.center', relayout.get('mapbox.center', {})) or {}
        return (zoom is not None and abs(float(zoom) - MAPA_ZOOM) < .05 and
                abs(float(centro.get('lat', 0)) - MAPA_CENTRO['lat']) < .01 and
                abs(float(centro.get('lon', 0)) - MAPA_CENTRO['lon']) < .01)
    return False

def estaciones_desde_evento(evento):
    """Extrae estaciones de selectedData/clickData de cualquiera de los gráficos vinculados."""
    estaciones = []
    for punto in (evento or {}).get('points', []):
        custom = punto.get('customdata')
        candidato = custom[0] if isinstance(custom, (list, tuple, np.ndarray)) and len(custom) else punto.get('y', punto.get('hovertext'))
        candidatos = candidato if isinstance(candidato, (list, tuple, np.ndarray)) else [candidato]
        estaciones.extend(str(x) for x in candidatos if x is not None and str(x) in estaciones_validas)
    return sorted(set(estaciones))

def figura_vacia(mensaje='No hay datos para los filtros seleccionados'):
    fig = go.Figure()
    fig.add_annotation(text=mensaje, x=.5, y=.5, xref='paper', yref='paper', showarrow=False, font={'size': 16})
    fig.update_layout(template=PLOT_TEMPLATE, xaxis={'visible': False}, yaxis={'visible': False}, margin={'l': 20, 'r': 20, 't': 45, 'b': 20})
    return fig

def fmt_pax(valor):
    if valor is None or not np.isfinite(valor):
        return '—'
    if valor >= 1_000_000:
        return f'{valor/1_000_000:.2f} M'
    if valor >= 1_000:
        return f'{valor/1_000:.1f} mil'
    return f'{valor:,.0f}'

def card(titulo, valor, detalle='', acento=COLOR_PRIMARIO):
    estilo = dict(CARD_STYLE)
    estilo['borderTop'] = f'4px solid {acento}'
    return html.Div([
        html.Div(titulo.upper(), style={'fontSize': '11px', 'fontWeight': 700, 'letterSpacing': '.065em', 'color': COLOR_TEXTO_SEC}),
        html.Div(valor, style={'fontSize': '25px', 'fontWeight': 750, 'color': COLOR_TEXTO, 'margin': '6px 0'}),
        html.Div(detalle, style={'fontSize': '12px', 'lineHeight': 1.4, 'color': COLOR_TEXTO_SEC}),
    ], style=estilo)

def perfiles_filtrados(segmento, anio, seleccion_lineas, seleccion_estaciones=None):
    d = perfiles[(perfiles['segmento_dia'] == segmento) & (perfiles['anio'] == int(anio))]
    return filtrar_estaciones(filtrar_lineas(d, seleccion_lineas), seleccion_estaciones)

def metricas_filtradas(segmento, anio, seleccion_lineas, seleccion_estaciones=None):
    d = metricas[(metricas['segmento_dia'] == segmento) & (metricas['anio'] == int(anio))]
    return filtrar_estaciones(filtrar_lineas(d, seleccion_lineas), seleccion_estaciones)

def calcular_tarjetas(segmento, anio, anio_base, seleccion_lineas, seleccion_estaciones=None):
    d = volumen_habitual[(volumen_habitual['segmento_dia'] == segmento) & (volumen_habitual['anio'] == int(anio))].copy()
    d = filtrar_estaciones(filtrar_lineas(d, seleccion_lineas), seleccion_estaciones)
    if d.empty:
        return [card('Sin datos', '—', 'Revisá los filtros', '#a61c3c')]
    total = float(d['pax_diarios_habitual'].sum())
    por_linea = d.groupby('linea', observed=True)['pax_diarios_habitual'].sum().sort_values(ascending=False)
    por_estacion = d.groupby('estacion_id', observed=True)['pax_diarios_habitual'].sum().sort_values(ascending=False)
    mayor_l, menor_l = str(por_linea.index[0]), str(por_linea.index[-1])
    mayor_e = str(por_estacion.index[0])
    n_l80 = int((por_linea.cumsum() / total < .80).sum() + 1)
    n_e80 = int((por_estacion.cumsum() / total < .80).sum() + 1)

    dp = mapa[(mapa['segmento_dia'] == segmento) & (mapa['anio'] == int(anio))].copy()
    dp = filtrar_estaciones(filtrar_lineas(dp, seleccion_lineas), seleccion_estaciones)
    if dp.empty:
        hora_red, pax_hora = '—', np.nan
    else:
        red = dp.groupby('slot_min', observed=True)['pax_slot_mediano'].sum().reindex(slot_min, fill_value=0).to_numpy(float)
        n60 = max(1, int(round(60 / INTERVALO_MIN)))
        ventanas = np.lib.stride_tricks.sliding_window_view(red, n60).sum(axis=-1)
        ip = int(np.argmax(ventanas))
        hora_red, pax_hora = slot_hora[ip], float(ventanas[ip])

    db = volumen_habitual[(volumen_habitual['segmento_dia'] == segmento) & (volumen_habitual['anio'] == int(anio_base))].copy()
    db = filtrar_estaciones(filtrar_lineas(db, seleccion_lineas), seleccion_estaciones)
    total_base = float(db['pax_diarios_habitual'].sum()) if not db.empty else np.nan
    cambio = total / total_base - 1 if np.isfinite(total_base) and total_base > 0 else np.nan
    parcial = int(anio) not in anios_completos
    return [
        card('Tráfico diario típico', fmt_pax(total), f'{segmento.lower()} · {anio}' + (' · parcial' if parcial else ''), COLOR_PRIMARIO),
        card('Hora pico de la red', hora_red, f'{fmt_pax(pax_hora)} pasajeros estimados en 60 min', COLOR_ACENTO),
        card('Línea con mayor uso', etiqueta_linea(mayor_l), f'{por_linea.iloc[0]/total:.1%} del tráfico · {fmt_pax(float(por_linea.iloc[0]))}', COLORES_LINEA[mayor_l]),
        card('Línea con menor uso', etiqueta_linea(menor_l), f'{por_linea.iloc[-1]/total:.1%} del tráfico · {fmt_pax(float(por_linea.iloc[-1]))}', COLORES_LINEA[menor_l]),
        card('Estación principal', mayor_e, f'{por_estacion.iloc[0]/total:.1%} del tráfico · {fmt_pax(float(por_estacion.iloc[0]))}', '#2c7da0'),
        card('Concentración por líneas', f'{n_l80} líneas', 'Reúnen al menos 80% del tráfico típico', COLOR_ACENTO),
        card('Concentración por estaciones', f'{n_e80} estaciones', 'Reúnen al menos 80% del tráfico típico', COLOR_ACENTO),
        card('Cambio contra año base', '—' if not np.isfinite(cambio) else f'{cambio:+.1%}', f'{anio_base} → {anio}', '#15803d' if np.isfinite(cambio) and cambio >= 0 else '#b91c1c'),
    ]

def grafico_mapa(segmento, anio, seleccion_lineas, minuto, seleccion_estaciones=None):
    base = filtrar_lineas(estaciones_geo, seleccion_lineas).dropna(subset=['latitud', 'longitud']).copy()
    universo = mapa[(mapa['segmento_dia'] == segmento) & (mapa['anio'] == int(anio))]
    universo = filtrar_lineas(universo, seleccion_lineas)
    datos_hora = universo[universo['slot_min'] == int(minuto)][['estacion_id', 'pax_slot_mediano', 'participacion_estacion_pct', 'dias_utilizados']]
    totales = universo.groupby('estacion_id', observed=True)['pax_dia_tipico'].max().rename('pax_dia_tipico').reset_index()
    contexto = base.merge(totales, on='estacion_id', how='left', validate='one_to_one').merge(datos_hora, on='estacion_id', how='left', validate='one_to_one')
    contexto[['pax_slot_mediano', 'pax_dia_tipico', 'participacion_estacion_pct', 'dias_utilizados']] = contexto[['pax_slot_mediano', 'pax_dia_tipico', 'participacion_estacion_pct', 'dias_utilizados']].fillna(0)
    if contexto.empty:
        return figura_vacia('No hay datos geográficos para esta hora')
    fig = go.Figure()

    # Trazado oficial: las coordenadas provienen del GeoJSON aportado y se
    # conectan según el orden ferroviario real de cada línea.
    for linea in [x for x in lineas if x in seleccion_lineas]:
        ruta = estaciones_geo[estaciones_geo['linea'] == linea].set_index('estacion').reindex(ORDEN_ESTACIONES[linea]).dropna(subset=['latitud', 'longitud'])
        fig.add_trace(go.Scattermap(
            lat=ruta['latitud'], lon=ruta['longitud'], mode='lines',
            line={'color': COLORES_LINEA[linea], 'width': 5}, opacity=.78,
            hoverinfo='skip', showlegend=True, name=f'Línea {linea}',
        ))

    # La escala es común a todas las horas del año/segmento: los volúmenes
    # pequeños ya no se agrandan artificialmente durante la madrugada.
    vmax = max(float(universo.loc[universo['slot_tipico'], 'pax_slot_mediano'].quantile(.99)), 1.0)
    vmax_intensidad = max(float(universo.loc[universo['slot_tipico'], 'participacion_estacion_pct'].quantile(.99)), .1)
    sizeref = 2 * vmax / 31**2
    escala_intensidad_mostrada = False
    seleccion_set = None if seleccion_estaciones is None else set(seleccion_estaciones)
    for linea in [x for x in lineas if x in seleccion_lineas]:
        g = contexto[contexto['linea'] == linea].copy()
        if g.empty:
            continue
        # Nodo pequeño = ubicación de la estación; no representa demanda.
        capas_base = [(g, .52)] if seleccion_set is None else [(g, .12), (g[g['estacion_id'].isin(seleccion_set)], 1.0)]
        for puntos, opacidad in capas_base:
            if puntos.empty:
                continue
            custom = puntos[['estacion_id', 'linea', 'pax_slot_mediano', 'pax_dia_tipico', 'participacion_estacion_pct', 'nombre_oficial', 'dias_utilizados']].to_numpy()
            fig.add_trace(go.Scattermap(
                lat=puntos['latitud'], lon=puntos['longitud'], mode='markers', customdata=custom,
                marker={'size': 7, 'color': COLORES_LINEA[linea], 'opacity': opacidad},
                showlegend=False, name=f'Estaciones {linea}',
                hovertemplate='<b>%{customdata[5]}</b><br>Línea %{customdata[1]}<br>Pasajeros típicos del intervalo: %{customdata[2]:,.0f}<br>Tráfico diario habitual: %{customdata[3]:,.0f}<br>Intervalo / día habitual: %{customdata[4]:.2f}%<br>Días con dato en el intervalo: %{customdata[6]:,.0f}<extra></extra>',
            ))
        demanda = g[g['pax_slot_mediano'] > 0].copy()
        capas_demanda = [(demanda, .78)] if seleccion_set is None else [(demanda, .14), (demanda[demanda['estacion_id'].isin(seleccion_set)], .94)]
        for puntos, opacidad in capas_demanda:
            if puntos.empty:
                continue
            custom = puntos[['estacion_id', 'linea', 'pax_slot_mediano', 'pax_dia_tipico', 'participacion_estacion_pct', 'nombre_oficial', 'dias_utilizados']].to_numpy()
            # Anillo exterior: conserva el código categórico de la línea.
            fig.add_trace(go.Scattermap(
                lat=puntos['latitud'], lon=puntos['longitud'], mode='markers', customdata=custom,
                marker={'size': puntos['pax_slot_mediano'], 'sizemode': 'area', 'sizeref': sizeref, 'sizemin': 8,
                        'color': COLORES_LINEA[linea], 'opacity': opacidad},
                showlegend=False, name=f'Demanda {linea}',
                hovertemplate='<b>%{customdata[5]}</b><br>Línea %{customdata[1]}<br>Pasajeros típicos del intervalo: %{customdata[2]:,.0f}<br>Tráfico diario habitual: %{customdata[3]:,.0f}<br>Intervalo / día habitual: %{customdata[4]:.2f}%<br>Días con dato en el intervalo: %{customdata[6]:,.0f}<extra></extra>',
            ))
            # Relleno: escala secuencial, común a todas las horas, que indica
            # qué proporción del día típico de esa estación ocurre en este slot.
            fig.add_trace(go.Scattermap(
                lat=puntos['latitud'], lon=puntos['longitud'], mode='markers', customdata=custom,
                marker={'size': puntos['pax_slot_mediano'] * .64, 'sizemode': 'area', 'sizeref': sizeref, 'sizemin': 6,
                        'color': puntos['participacion_estacion_pct'], 'colorscale': ESCALA_INTENSIDAD,
                        'cmin': 0, 'cmax': vmax_intensidad, 'opacity': opacidad,
                        'showscale': not escala_intensidad_mostrada,
                        'colorbar': {'title': '% del día', 'outlinewidth': 0, 'x': 1.01, 'len': .70}},
                showlegend=False, name=f'Intensidad {linea}',
                hovertemplate='<b>%{customdata[5]}</b><br>Línea %{customdata[1]}<br>Pasajeros típicos del intervalo: %{customdata[2]:,.0f}<br>Tráfico diario habitual: %{customdata[3]:,.0f}<br>Intervalo / día habitual: %{customdata[4]:.2f}%<br>Días con dato en el intervalo: %{customdata[6]:,.0f}<extra></extra>',
            ))
            escala_intensidad_mostrada = True

    seleccion_visible = filtrar_estaciones(contexto, seleccion_estaciones)
    if seleccion_estaciones is not None and not seleccion_visible.empty:
        fig.add_annotation(text=f'{len(seleccion_visible)} estación(es) seleccionada(s)', x=.01, y=.99, xref='paper', yref='paper', showarrow=False,
                           bgcolor='rgba(255,209,0,.92)', bordercolor='#111111', borderwidth=1, font={'color': '#111111', 'size': 12})
    elif seleccion_estaciones == []:
        fig.add_annotation(text='Sin coincidencias entre selecciones activas', x=.5, y=.98, xref='paper', yref='paper', showarrow=False,
                           bgcolor='rgba(255,255,255,.92)', bordercolor='#b30000', font={'color': '#8b0000'})

    fig.update_layout(
        template=PLOT_TEMPLATE, height=650, dragmode='lasso', clickmode='event+select', uirevision='seleccion-estaciones',
        map={'style': MAPA_ESTILO_SUAVE, 'center': MAPA_CENTRO, 'zoom': MAPA_ZOOM},
        legend={'title': {'text': 'Líneas'}, 'orientation': 'h', 'x': .01, 'y': .01, 'bgcolor': 'rgba(255,255,255,.9)'},
        title=f'Red de Subte y demanda — {slot_hora[np.argmin(np.abs(slot_min-int(minuto)))]} · {segmento}, {anio}',
        margin={'l': 0, 'r': 12, 't': 55, 'b': 0},
    )
    return fig

def grafico_heatmap(segmento, anio, seleccion_lineas, seleccion_estaciones=None, n=30, minuto=None):
    d = metricas_filtradas(segmento, anio, seleccion_lineas, seleccion_estaciones)
    if d.empty:
        return figura_vacia()
    ids = d.nlargest(n, 'pax_diarios_mediana')['estacion_id'].tolist()
    p = perfiles_filtrados(segmento, anio, seleccion_lineas, seleccion_estaciones).set_index('estacion_id').reindex(ids).dropna(how='all', subset=slot_cols)
    if p.empty:
        return figura_vacia()
    orden = p[slot_cols].to_numpy(float).argmax(axis=1).argsort()
    p = p.iloc[orden]
    fig = go.Figure(go.Heatmap(z=p[slot_cols].to_numpy(float), x=slot_hora, y=p.index, colorscale=ESCALA_INTENSIDAD, colorbar={'title': '% diario', 'outlinewidth': 0},
        hovertemplate='<b>%{y}</b><br>Hora: %{x}<br>Participación: %{z:.2f}%<extra></extra>'))
    fig.update_layout(template=PLOT_TEMPLATE, height=590, title=f'Top {len(p)} estaciones por volumen', margin={'l': 150, 'r': 55, 't': 55, 'b': 55})
    fig.update_xaxes(tickmode='array', tickvals=slot_hora[::8], ticktext=slot_hora[::8], title='Hora')
    if minuto is not None:
        hora_activa = slot_hora[np.argmin(np.abs(slot_min - int(minuto)))]
        fig.add_vline(x=hora_activa, line_width=2, line_dash='dash', line_color='#111111', opacity=.8)
    return fig

def grafico_presion(segmento, anio, seleccion_lineas, seleccion_estaciones=None):
    d = metricas_filtradas(segmento, anio, seleccion_lineas, seleccion_estaciones).dropna(subset=['pax_diarios_mediana', 'participacion_pico_60_pct'])
    if d.empty:
        return figura_vacia()
    fig = px.scatter(
        d, x='participacion_pico_60_pct', y='pax_diarios_mediana', size='pax_pico_60_estimado',
        color='indice_presion_demanda', color_continuous_scale=ESCALA_INTENSIDAD, size_max=38,
        hover_name='estacion_id', custom_data=['estacion_id', 'hora_pico_60_txt', 'duracion_pico_min', 'accion_preliminar'],
        labels={'participacion_pico_60_pct': 'Participación de la hora pico (%)', 'pax_diarios_mediana': 'Pasajeros diarios típicos', 'indice_presion_demanda': 'Índice'},
    )
    fig.update_traces(hovertemplate='<b>%{hovertext}</b><br>Volumen diario: %{y:,.0f}<br>Participación pico: %{x:.1f}%<br>Hora pico: %{customdata[1]}<br>Duración: %{customdata[2]:.0f} min<br>%{customdata[3]}<extra></extra>')
    fig.update_layout(template=PLOT_TEMPLATE, height=520, dragmode='lasso', clickmode='event+select', uirevision='seleccion-estaciones', title='Matriz de presión de demanda', margin={'l': 65, 'r': 35, 't': 55, 'b': 55})
    return fig

def grafico_evolucion(segmento, anio_base, anio, seleccion_lineas, seleccion_estaciones=None):
    lo, hi = sorted([int(anio_base), int(anio)])
    d = volumen_habitual[(volumen_habitual['segmento_dia'] == segmento) & volumen_habitual['anio'].between(lo, hi)]
    d = filtrar_estaciones(filtrar_lineas(d, seleccion_lineas), seleccion_estaciones)
    if d.empty:
        return figura_vacia()
    a = d.groupby('anio', observed=True)['pax_diarios_habitual'].sum().reset_index(name='trafico_tipico')
    fig = px.scatter(d, x='anio', y='pax_diarios_habitual', custom_data=['estacion_id'], labels={'anio': 'Año', 'pax_diarios_habitual': 'Pasajeros diarios habituales'})
    fig.update_traces(name='Estaciones', marker={'size': 7, 'color': '#6baed6', 'opacity': .38, 'line': {'color': 'white', 'width': .5}}, hovertemplate='<b>%{customdata[0]}</b><br>Año: %{x}<br>Tráfico diario típico: %{y:,.0f}<extra></extra>')
    fig.add_trace(go.Scatter(x=a['anio'], y=a['trafico_tipico'], mode='lines+markers', name='Total seleccionado', line={'color': COLOR_PRIMARIO, 'width': 3}, marker={'size': 8, 'color': COLOR_PRIMARIO}, hovertemplate='Año: %{x}<br>Total típico: %{y:,.0f}<extra></extra>'))
    fig.add_vrect(x0=2020, x1=2021, fillcolor='#7aa6c2', opacity=.13, line_width=0)
    fig.update_layout(template=PLOT_TEMPLATE, height=520, dragmode='lasso', clickmode='event+select', uirevision='seleccion-estaciones', title='Evolución del tráfico habitual · seleccioná puntos de estaciones', margin={'l': 65, 'r': 25, 't': 55, 'b': 55})
    return fig

def grafico_duracion(segmento, anio, seleccion_lineas, seleccion_estaciones=None, n=30):
    d = metricas_filtradas(segmento, anio, seleccion_lineas, seleccion_estaciones).nlargest(n, 'indice_presion_demanda').sort_values('duracion_pico_min')
    if d.empty:
        return figura_vacia()
    fig = px.bar(d, x='duracion_pico_min', y='estacion_id', orientation='h', color='participacion_pico_60_pct', color_continuous_scale=ESCALA_INTENSIDAD,
        custom_data=['estacion_id', 'hora_pico_60_txt', 'pax_diarios_mediana', 'indice_presion_demanda'],
        labels={'duracion_pico_min': 'Duración continua ≥80% del máximo (min)', 'estacion_id': 'Estación', 'participacion_pico_60_pct': '% del día en la mejor hora'})
    fig.update_traces(hovertemplate='<b>%{y}</b><br>Duración continua ≥80% del máximo: %{x:.0f} min<br>Mejor ventana de 60 min: %{customdata[1]}<br>Porcentaje del día en esa hora: %{marker.color:.1f}%<br>Volumen diario: %{customdata[2]:,.0f}<br>Índice de presión: %{customdata[3]:.1f}<extra></extra>')
    fig.update_layout(template=PLOT_TEMPLATE, height=650, dragmode='select', clickmode='event+select', uirevision='seleccion-estaciones', title=f'Duración del pico — top {len(d)} por presión', margin={'l': 175, 'r': 30, 't': 55, 'b': 55})
    return fig

def grafico_comparacion_picos(segmento, anio, seleccion_lineas, seleccion_estaciones=None, n=12):
    d = metricas_filtradas(segmento, anio, seleccion_lineas, seleccion_estaciones).dropna(subset=['duracion_pico_min', 'pax_pico_60_estimado']).copy()
    if d.empty:
        return figura_vacia()
    # El pico extendido es temporal; el pico intenso se mide en pasajeros
    # estimados durante la mejor ventana consecutiva de 60 minutos.
    extendido = d.nlargest(n, 'duracion_pico_min').sort_values('duracion_pico_min')
    intenso = d.nlargest(n, 'pax_pico_60_estimado').sort_values('pax_pico_60_estimado')
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=.20,
        subplot_titles=(f'Top {len(extendido)} · pico más extendido', f'Top {len(intenso)} · pico más intenso'))
    custom_ext = extendido[['estacion_id', 'hora_pico_60_txt', 'pax_pico_60_estimado', 'participacion_pico_60_pct']].to_numpy()
    custom_int = intenso[['estacion_id', 'hora_pico_60_txt', 'duracion_pico_min', 'participacion_pico_60_pct']].to_numpy()
    fig.add_trace(go.Bar(x=extendido['duracion_pico_min'], y=extendido['estacion_id'], orientation='h',
        customdata=custom_ext, marker={'color': '#2b6cb0'}, name='Pico extendido',
        hovertemplate='<b>%{y}</b><br>Racha ≥80% del máximo: %{x:.0f} min<br>Mejor hora: %{customdata[1]}<br>Pasajeros en esa hora: %{customdata[2]:,.0f}<br>Concentración: %{customdata[3]:.1f}% del día<extra></extra>'), row=1, col=1)
    fig.add_trace(go.Bar(x=intenso['pax_pico_60_estimado'], y=intenso['estacion_id'], orientation='h',
        customdata=custom_int, marker={'color': '#d95f02'}, name='Pico intenso',
        hovertemplate='<b>%{y}</b><br>Pasajeros en su mejor hora: %{x:,.0f}<br>Mejor hora: %{customdata[1]}<br>Racha ≥80% del máximo: %{customdata[2]:.0f} min<br>Concentración: %{customdata[3]:.1f}% del día<extra></extra>'), row=1, col=2)
    fig.update_xaxes(title='Duración continua (min)', row=1, col=1)
    fig.update_xaxes(title='Pasajeros típicos en la mejor hora', row=1, col=2)
    fig.update_yaxes(title='Estación', row=1, col=1)
    fig.update_layout(template=PLOT_TEMPLATE, height=560, dragmode='select', clickmode='event+select', uirevision='seleccion-estaciones',
        title=f'Pico extendido vs. pico intenso — {segmento}, {anio}', showlegend=False, margin={'l': 175, 'r': 30, 't': 75, 'b': 55})
    return fig

def grafico_perfil_estacion(estacion_id, segmento, anio_base, anio, minuto=None):
    if not estacion_id:
        return figura_vacia('Elegí una estación')
    d = perfiles[(perfiles['estacion_id'] == estacion_id) & (perfiles['segmento_dia'] == segmento) & perfiles['anio'].isin([int(anio_base), int(anio)])]
    if d.empty:
        return figura_vacia()
    filas = []
    for r in d.itertuples(index=False):
        vals = np.asarray([getattr(r, c) for c in slot_cols], dtype=float)
        filas.append(pd.DataFrame({'hora': slot_hora, 'participacion': vals, 'anio': str(int(r.anio)), 'estacion_id': estacion_id}))
    largo = pd.concat(filas, ignore_index=True)
    fig = px.line(largo, x='hora', y='participacion', color='anio', custom_data=['estacion_id'], color_discrete_sequence=[COLOR_PRIMARIO, '#d95f0e'], labels={'participacion': '% diario', 'hora': 'Hora', 'anio': 'Año'})
    fig.update_traces(line={'width': 3}, hovertemplate='<b>%{customdata[0]}</b><br>Hora: %{x}<br>Participación: %{y:.2f}%<extra></extra>')
    fig.update_layout(template=PLOT_TEMPLATE, height=460, dragmode='select', clickmode='event+select', uirevision='detalle-estacion', title=f'Perfil horario — {estacion_id}', margin={'l': 55, 'r': 25, 't': 55, 'b': 55})
    fig.update_xaxes(tickmode='array', tickvals=slot_hora[::8], ticktext=slot_hora[::8])
    if minuto is not None:
        hora_activa = slot_hora[np.argmin(np.abs(slot_min - int(minuto)))]
        fig.add_vline(x=hora_activa, line_width=2, line_dash='dash', line_color='#111111', opacity=.8)
    return fig

def grafico_historia_estacion(estacion_id, segmento):
    if not estacion_id:
        return figura_vacia('Elegí una estación')
    d = metricas[(metricas['estacion_id'] == estacion_id) & (metricas['segmento_dia'] == segmento)].sort_values('anio')
    if d.empty:
        return figura_vacia()
    fig = make_subplots(specs=[[{'secondary_y': True}]])
    custom = np.asarray([[estacion_id]] * len(d), dtype=object)
    fig.add_trace(go.Scatter(x=d['anio'], y=d['pax_diarios_mediana'], customdata=custom, mode='lines+markers', name='Tráfico diario típico', line={'color': '#24466f', 'width': 3}), secondary_y=False)
    fig.add_trace(go.Scatter(x=d['anio'], y=d['participacion_pico_60_pct'], customdata=custom, mode='lines+markers', name='Participación pico', line={'color': '#e45756', 'width': 2}), secondary_y=True)
    fig.update_yaxes(title_text='Pasajeros diarios típicos', secondary_y=False)
    fig.update_yaxes(title_text='Participación pico 60 min (%)', secondary_y=True)
    fig.update_layout(template=PLOT_TEMPLATE, height=460, dragmode='select', clickmode='event+select', uirevision='detalle-estacion', title='Evolución de volumen y concentración', legend={'orientation': 'h', 'y': -0.18}, margin={'l': 65, 'r': 65, 't': 55, 'b': 65})
    return fig

def tarjetas_estacion(estacion_id, segmento, anio):
    d = metricas[(metricas['estacion_id'] == estacion_id) & (metricas['segmento_dia'] == segmento) & (metricas['anio'] == int(anio))]
    if d.empty:
        return [card('Estación', estacion_id or '—', 'Sin datos para el año seleccionado')]
    r = d.iloc[0]
    return [
        card('Volumen diario típico', fmt_pax(float(r.pax_diarios_mediana)), f'{segmento.lower()} · {anio}'),
        card('Hora pico', str(r.hora_pico_60_txt), f'{float(r.participacion_pico_60_pct):.1f}% del día en 60 min', COLOR_ACENTO),
        card('Duración del pico', f'{float(r.duracion_pico_min):.0f} min', 'Racha continua ≥80% del máximo puntual', '#3f7cac'),
        card('Índice de presión', f'{float(r.indice_presion_demanda):.1f}', str(r.accion_preliminar), '#d95f0e'),
    ]

def grafico_trayectorias(segmento, anio_base, anio, seleccion_lineas, seleccion_estaciones=None):
    lo, hi = sorted([int(anio_base), int(anio)])
    d = scores[(scores['segmento_dia'] == segmento) & scores['anio'].between(lo, hi)]
    d = filtrar_estaciones(filtrar_lineas(d, seleccion_lineas), seleccion_estaciones).dropna(subset=['FPC1', 'FPC2'])
    if d.empty:
        return figura_vacia()
    conteo = d.groupby('estacion_id')['anio'].nunique().sort_values(ascending=False)
    if len(conteo) > 30:
        d = d[d['estacion_id'].isin(conteo.head(30).index)]
        sufijo = ' · 30 estaciones con mayor continuidad'
    else:
        sufijo = ''
    fig = px.line(d.sort_values(['estacion_id', 'anio']), x='FPC1', y='FPC2', color='estacion_id', markers=True, hover_name='estacion_id', custom_data=['estacion_id', 'anio', 'cluster_id'], color_discrete_sequence=PALETA_CATEGORICA)
    fig.update_layout(template=PLOT_TEMPLATE, height=590, dragmode='lasso', clickmode='event+select', uirevision='seleccion-estaciones', title=f'Trayectorias FPCA — {segmento}{sufijo}', showlegend=False, margin={'l': 60, 'r': 25, 't': 55, 'b': 55})
    return fig

def grafico_composicion_clusters(segmento, anio_base, anio, seleccion_lineas, seleccion_estaciones=None):
    lo, hi = sorted([int(anio_base), int(anio)])
    d = scores[(scores['segmento_dia'] == segmento) & scores['anio'].between(lo, hi)]
    d = filtrar_estaciones(filtrar_lineas(d, seleccion_lineas), seleccion_estaciones)
    if d.empty:
        return figura_vacia()
    c = d.groupby(['anio', 'cluster_id'], observed=True).agg(
        n=('estacion_id', 'size'), estaciones=('estacion_id', lambda x: sorted(set(x.astype(str))))
    ).reset_index()
    c['proporcion'] = c.groupby('anio')['n'].transform(lambda x: x / x.sum())
    fig = px.bar(c, x='anio', y='proporcion', color='cluster_id', barmode='stack', custom_data=['estaciones', 'n'], color_discrete_sequence=PALETA_CATEGORICA, labels={'proporcion': 'Proporción', 'anio': 'Año', 'cluster_id': 'Cluster'})
    fig.update_traces(hovertemplate='Año: %{x}<br>Proporción: %{y:.1%}<br>Estaciones: %{customdata[1]}<extra></extra>')
    fig.update_layout(template=PLOT_TEMPLATE, height=450, dragmode='select', clickmode='event+select', uirevision='seleccion-estaciones', title='Composición anual de clusters', yaxis_tickformat='.0%', margin={'l': 55, 'r': 25, 't': 55, 'b': 55})
    return fig

def grafico_perfiles_cluster(segmento, anio, seleccion_lineas, seleccion_estaciones=None, minuto=None):
    d = perfiles_filtrados(segmento, anio, seleccion_lineas, seleccion_estaciones)
    if d.empty:
        return figura_vacia()
    fig = go.Figure()
    for cluster, g in d.groupby('cluster_id', observed=True):
        arr = g[slot_cols].to_numpy(float)
        med, p10, p90 = np.median(arr, axis=0), np.quantile(arr, .10, axis=0), np.quantile(arr, .90, axis=0)
        miembros = sorted(g['estacion_id'].astype(str).unique().tolist())
        custom = [[miembros] for _ in slot_hora]
        color = PALETA_CATEGORICA[len(fig.data) // 3 % len(PALETA_CATEGORICA)]
        fig.add_trace(go.Scatter(x=slot_hora, y=p90, mode='lines', line={'width': 0}, showlegend=False, hoverinfo='skip'))
        fig.add_trace(go.Scatter(x=slot_hora, y=p10, mode='lines', line={'width': 0}, fill='tonexty', fillcolor='rgba(120,140,160,.13)', showlegend=False, hoverinfo='skip'))
        fig.add_trace(go.Scatter(x=slot_hora, y=med, customdata=custom, mode='lines', name=f'{cluster} (n={len(g)})', line={'width': 3, 'color': color}, hovertemplate=f'<b>{cluster}</b><br>Hora: %{{x}}<br>Mediana: %{{y:.2f}}%<br>Estaciones: {len(miembros)}<extra></extra>'))
    fig.update_layout(template=PLOT_TEMPLATE, height=450, dragmode='select', clickmode='event+select', uirevision='seleccion-estaciones', title=f'Perfiles de clusters — {segmento}, {anio}', margin={'l': 55, 'r': 25, 't': 55, 'b': 55})
    fig.update_xaxes(tickmode='array', tickvals=slot_hora[::8], ticktext=slot_hora[::8], title='Hora')
    fig.update_yaxes(title='% diario por slot')
    if minuto is not None:
        hora_activa = slot_hora[np.argmin(np.abs(slot_min - int(minuto)))]
        fig.add_vline(x=hora_activa, line_width=2, line_dash='dash', line_color='#111111', opacity=.8)
    return fig

app = Dash(__name__, title='Demanda de Subtes', assets_folder=str(ROOT / 'assets'))
server = app.server

filtros_globales = html.Div([
    html.Div([html.Label('Tipo de día'), dcc.RadioItems(id='segmento-filter', options=SEGMENTOS, value='Laborable', inline=True)]),
    html.Div([html.Label('Año principal'), dcc.Dropdown(id='anio-filter', options=anios, value=anio_principal_default, clearable=False)]),
    html.Div([html.Label('Año base'), dcc.Dropdown(id='anio-base-filter', options=anios, value=anio_base_default, clearable=False)]),
    html.Div([html.Label('Líneas'), dcc.Dropdown(id='linea-filter', options=lineas, value=lineas, multi=True, clearable=False)]),
], style={'display': 'grid', 'gridTemplateColumns': '2fr 1fr 1fr 2fr', 'gap': '18px', 'background': 'white', 'padding': '18px 20px', 'borderRadius': '16px', 'border': '1px solid #dce5ef', 'boxShadow': '0 8px 24px rgba(31,55,85,.06)'})

tab_resumen = html.Div([
    html.Div([
        html.Div([
            html.Strong('Selección vinculada: '),
            html.Span(id='seleccion-info', children='sin selección; se muestran todas las estaciones'),
            html.Div('Usá lazo o rectángulo sobre puntos, seleccioná barras, o hacé clic en una celda, trayectoria o perfil de cluster. Reset view/Reset axes quita solo la selección de ese gráfico; el botón de la derecha quita todas.', style={'fontSize': '12px', 'color': COLOR_TEXTO_SEC, 'marginTop': '4px'}),
        ]),
        html.Button('Quitar todas las selecciones', id='limpiar-seleccion', n_clicks=0, style={'border': 'none', 'borderRadius': '9px', 'background': COLOR_PRIMARIO, 'color': 'white', 'fontWeight': 650, 'padding': '9px 14px', 'cursor': 'pointer'}),
    ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'gap': '12px', 'marginTop': '14px', 'padding': '12px 16px', 'background': '#edf6f5', 'border': '1px solid #b9ddd8', 'borderRadius': '12px'}),
    html.Div(id='cards-red', style={'display': 'grid', 'gridTemplateColumns': 'repeat(4, minmax(210px, 1fr))', 'gap': '12px', 'marginTop': '14px'}),
    html.Div([
        html.Div([
            html.Div([
                html.Label('Hora del mapa', style={'display': 'block', 'marginBottom': '8px'}),
                html.Div([
                    html.Button('▶ Reproducir', id='reproducir-mapa', n_clicks=0, style={'minWidth': '112px', 'border': '1px solid #111111', 'borderRadius': '9px', 'background': '#FFD100', 'color': '#111111', 'fontWeight': 700, 'padding': '8px 12px', 'cursor': 'pointer'}),
                    html.Div(dcc.Slider(id='hora-map-filter', min=HORARIOS_HABITUALES['Laborable'][0], max=HORARIOS_HABITUALES['Laborable'][1], step=INTERVALO_MIN, value=17*60, marks=marcas_horario('Laborable'), allow_direct_input=False, updatemode='mouseup'), style={'flex': 1, 'minWidth': 0}),
                ], style={'display': 'flex', 'alignItems': 'center', 'gap': '16px'}),
            ], style={'padding': '8px 18px'}),
            dcc.Graph(id='mapa-graph', config={'displaylogo': False, 'modeBarButtonsToAdd': ['lasso2d', 'select2d']}),
            html.Div('Alcance: operación habitual (laborables 05:30–23:30; sábados 06:00–24:00; domingos/feriados 08:00–22:00). Dentro de esas ventanas se conserva todo el dato disponible; sólo se excluyen franjas fuera de servicio y extensiones nocturnas por eventos. Anillo = línea; relleno = % del día; tamaño = demanda, con escala fija durante la animación. Durante la reproducción se actualiza solo el mapa; al pausar, la hora queda marcada en los gráficos temporales.', style={'fontSize': '12px', 'color': COLOR_TEXTO_SEC, 'padding': '0 12px 8px'}),
        ], style=PANEL_STYLE),
        html.Div(dcc.Graph(id='heatmap-graph', config={'displaylogo': False}), style=PANEL_STYLE),
    ], style={'display': 'grid', 'gridTemplateColumns': '1.15fr .85fr', 'gap': '14px', 'marginTop': '14px'}),
    html.Div([
        html.Div(dcc.Graph(id='presion-graph', config={'displaylogo': False, 'modeBarButtonsToAdd': ['lasso2d', 'select2d']}), style=PANEL_STYLE),
        html.Div(dcc.Graph(id='evolucion-graph', config={'displaylogo': False, 'modeBarButtonsToAdd': ['lasso2d', 'select2d']}), style=PANEL_STYLE),
    ], style={'display': 'grid', 'gridTemplateColumns': '1.1fr .9fr', 'gap': '14px', 'marginTop': '14px'}),
    html.Div([
        dcc.Graph(id='comparacion-picos-graph', config={'displaylogo': False, 'modeBarButtonsToAdd': ['select2d']}),
        html.Div('Izquierda: estaciones con una meseta de demanda más prolongada. Derecha: estaciones con más pasajeros en su mejor ventana de 60 minutos. Es posible que una estación aparezca en ambos rankings: tiene un pico alto y sostenido.', style={'fontSize': '12px', 'color': COLOR_TEXTO_SEC, 'padding': '0 12px 8px'}),
    ], style={**PANEL_STYLE, 'marginTop': '14px'}),
], style={'paddingBottom': '20px'})

tab_estacion = html.Div([
    html.Div([html.Label('Estación'), dcc.Dropdown(id='estacion-filter', placeholder='Elegí una estación')], style={'maxWidth': '520px', 'margin': '16px 0'}),
    html.Div(id='cards-estacion', style={'display': 'grid', 'gridTemplateColumns': 'repeat(4, minmax(210px, 1fr))', 'gap': '12px'}),
    html.Div([
        html.Div(dcc.Graph(id='perfil-estacion-graph', config={'displaylogo': False, 'modeBarButtonsToAdd': ['select2d']}), style=PANEL_STYLE),
        html.Div(dcc.Graph(id='historia-estacion-graph', config={'displaylogo': False, 'modeBarButtonsToAdd': ['select2d']}), style=PANEL_STYLE),
    ], style={'display': 'grid', 'gridTemplateColumns': '1fr 1fr', 'gap': '14px', 'marginTop': '14px'}),
], style={'paddingBottom': '20px'})

tab_fpca = html.Div([
    html.Div('Los ejes FPC1 y FPC2 pertenecen al modelo del tipo de día seleccionado y no se comparan numéricamente entre segmentos.', style={'fontSize': '13px', 'color': COLOR_TEXTO_SEC, 'margin': '14px 0'}),
    html.Div([
        html.Div(dcc.Graph(id='trayectorias-graph', config={'displaylogo': False, 'modeBarButtonsToAdd': ['lasso2d', 'select2d']}), style=PANEL_STYLE),
        html.Div(dcc.Graph(id='composicion-graph', config={'displaylogo': False, 'modeBarButtonsToAdd': ['select2d']}), style=PANEL_STYLE),
    ], style={'display': 'grid', 'gridTemplateColumns': '1.15fr .85fr', 'gap': '14px'}),
    html.Div(dcc.Graph(id='clusters-graph', config={'displaylogo': False, 'modeBarButtonsToAdd': ['select2d']}), style={**PANEL_STYLE, 'marginTop': '14px'}),
], style={'paddingBottom': '20px'})

app.layout = html.Div([
    dcc.Store(id='selecciones-graficos', data={}),
    dcc.Store(id='seleccion-estaciones', data=None),
    dcc.Store(id='hora-contexto', data=17*60),
    dcc.Interval(id='reloj-mapa', interval=650, n_intervals=0, disabled=True),
    html.Div([
        html.Div([
            marca_demanda_subte(),
            html.Div([
                html.H1('Panel de demanda y patrones', style={'margin': 0, 'fontSize': '32px', 'letterSpacing': '-.025em', 'color': COLOR_TEXTO}),
                html.Div('Red de Subte de la Ciudad de Buenos Aires · volumen, concentración horaria y patrones funcionales', style={'color': COLOR_TEXTO_SEC, 'marginTop': '7px', 'fontSize': '14px'}),
                html.Div([insignia_linea(linea, 32) for linea in lineas], style={'display': 'flex', 'gap': '8px', 'marginTop': '14px'}),
            ], style={'flex': 1}),
        ], style={'display': 'flex', 'alignItems': 'center', 'flexWrap': 'wrap', 'gap': '22px', 'marginBottom': '22px', 'padding': '16px 20px',
                  'background': 'white', 'borderRadius': '18px', 'border': '1px solid #dce5ef', 'borderBottom': '5px solid #FFD100',
                  'boxShadow': '0 8px 24px rgba(31,55,85,.07)'}),
        filtros_globales,
        dcc.Tabs(id='tabs', value='resumen', children=[
            dcc.Tab(label='Resumen de red', value='resumen', children=tab_resumen, style=TAB_STYLE, selected_style=TAB_SELECTED_STYLE),
            dcc.Tab(label='Detalle de estación', value='estacion', children=tab_estacion, style=TAB_STYLE, selected_style=TAB_SELECTED_STYLE),
            dcc.Tab(label='Patrones FPCA', value='fpca', children=tab_fpca, style=TAB_STYLE, selected_style=TAB_SELECTED_STYLE),
        ], style={'marginTop': '14px'}),
    ], style={'maxWidth': '1680px', 'margin': '0 auto', 'padding': '18px'}),
], style={'background': COLOR_FONDO, 'minHeight': '100vh', 'fontFamily': 'Inter, Arial, sans-serif'})

print('Layout creado.')

GRAFICOS_VINCULADOS = [
    'mapa-graph', 'heatmap-graph', 'presion-graph', 'evolucion-graph', 'comparacion-picos-graph',
    'trayectorias-graph', 'composicion-graph', 'clusters-graph',
    'perfil-estacion-graph', 'historia-estacion-graph',
]

@app.callback(
    Output('selecciones-graficos', 'data'),
    *[entrada for grafico in GRAFICOS_VINCULADOS for entrada in (
        Input(grafico, 'selectedData'), Input(grafico, 'clickData'), Input(grafico, 'relayoutData')
    )],
    Input('limpiar-seleccion', 'n_clicks'), Input('segmento-filter', 'value'),
    Input('anio-filter', 'value'), Input('anio-base-filter', 'value'), Input('linea-filter', 'value'),
    State('selecciones-graficos', 'data'), prevent_initial_call=True,
)
def actualizar_selecciones_por_grafico(*valores):
    if not ctx.triggered:
        return no_update
    disparados = ctx.triggered
    ids_disparados = {item['prop_id'].rsplit('.', 1)[0] for item in disparados}
    if ids_disparados & {'limpiar-seleccion', 'segmento-filter', 'anio-filter', 'anio-base-filter', 'linea-filter'}:
        return {}
    estado = dict(valores[-1] or {})
    # Reset axes/view puede llegar junto con selectedData=None: se procesa primero.
    for item in disparados:
        grafico, propiedad = item['prop_id'].rsplit('.', 1)
        if propiedad == 'relayoutData' and es_reset_vista(item.get('value'), grafico):
            if grafico in estado:
                estado.pop(grafico, None)
                return estado
            return no_update
    # En un clic pueden llegar clickData y selectedData; se prioriza la selección múltiple.
    for tipo_evento in ('selectedData', 'clickData'):
        for item in disparados:
            grafico, propiedad = item['prop_id'].rsplit('.', 1)
            if propiedad != tipo_evento:
                continue
            seleccion = estaciones_desde_evento(item.get('value'))
            if seleccion:
                estado[grafico] = seleccion
                return estado
    # Los selectedData=None emitidos por un redibujado no deben borrar filtros.
    return no_update

@app.callback(Output('seleccion-estaciones', 'data'), Input('selecciones-graficos', 'data'))
def consolidar_selecciones(selecciones_por_grafico):
    return combinar_selecciones(selecciones_por_grafico)

@app.callback(Output('seleccion-info', 'children'), Input('seleccion-estaciones', 'data'), Input('selecciones-graficos', 'data'))
def actualizar_texto_seleccion(seleccion_estaciones, selecciones_por_grafico):
    n_filtros = len(selecciones_por_grafico or {})
    if seleccion_estaciones is None:
        return 'sin selección; se muestran todas las estaciones'
    if not seleccion_estaciones:
        return f'sin coincidencias entre {n_filtros} selecciones activas'
    muestra = ', '.join(seleccion_estaciones[:4])
    resto = f' y {len(seleccion_estaciones) - 4} más' if len(seleccion_estaciones) > 4 else ''
    return f'{len(seleccion_estaciones)} estación(es) · {n_filtros} gráfico(s) activo(s): {muestra}{resto}'

@app.callback(
    Output('reloj-mapa', 'disabled'), Output('reproducir-mapa', 'children'),
    Input('reproducir-mapa', 'n_clicks'), State('reloj-mapa', 'disabled'),
    prevent_initial_call=True,
)
def alternar_reproduccion_mapa(_, esta_detenido):
    nuevo_estado = not bool(esta_detenido)
    return nuevo_estado, ('▶ Reproducir' if nuevo_estado else '⏸ Pausar')

@app.callback(
    Output('hora-map-filter', 'min'), Output('hora-map-filter', 'max'), Output('hora-map-filter', 'marks'),
    Input('segmento-filter', 'value'),
)
def actualizar_rango_horario(segmento):
    inicio, fin = limites_horario(segmento)
    return inicio, fin, marcas_horario(segmento)

@app.callback(
    Output('hora-map-filter', 'value'), Input('reloj-mapa', 'n_intervals'), Input('segmento-filter', 'value'),
    State('hora-map-filter', 'value'), prevent_initial_call=True,
)
def avanzar_hora_mapa(_, segmento, minuto_actual):
    inicio, fin = limites_horario(segmento)
    if ctx.triggered_id == 'segmento-filter':
        return int(np.clip(17*60 if minuto_actual is None else minuto_actual, inicio, fin))
    slots_activos = slot_min[(slot_min >= inicio) & (slot_min <= fin)]
    if minuto_actual is None:
        return int(slots_activos[0])
    indice = int(np.argmin(np.abs(slots_activos - int(minuto_actual))))
    return int(slots_activos[(indice + 1) % len(slots_activos)])

@app.callback(
    Output('hora-contexto', 'data'), Input('reloj-mapa', 'disabled'),
    Input('hora-map-filter', 'value'), prevent_initial_call=True,
)
def fijar_hora_contexto_al_pausar(esta_detenido, minuto_actual):
    return int(minuto_actual) if esta_detenido and minuto_actual is not None else no_update

@app.callback(
    Output('mapa-graph', 'figure'),
    Input('segmento-filter', 'value'), Input('anio-filter', 'value'),
    Input('linea-filter', 'value'), Input('hora-map-filter', 'value'),
    Input('seleccion-estaciones', 'data'),
)
def actualizar_mapa(segmento, anio, seleccion_lineas, minuto, seleccion_estaciones):
    return grafico_mapa(segmento, anio, seleccion_lineas, minuto, seleccion_estaciones)

@app.callback(
    Output('cards-red', 'children'), Output('heatmap-graph', 'figure'),
    Output('presion-graph', 'figure'), Output('evolucion-graph', 'figure'),
    Output('comparacion-picos-graph', 'figure'),
    Input('segmento-filter', 'value'), Input('anio-filter', 'value'),
    Input('anio-base-filter', 'value'), Input('linea-filter', 'value'),
    Input('seleccion-estaciones', 'data'), Input('hora-contexto', 'data'),
)
def actualizar_resumen(segmento, anio, anio_base, seleccion_lineas, seleccion_estaciones, minuto_contexto):
    return (
        calcular_tarjetas(segmento, anio, anio_base, seleccion_lineas, seleccion_estaciones),
        grafico_heatmap(segmento, anio, seleccion_lineas, seleccion_estaciones, minuto=minuto_contexto),
        grafico_presion(segmento, anio, seleccion_lineas, seleccion_estaciones),
        grafico_evolucion(segmento, anio_base, anio, seleccion_lineas, seleccion_estaciones),
        grafico_comparacion_picos(segmento, anio, seleccion_lineas, seleccion_estaciones),
    )

@app.callback(
    Output('estacion-filter', 'options'), Output('estacion-filter', 'value'),
    Input('linea-filter', 'value'), Input('seleccion-estaciones', 'data'), State('estacion-filter', 'value'),
)
def actualizar_estaciones(seleccion_lineas, seleccion_estaciones, actual):
    d = filtrar_lineas(metricas, seleccion_lineas)
    d = filtrar_estaciones(d, seleccion_estaciones)
    opciones = sorted(d['estacion_id'].dropna().unique().tolist())
    valor = actual if actual in opciones else (opciones[0] if opciones else None)
    return opciones, valor

@app.callback(
    Output('cards-estacion', 'children'), Output('perfil-estacion-graph', 'figure'),
    Output('historia-estacion-graph', 'figure'),
    Input('estacion-filter', 'value'), Input('segmento-filter', 'value'),
    Input('anio-filter', 'value'), Input('anio-base-filter', 'value'), Input('hora-contexto', 'data'),
)
def actualizar_detalle_estacion(estacion_id, segmento, anio, anio_base, minuto_contexto):
    return (
        tarjetas_estacion(estacion_id, segmento, anio),
        grafico_perfil_estacion(estacion_id, segmento, anio_base, anio, minuto_contexto),
        grafico_historia_estacion(estacion_id, segmento),
    )

@app.callback(
    Output('trayectorias-graph', 'figure'), Output('composicion-graph', 'figure'),
    Output('clusters-graph', 'figure'),
    Input('segmento-filter', 'value'), Input('anio-filter', 'value'),
    Input('anio-base-filter', 'value'), Input('linea-filter', 'value'), Input('seleccion-estaciones', 'data'), Input('hora-contexto', 'data'),
)
def actualizar_fpca(segmento, anio, anio_base, seleccion_lineas, seleccion_estaciones, minuto_contexto):
    return (
        grafico_trayectorias(segmento, anio_base, anio, seleccion_lineas, seleccion_estaciones),
        grafico_composicion_clusters(segmento, anio_base, anio, seleccion_lineas, seleccion_estaciones),
        grafico_perfiles_cluster(segmento, anio, seleccion_lineas, seleccion_estaciones, minuto_contexto),
    )

print('Callbacks registrados.')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', '8050')), debug=False)
