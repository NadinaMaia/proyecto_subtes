import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";

const workspaceDir = "/Users/nadinasoler/Documents/documentos/Nari/proyecto_subtes";
const SKILL_DIR = "/Users/nadinasoler/.codex/plugins/cache/openai-primary-runtime/presentations/26.927.11222/skills/presentations";
const TMP_DIR = path.join(workspaceDir, ".presentation_subte_moving");
const FINAL_PPTX = path.join(workspaceDir, "outputs", "Presentacion_Proyecto_Subte_FPCA_2014_2026_subte_avanza_final.pptx");
const RUNTIME_PYTHON = "/Users/nadinasoler/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12";
const RUNTIME_NODE_MODULES = "/Users/nadinasoler/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules";
const requireFromRuntime = createRequire(path.join(RUNTIME_NODE_MODULES, "__runtime__.cjs"));
const { Presentation, PresentationFile } = await import(pathToFileURL(requireFromRuntime.resolve("@oai/artifact-tool")).href);

const { makeNativeBulletParagraphs, applyPresentationChartFont, finalizePresentation } = await import(
  pathToFileURL(path.join(SKILL_DIR, "container_tools/artifact_tool_utils.mjs")).href,
);

const W = 1280;
const H = 720;
const HEAD = "Arial Black";
const BODY = "Arial";
const COLORS = {
  white: "#FFFFFF",
  paper: "#F7F7F3",
  ink: "#111111",
  body: "#111111",
  muted: "#5B6066",
  h1: "#111111",
  h2: "#111111",
  h3: "#111111",
  yellow: "#FFD400",
  yellowSoft: "#FFF5B8",
  cyan: "#00A8C6",
  cyanSoft: "#DDF5F8",
  red: "#E31B23",
  greenLine: "#00A650",
  purpleLine: "#6F2C91",
  blueLine: "#0055A4",
  blue: "#DDF5F8",
  blueBorder: "#00A8C6",
  blueSoft: "#F0FAFB",
  warm: "#FFF5B8",
  warmBorder: "#FFD400",
  green: "#E1F4E7",
  purple: "#EEE3F3",
  rose: "#FBE2E3",
  rule: "#C7C9C7",
  grid: "#E3E4E1",
};

const LINE_COLORS = [COLORS.cyan, COLORS.red, COLORS.blueLine, COLORS.greenLine, COLORS.purpleLine, COLORS.yellow];
const motifBlob = await fs.readFile(path.join(workspaceDir, "assets/presentacion/subte-route-motif.png"));
const trainBlob = await fs.readFile(path.join(workspaceDir, "assets/presentacion/subte-train.png"));
const logoBlob = await fs.readFile(path.join(workspaceDir, "assets/demanda-subte.png"));

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') {
        field += '"';
        i += 1;
      } else if (ch === '"') quoted = false;
      else field += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ",") {
      row.push(field);
      field = "";
    } else if (ch === "\n") {
      row.push(field.replace(/\r$/, ""));
      rows.push(row);
      row = [];
      field = "";
    } else field += ch;
  }
  if (field.length || row.length) {
    row.push(field.replace(/\r$/, ""));
    rows.push(row);
  }
  const headers = rows.shift();
  return rows.filter((r) => r.some((v) => v !== "")).map((r) =>
    Object.fromEntries(headers.map((h, i) => [h, r[i] ?? ""])),
  );
}

async function readCsv(rel) {
  return parseCsv(await fs.readFile(path.join(workspaceDir, rel), "utf8"));
}

function median(values) {
  const clean = values.filter(Number.isFinite).sort((a, b) => a - b);
  if (!clean.length) return 0;
  const mid = Math.floor(clean.length / 2);
  return clean.length % 2 ? clean[mid] : (clean[mid - 1] + clean[mid]) / 2;
}

const [dailyRows, varianceRows, modelRows, clusterRows, profileRows, changeRows, prototypeRows] = await Promise.all([
  readCsv("subte_fpca_work/resultados/serie_diaria_red.csv"),
  readCsv("subte_fpca_work/resultados/varianza_fpca_segmentada.csv"),
  readCsv("subte_fpca_work/resultados/resumen_modelos_segmentados.csv"),
  readCsv("subte_fpca_work/resultados/caracterizacion_clusters.csv"),
  readCsv("subte_fpca_work/resultados/perfiles_suavizados_segmentados.csv"),
  readCsv("subte_fpca_work/resultados/cambios_2019_2025_por_segmento.csv"),
  readCsv("subte_fpca_work/resultados/prototipos_maxvol.csv"),
]);

const byYear = new Map();
for (const r of dailyRows) {
  const year = Number(r.anio);
  if (!byYear.has(year)) byYear.set(year, []);
  byYear.get(year).push(Number(r.pax_total));
}
const annualYears = [...byYear.keys()].sort((a, b) => a - b);
const annualValues = annualYears.map((year) => Number((median(byYear.get(year)) / 1_000_000).toFixed(6)));
const value2019 = annualValues[annualYears.indexOf(2019)];
const value2025 = annualValues[annualYears.indexOf(2025)];
const recoveryRatio = value2025 / value2019;

const varianceSummary = modelRows.map((r) => ({
  segment: r.segmento_dia,
  components: Number(r.componentes_90),
  variance: Number(Number(varianceRows.find((v) => v.segmento_dia === r.segmento_dia && Number(v.componente) === Number(r.componentes_90))?.acumulada ?? 0).toFixed(6)),
  k: Number(r.k),
  silhouette: Number(r.silhouette),
  ari: Number(r.ari_estabilidad),
}));

const selectedSlots = Array.from({ length: 19 }, (_, i) => 300 + i * 60);
const slotColumns = selectedSlots.map((m) => `slot_${String(m).padStart(4, "0")}`);
const hourCategories = selectedSlots.map((m) => String(Math.floor(m / 60)).padStart(2, "0"));
const profileGroups = new Map();
for (const r of profileRows) {
  const key = `${r.segmento_dia}::${r.cluster_id}`;
  if (!profileGroups.has(key)) profileGroups.set(key, slotColumns.map(() => []));
  slotColumns.forEach((col, i) => profileGroups.get(key)[i].push(Number(r[col])));
}
const clusterProfiles = Object.fromEntries(
  [...profileGroups].map(([key, cols]) => [key, cols.map((values) => Number(median(values).toFixed(6)))]),
);

const topChanges = changeRows
  .map((r) => ({
    ...r,
    distancia_scores: Number(r.distancia_scores),
    ratio_pax_post_pre: Number(r.ratio_pax_post_pre),
  }))
  .sort((a, b) => b.distancia_scores - a.distancia_scores)
  .slice(0, 5);

const selectedPrototypeIds = ["LAB-P2", "SAB-P3", "DOM-P3"];
const selectedPrototypes = selectedPrototypeIds.map((id) => prototypeRows.find((r) => r.prototipo_maxvol === id));

const presentation = Presentation.create({ slideSize: { width: W, height: H } });

function addShape(slide, geometry, position, fill = "none", lineFill = "none", lineWidth = 0, name) {
  return slide.shapes.add({
    geometry,
    name,
    position,
    fill,
    line: { style: "solid", fill: lineFill, width: lineWidth },
  });
}

function addText(slide, text, position, options = {}) {
  const box = addShape(slide, "textbox", position, "none", "none", 0, options.name);
  box.text = text;
  box.text.style = {
    typeface: options.typeface ?? BODY,
    fontSize: options.fontSize ?? 30,
    bold: options.bold ?? false,
    italic: options.italic ?? false,
    color: options.color ?? COLORS.body,
    alignment: options.alignment ?? "left",
    verticalAlignment: options.verticalAlignment ?? "top",
    autoFit: options.autoFit ?? "none",
    wrap: options.wrap ?? "square",
    lineSpacing: options.lineSpacing ?? 1.18,
    insets: options.insets ?? { top: 0, right: 0, bottom: 0, left: 0 },
  };
  return box;
}

function addRichText(slide, paragraphs, position, options = {}) {
  const box = addShape(slide, "textbox", position, "none", "none", 0, options.name);
  box.text = paragraphs;
  box.text.style = {
    typeface: options.typeface ?? BODY,
    fontSize: options.fontSize ?? 30,
    color: options.color ?? COLORS.body,
    autoFit: "none",
    wrap: "square",
    lineSpacing: options.lineSpacing ?? 1.16,
    insets: options.insets ?? { top: 0, right: 0, bottom: 0, left: 0 },
  };
  return box;
}

function addBullets(slide, items, position, options = {}) {
  const box = addShape(slide, "textbox", position, "none", "none", 0, options.name);
  box.text = makeNativeBulletParagraphs(items, {
    marginLeftPoints: options.marginLeftPoints ?? 24,
    hangingPoints: options.hangingPoints ?? 12,
    spaceAfterPoints: options.spaceAfterPoints ?? 14,
    bulletCharacter: options.bulletCharacter ?? "•",
  });
  box.text.style = {
    typeface: BODY,
    fontSize: options.fontSize ?? 31,
    color: options.color ?? COLORS.body,
    autoFit: "none",
    wrap: "square",
    lineSpacing: options.lineSpacing ?? 1.16,
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
  };
  return box;
}

function addBox(slide, position, fill, options = {}) {
  const shape = addShape(slide, "roundRect", position, fill, options.lineFill ?? "none", options.lineWidth ?? 0, options.name);
  shape.borderRadius = options.borderRadius ?? 16;
  return shape;
}

function addImage(slide, blob, position, alt, fit = "contain") {
  return slide.images.add({ blob, contentType: "image/png", alt, fit, position });
}

function addCallout(slide, position, fill, accent, text, options = {}) {
  addBox(slide, position, fill, { borderRadius: options.borderRadius ?? 16, name: options.name });
  addShape(slide, "rect", { left: position.left, top: position.top, width: options.barWidth ?? 7, height: position.height }, accent, "none", 0);
  return addText(slide, text, {
    left: position.left + 26,
    top: position.top + 18,
    width: position.width - 48,
    height: position.height - 34,
  }, {
    fontSize: options.fontSize ?? 27,
    bold: options.bold ?? false,
    color: options.color ?? COLORS.ink,
    verticalAlignment: options.verticalAlignment ?? "middle",
  });
}

function addFooter(slide, number) {
  const accent = LINE_COLORS[(number - 1) % LINE_COLORS.length];
  const trainWidth = 110;
  const trainHeight = 31;
  const startX = 24;
  const endX = 1068;
  const progress = (number - 1) / 15;
  const trainX = startX + (endX - startX) * progress;
  addShape(slide, "rect", { left: 0, top: 692, width: 1280, height: 3 }, COLORS.ink, "none", 0);
  addShape(slide, "rect", { left: 0, top: 692, width: trainX + trainWidth / 2, height: 6 }, COLORS.yellow, "none", 0);
  addImage(slide, trainBlob, { left: trainX, top: 658, width: trainWidth, height: trainHeight }, `Coche del Subte avanzando, diapositiva ${number}`, "contain");
  addText(slide, "PROYECTO FINAL · PULSO DEL SUBTE", { left: 54, top: 701, width: 430, height: 16 }, {
    fontSize: 12,
    bold: true,
    color: COLORS.muted,
  });
  const stop = addShape(slide, "ellipse", { left: 1192, top: 687, width: 28, height: 28 }, accent, COLORS.ink, 1.5);
  stop.text = String(number);
  stop.text.style = { typeface: BODY, fontSize: 12, bold: true, color: number % 6 === 0 ? COLORS.ink : COLORS.white, alignment: "center", verticalAlignment: "middle", autoFit: "none" };
}

function addTitle(slide, title, number) {
  const accent = LINE_COLORS[(number - 1) % LINE_COLORS.length];
  addShape(slide, "rect", { left: 64, top: 39, width: 11, height: 72 }, COLORS.yellow, "none", 0);
  addText(slide, title, { left: 92, top: 39, width: 1070, height: 76 }, {
    typeface: HEAD,
    fontSize: 49,
    bold: true,
    color: COLORS.ink,
    name: "Slide title",
  });
  addShape(slide, "rect", { left: 1167, top: 55, width: 48, height: 36 }, accent, COLORS.ink, 1);
  addFooter(slide, number);
}

function addNotes(slide, lines, sources) {
  slide.speakerNotes.textFrame.setText([
    ...lines,
    "",
    "[Sources]",
    ...sources,
    "[/Sources]",
  ]);
  slide.speakerNotes.setVisible(true);
}

function createContentSlide(title, notes, sources) {
  const slide = presentation.slides.add();
  slide.background.fill = COLORS.paper;
  const number = presentation.slides.items.length;
  addTitle(slide, title, number);
  addNotes(slide, notes, sources);
  return slide;
}

function createSectionSlide(title, subtitle, notes, sources) {
  const slide = presentation.slides.add();
  slide.background.fill = COLORS.paper;
  const number = presentation.slides.items.length;
  addImage(slide, motifBlob, { left: 0, top: 0, width: W, height: H }, "Mapa abstracto inspirado en la red de Subte", "cover");
  addShape(slide, "rect", { left: 0, top: 245, width: 1000, height: 142 }, COLORS.ink, "none", 0);
  addShape(slide, "ellipse", { left: 1040, top: 258, width: 112, height: 112 }, COLORS.yellow, COLORS.ink, 4);
  addText(slide, title, { left: 86, top: 267, width: 860, height: 88 }, {
    typeface: HEAD,
    fontSize: 70,
    bold: true,
    color: COLORS.white,
    alignment: "left",
    verticalAlignment: "middle",
    name: "Section title",
  });
  if (subtitle) addText(slide, subtitle, { left: 88, top: 418, width: 910, height: 58 }, {
    fontSize: 27,
    color: COLORS.ink,
    bold: true,
    alignment: "left",
  });
  addFooter(slide, number);
  addNotes(slide, notes, sources);
  return slide;
}

function styleChart(chart) {
  applyPresentationChartFont(chart, { fontFamily: BODY });
  if (chart.titleTextStyle) {
    chart.titleTextStyle.typeface = HEAD;
    chart.titleTextStyle.fill = COLORS.h3;
    chart.titleTextStyle.fontSize = 22;
    chart.titleTextStyle.bold = true;
  }
  return chart;
}

// 1. Cover
{
  const slide = presentation.slides.add();
  slide.background.fill = COLORS.paper;
  addImage(slide, motifBlob, { left: 0, top: 0, width: W, height: H }, "Mapa abstracto de líneas y estaciones", "cover");
  addShape(slide, "rect", { left: 0, top: 95, width: 925, height: 270 }, COLORS.ink, "none", 0);
  addShape(slide, "rect", { left: 0, top: 365, width: 925, height: 13 }, COLORS.yellow, "none", 0);
  addText(slide, "EL PULSO\nESPACIO-TEMPORAL", { left: 75, top: 123, width: 800, height: 178 }, {
    typeface: HEAD,
    fontSize: 66,
    bold: true,
    color: COLORS.white,
    alignment: "left",
    verticalAlignment: "middle",
    name: "Deck title",
  });
  addText(slide, "DEL SUBTE DE BUENOS AIRES", { left: 76, top: 309, width: 780, height: 38 }, {
    fontSize: 28,
    bold: true,
    color: COLORS.yellow,
    alignment: "left",
  });
  addImage(slide, logoBlob, { left: 1010, top: 54, width: 205, height: 205 }, "Marca circular Demanda Subte", "contain");
  addText(slide, "FPCA · CLUSTERING · MAXVOL", { left: 74, top: 416, width: 700, height: 45 }, {
    fontSize: 29,
    bold: true,
    color: COLORS.ink,
    alignment: "left",
  });
  addText(slide, "Demanda de pasajeros · 2014–2026", { left: 76, top: 466, width: 650, height: 38 }, {
    fontSize: 23,
    color: COLORS.muted,
    alignment: "left",
  });
  addImage(slide, trainBlob, { left: 540, top: 450, width: 690, height: 205 }, "Ilustración de coche del Subte", "contain");
  addShape(slide, "rect", { left: 75, top: 570, width: 435, height: 42 }, COLORS.ink, "none", 0);
  addText(slide, "PROYECTO FINAL · VISUALIZACIÓN DE DATOS", { left: 92, top: 581, width: 405, height: 22 }, {
    fontSize: 14,
    color: COLORS.white,
    bold: true,
    alignment: "left",
  });
  addFooter(slide, 1);
  addNotes(slide, [
    "Abrir con la idea de que la demanda tiene una forma horaria y una geografía, no solo un total diario.",
    "Anticipar que la presentación cubrirá el problema, los datos, el método, los resultados y la aplicación visual.",
    "La identidad visual usa amarillo y negro como referencia cultural inmediata del Subte; los colores de línea se reservan para categorías y navegación.",
  ], [
    "Day1_3_Data_Visualization_Color.pdf, variables visuales y aspectos culturales del color",
    "Contenido del proyecto: Presentacion_Proyecto_Subte_FPCA_2014_2026.pptx",
  ]);
}

// 2. Section
createSectionSlide("El proyecto", "Problema, datos, audiencia y contexto de uso", [
  "Usar esta diapositiva como transición breve.",
], ["subte_fpca_work/documentacion/generar_presentacion_proyecto.py"]);

// 3. Why
{
  const slide = createContentSlide("Why: el total diario oculta la forma", [
    "La motivación es separar volumen, horario y geografía para evitar conclusiones basadas solo en totales.",
    "La pregunta guía organiza las tareas del proyecto.",
  ], ["subte_fpca_work/documentacion/generar_presentacion_proyecto.py, secciones 1 y 2"]);
  addText(slide, "¿Cómo cambió la geografía y la temporalidad de la demanda, y qué perfiles caracterizan a las estaciones?", {
    left: 72, top: 138, width: 1136, height: 118,
  }, { typeface: HEAD, fontSize: 38, bold: true, color: COLORS.ink, alignment: "center", verticalAlignment: "middle" });
  addBullets(slide, [
    "Comparar estaciones sin confundir tamaño con forma horaria.",
    "Distinguir laborables, sábados y domingos o feriados.",
    "Reconocer cambios históricos sin leer la pandemia ni un año parcial como tendencia estable.",
    "Convertir el análisis en una aplicación visual explorable.",
  ], { left: 110, top: 300, width: 1060, height: 260, fontSize: 29, spaceAfterPoints: 12 });
  addCallout(slide, { left: 145, top: 575, width: 990, height: 74 }, COLORS.warm, COLORS.warmBorder,
    "Objetivo: explicar dónde, cuándo y cómo cambia el uso típico de la red.", { fontSize: 28, bold: true });
}

// 4. What
{
  const slide = createContentSlide("What: datos cada 15 minutos", [
    "Describir la unidad de observación y aclarar que 2026 es parcial.",
    "Separar datos de origen y productos derivados.",
  ], [
    "subte_fpca_work/resultados/resumen_automatico.md",
    "subte_fpca_work/resultados/resumen_capa_mapa_dashboard.csv",
  ]);
  addRichText(slide, [
    [{ run: "Período: ", textStyle: { bold: true } }, "2014–2026; 2026 llega al 30 de junio."],
    [{ run: "Unidad: ", textStyle: { bold: true } }, "línea + estación + fecha + intervalo de 15 minutos."],
    [{ run: "Segmentos: ", textStyle: { bold: true } }, "laborable, sábado y domingo/feriado."],
    [{ run: "Derivados: ", textStyle: { bold: true } }, "curvas típicas, scores FPCA, clusters, prototipos y capa geográfica."],
  ], { left: 72, top: 160, width: 650, height: 340 }, { fontSize: 30, lineSpacing: 1.28 });
  addBox(slide, { left: 780, top: 155, width: 425, height: 340 }, COLORS.blue, { borderRadius: 16 });
  const metrics = [
    ["122 / 122", "fuentes aceptadas"],
    ["139,2 M", "filas estandarizadas"],
    ["137,2 M", "filas tras resolver la clave"],
    ["3.270", "curvas funcionales"],
  ];
  metrics.forEach(([value, label], i) => {
    const y = 182 + i * 75;
    addText(slide, value, { left: 812, top: y, width: 145, height: 42 }, { fontSize: 33, bold: true, color: COLORS.h1 });
    addText(slide, label, { left: 970, top: y + 6, width: 205, height: 34 }, { fontSize: 22, color: COLORS.ink });
  });
  addCallout(slide, { left: 72, top: 540, width: 1136, height: 102 }, COLORS.blueSoft, COLORS.blueBorder,
    "Alcance comparable: se excluye Premetro, se conserva la identidad línea + estación y se muestran las advertencias de cobertura.", { fontSize: 26 });
}

// 5. To whom + context
{
  const slide = createContentSlide("To whom: explorar antes de decidir", [
    "Nombrar la audiencia principal y las audiencias secundarias.",
    "El contexto de uso es exploratorio, no control operativo en tiempo real.",
  ], ["subte_fpca_work/documentacion/generar_presentacion_proyecto.py, sección 3"]);
  addText(slide, "Audiencia", { left: 78, top: 150, width: 470, height: 44 }, { typeface: HEAD, fontSize: 37, bold: true, color: COLORS.h3 });
  addBullets(slide, [
    "Equipos de análisis y planificación de movilidad.",
    "Docente y jurado: trazabilidad y decisiones metodológicas.",
    "Público interesado en la dinámica de la red.",
  ], { left: 78, top: 220, width: 520, height: 260, fontSize: 26, spaceAfterPoints: 12 });
  addText(slide, "Contexto de uso", { left: 680, top: 150, width: 500, height: 44 }, { typeface: HEAD, fontSize: 37, bold: true, color: COLORS.h3 });
  addBullets(slide, [
    "Notebook Jupyter con una aplicación Dash reproducible.",
    "Exploración por año, tipo de día, línea, hora y estación.",
    "Apoyo a reuniones de diagnóstico y formulación de nuevas preguntas.",
  ], { left: 680, top: 220, width: 520, height: 260, fontSize: 26, spaceAfterPoints: 12 });
  addCallout(slide, { left: 135, top: 548, width: 1010, height: 92 }, COLORS.green, "#22C55E",
    "El tablero aporta evidencia descriptiva. No reemplaza datos de capacidad, tiempos de viaje ni un diseño causal.", { fontSize: 26, bold: true });
}

// 6. How, view-task mapping and visual-language rationale
{
  const slide = createContentSlide("How: vistas y lenguaje visual", [
    "Las vistas se eligieron según la tarea: localizar, comparar formas, detectar presión y explicar cambios.",
    "Posición codifica geografía y tiempo; tamaño codifica volumen absoluto; el tono identifica líneas o categorías.",
    "Brillo, saturación e intensidad expresan magnitud o énfasis. La opacidad reduce el peso del contexto no seleccionado.",
    "Forma, orientación y textura no codifican cantidades principales: se reservan para símbolos o redundancia accesible, evitando sobrecarga.",
    "El amarillo y negro funcionan como referencia cultural del Subte, no como escala cuantitativa. Los colores complementarios se usan solo para contraste puntual.",
    "Nunca se depende solo de rojo/verde: etiquetas, posición, tamaño y selección redundante sostienen la lectura ante deficiencias de visión cromática.",
  ], [
    "creacion_dashboard.ipynb, definición de vistas, escalas y callbacks",
    "subte_fpca_work/documentacion/generar_presentacion_proyecto.py, secciones 5 y 6",
    "Day1_3_Data_Visualization_Color.pdf, págs. 2, 18–20, 27–34 y 36",
  ]);
  addText(slide, "VISTAS → TAREAS", { left: 72, top: 139, width: 470, height: 32 }, { fontSize: 19, bold: true, color: COLORS.muted });
  const rows = [
    ["Mapa horario", "Localizar concentración"],
    ["Heatmap", "Comparar formas del día"],
    ["Matriz de presión", "Cruzar volumen e intensidad"],
    ["Evolución / detalle", "Explicar cambios"],
  ];
  rows.forEach(([view, task], i) => {
    const y = 184 + i * 82;
    addShape(slide, "rect", { left: 72, top: y, width: 8, height: 59 }, LINE_COLORS[i], "none", 0);
    addText(slide, view, { left: 99, top: y, width: 330, height: 27 }, { typeface: HEAD, fontSize: 21, bold: true, color: COLORS.ink });
    addText(slide, task, { left: 99, top: y + 29, width: 390, height: 25 }, { fontSize: 17, color: COLORS.muted });
  });

  addText(slide, "VARIABLE VISUAL → SIGNIFICADO", { left: 586, top: 139, width: 600, height: 32 }, { fontSize: 19, bold: true, color: COLORS.muted });
  const mappings = [
    ["POSICIÓN", "estación y hora", COLORS.cyan],
    ["TAMAÑO", "pasajeros absolutos", COLORS.yellow],
    ["TONO", "línea o categoría", COLORS.red],
    ["VALOR / INTENSIDAD", "participación o énfasis", COLORS.blueLine],
    ["OPACIDAD", "contexto vs. selección", COLORS.purpleLine],
  ];
  mappings.forEach(([variable, meaning, color], i) => {
    const y = 178 + i * 69;
    addShape(slide, "ellipse", { left: 590, top: y + 4, width: 38 + i * 4, height: 38 + i * 4 }, color, COLORS.ink, 1.2);
    addText(slide, variable, { left: 660, top: y, width: 225, height: 27 }, { fontSize: 18, bold: true, color: COLORS.ink });
    addText(slide, meaning, { left: 885, top: y, width: 300, height: 27 }, { fontSize: 18, color: COLORS.muted });
  });
  addCallout(slide, { left: 92, top: 550, width: 1096, height: 88 }, COLORS.yellowSoft, COLORS.yellow,
    "Amarillo + negro = identidad cultural. El color de línea clasifica; la magnitud se apoya también en posición, tamaño y etiquetas.", { fontSize: 24, bold: true });
}

// 7. Section
createSectionSlide("Del dato al modelo", "Calidad, curvas funcionales y reducción dimensional", [
  "Transición hacia la parte metodológica.",
], ["Proyecto_Subte_FPCA_2014-26.ipynb"]);

// 8. Pipeline
{
  const slide = createContentSlide("La comparabilidad precede al modelado", [
    "Explicar el pipeline como una cadena de decisiones de comparabilidad.",
    "No detenerse en código; resaltar por qué existe cada etapa.",
  ], [
    "Proyecto_Subte_FPCA_2014-26.ipynb, secciones 1–14",
    "subte_fpca_work/resultados/resumen_automatico.md",
  ]);
  const stages = [
    ["1", "Ingesta", "122 fuentes"],
    ["2", "Control", "fechas, grilla y cobertura"],
    ["3", "Curvas", "estación × año × segmento"],
    ["4", "Modelos", "FPCA, clusters y volumen"],
    ["5", "Producto", "vistas coordinadas"],
  ];
  addShape(slide, "line", { left: 150, top: 275, width: 980, height: 0 }, "none", COLORS.rule, 3);
  stages.forEach(([n, name, desc], i) => {
    const x = 115 + i * 242;
    const circle = addShape(slide, "ellipse", { left: x, top: 238, width: 74, height: 74 }, i === 4 ? COLORS.warm : COLORS.blue, COLORS.h3, 2);
    circle.text = n;
    circle.text.style = { typeface: HEAD, fontSize: 32, bold: true, color: COLORS.h1, alignment: "center", verticalAlignment: "middle", autoFit: "none" };
    addText(slide, name, { left: x - 55, top: 330, width: 184, height: 42 }, { typeface: HEAD, fontSize: 27, bold: true, color: COLORS.h3, alignment: "center" });
    addText(slide, desc, { left: x - 65, top: 382, width: 204, height: 82 }, { fontSize: 21, color: COLORS.muted, alignment: "center" });
  });
  addCallout(slide, { left: 165, top: 530, width: 950, height: 92 }, COLORS.warm, COLORS.warmBorder,
    "Resultado: 3.270 curvas comparables; 28 días faltantes quedan señalados y 2026 conserva la marca de año parcial.", { fontSize: 26, bold: true });
}

// 9. FPCA
{
  const slide = createContentSlide("FPCA por tipo de día", [
    "Explicar que la curva tiene 96 intervalos y que FPCA la resume en 2 o 3 componentes.",
    "Los scores no se comparan entre segmentos porque cada tipo de día tiene su propio modelo.",
    "La posición sobre los ejes transmite el patrón y la magnitud; el color funciona como apoyo, no como único canal de lectura.",
    "La curva negra ofrece máximo contraste sobre fondo claro y la barra amarilla subraya el umbral explicado con la identidad del Subte.",
  ], [
    "subte_fpca_work/resultados/varianza_fpca_segmentada.csv",
    "subte_fpca_work/resultados/resumen_modelos_segmentados.csv",
    "subte_fpca_work/resultados/horarios_mayor_contribucion.csv",
    "Day1_3_Data_Visualization_Color.pdf, variables ordenadas: posición, tamaño y valor",
  ]);
  const labC1 = clusterProfiles["Laborable::LAB-C1"];
  const curveChart = slide.charts.add("line", {
    position: { left: 55, top: 158, width: 560, height: 345 },
    title: "Curva diaria normalizada · LAB-C1",
    titleTextStyle: { typeface: HEAD, fontSize: 22, fill: COLORS.h3, bold: true },
    categories: hourCategories,
    series: [{ name: "Participación por hora", values: labC1, line: { style: "solid", fill: COLORS.h2, width: 3 }, marker: { symbol: "none" } }],
    hasLegend: false,
    xAxis: { textStyle: { typeface: BODY, fontSize: 13, fill: COLORS.muted }, majorGridlines: null, line: { style: "solid", fill: COLORS.rule, width: 1 } },
    yAxis: { visible: false, majorGridlines: null },
    chartFill: COLORS.white,
    plotAreaFill: COLORS.white,
  });
  styleChart(curveChart);
  const varianceChart = slide.charts.add("bar", {
    position: { left: 660, top: 158, width: 560, height: 345 },
    title: "Varianza acumulada al alcanzar el umbral",
    titleTextStyle: { typeface: HEAD, fontSize: 22, fill: COLORS.h3, bold: true },
    categories: varianceSummary.map((r) => r.segment.replace("Domingo/Feriado", "Domingo/feriado")),
    series: [{
      name: "Varianza acumulada",
      values: varianceSummary.map((r) => r.variance),
      valuesFormatCode: "0.0%",
      fill: COLORS.yellow,
    }],
    barOptions: { direction: "bar", grouping: "clustered", gapWidth: 52 },
    hasLegend: false,
    xAxis: { min: 0, max: 1, numberFormatCode: "0%", majorGridlines: { style: "solid", fill: COLORS.grid, width: 1 }, textStyle: { typeface: BODY, fontSize: 13, fill: COLORS.muted } },
    yAxis: { textStyle: { typeface: BODY, fontSize: 15, fill: COLORS.ink }, majorGridlines: null, line: { style: "solid", fill: COLORS.rule, width: 1 } },
    dataLabels: { showValue: true, position: "outEnd", textStyle: { typeface: BODY, fontSize: 15, fill: COLORS.ink, bold: true } },
    chartFill: COLORS.white,
    plotAreaFill: COLORS.white,
  });
  styleChart(varianceChart);
  addCallout(slide, { left: 105, top: 545, width: 1070, height: 92 }, COLORS.yellowSoft, COLORS.yellow,
    "Laborables: 2 FPC explican 90,2%; sábados y domingos/feriados requieren 3. FPC1 destaca 08:15 y FPC2, 17:45.", { fontSize: 25, bold: true });
}

// 10. Section
createSectionSlide("Resultados", "Evolución de red, perfiles recurrentes y casos reales", [
  "Transición hacia resultados.",
], ["subte_fpca_work/resultados/resumen_automatico.md"]);

// 11. Evolution
{
  const slide = createContentSlide("2025 alcanza 51% del nivel de 2019", [
    "Presentar la expansión hasta 2019, la ruptura de 2020–2021 y la recuperación posterior.",
    "Aclarar que la mediana de red da contexto general y que 2026 es parcial.",
    "La serie principal se mantiene negra para continuidad. El rojo señala la ruptura pandémica y el amarillo el año parcial: ambos colores se acompañan con año y etiqueta.",
    "Esta redundancia evita que la interpretación dependa solamente del contraste cromático rojo-verde.",
  ], [
    "subte_fpca_work/resultados/serie_diaria_red.csv",
    "subte_fpca_work/resultados/cobertura_temporal_anios.csv",
    "Day1_3_Data_Visualization_Color.pdf, espacios oponentes y accesibilidad cromática",
  ]);
  const trend = slide.charts.add("line", {
    position: { left: 68, top: 165, width: 820, height: 410 },
    title: "Evolución anual de la mediana diaria",
    titleTextStyle: { typeface: HEAD, fontSize: 22, fill: COLORS.h3, bold: true },
    categories: annualYears.map(String),
    series: [{
      name: "Millones de validaciones",
      values: annualValues,
      line: { style: "solid", fill: COLORS.h2, width: 3 },
      marker: { symbol: "circle", size: 6 },
      points: [
        { idx: annualYears.indexOf(2020), fill: "#DC2626" },
        { idx: annualYears.indexOf(2021), fill: "#DC2626" },
        { idx: annualYears.indexOf(2026), fill: COLORS.warmBorder },
      ],
    }],
    hasLegend: false,
    xAxis: { textStyle: { typeface: BODY, fontSize: 14, fill: COLORS.muted }, majorGridlines: null, line: { style: "solid", fill: COLORS.rule, width: 1 } },
    yAxis: { min: 0, max: 1.3, majorUnit: 0.25, numberFormatCode: "0.0\" M\"", textStyle: { typeface: BODY, fontSize: 14, fill: COLORS.muted }, majorGridlines: { style: "solid", fill: COLORS.grid, width: 1 } },
    chartFill: COLORS.white,
    plotAreaFill: COLORS.white,
  });
  styleChart(trend);
  addBox(slide, { left: 925, top: 162, width: 285, height: 392 }, COLORS.warm, { borderRadius: 16 });
  const highlights = [
    ["2019", `${value2019.toFixed(2).replace(".", ",")} M`, "máximo pre-pandemia"],
    ["2020", `${annualValues[annualYears.indexOf(2020)].toFixed(2).replace(".", ",")} M`, "ruptura extraordinaria"],
    ["2025", `${value2025.toFixed(2).replace(".", ",")} M`, "último año completo"],
  ];
  highlights.forEach(([year, value, note], i) => {
    const y = 190 + i * 105;
    addText(slide, year, { left: 954, top: y, width: 70, height: 34 }, { fontSize: 23, bold: true, color: COLORS.h3 });
    addText(slide, value, { left: 1030, top: y - 5, width: 150, height: 42 }, { fontSize: 31, bold: true, color: COLORS.ink });
    addText(slide, note, { left: 954, top: y + 42, width: 226, height: 34 }, { fontSize: 18, color: COLORS.muted });
  });
  addText(slide, "2026: enero–junio", { left: 954, top: 505, width: 226, height: 32 }, { fontSize: 20, bold: true, color: COLORS.ink });
  addCallout(slide, { left: 160, top: 592, width: 960, height: 56 }, COLORS.blueSoft, COLORS.blueBorder,
    `La comparación 2019–2025 muestra recuperación parcial: ${(recoveryRatio * 100).toFixed(0)}% del nivel diario.`, { fontSize: 24, bold: true, barWidth: 6 });
}

// 12. Profiles
{
  const slide = createContentSlide("Perfiles horarios por tipo de día", [
    "Mostrar que los clusters describen formas, no tamaños de estación.",
    "La estructura del sábado es más continua y tiene una silhouette más moderada.",
    "Los perfiles combinan tono con marcas distintas para que cada cluster siga siendo identificable sin depender solo del color.",
    "El amarillo se usa como acento dominante y el cian como contraste frío; el negro sostiene jerarquía y legibilidad.",
  ], [
    "subte_fpca_work/resultados/caracterizacion_clusters.csv",
    "subte_fpca_work/resultados/perfiles_suavizados_segmentados.csv",
    "subte_fpca_work/resultados/resumen_modelos_segmentados.csv",
    "Day1_3_Data_Visualization_Color.pdf, armonías, complementarios y redundancia visual",
  ]);
  const configs = [
    { segment: "Laborable", clusters: ["LAB-C1", "LAB-C2"], left: 35, width: 390 },
    { segment: "Sábado", clusters: ["SAB-C1", "SAB-C2", "SAB-C3"], left: 445, width: 390 },
    { segment: "Domingo/Feriado", clusters: ["DOM-C1", "DOM-C2"], left: 855, width: 390 },
  ];
  const palette = [COLORS.ink, COLORS.yellow, COLORS.cyan];
  const markers = ["circle", "square", "triangle"];
  configs.forEach((cfg) => {
    const chart = slide.charts.add("line", {
      position: { left: cfg.left, top: 155, width: cfg.width, height: 375 },
      title: cfg.segment.replace("Domingo/Feriado", "Domingo / feriado"),
      titleTextStyle: { typeface: HEAD, fontSize: 22, fill: COLORS.h3, bold: true },
      categories: hourCategories,
      series: cfg.clusters.map((cluster, i) => ({
        name: cluster,
        values: clusterProfiles[`${cfg.segment}::${cluster}`],
        line: { style: "solid", fill: palette[i], width: 3 },
        marker: { symbol: markers[i], size: 4 },
      })),
      hasLegend: true,
      legend: { position: "bottom", overlay: false, textStyle: { typeface: BODY, fontSize: 14, fill: COLORS.ink } },
      xAxis: { textStyle: { typeface: BODY, fontSize: 12, fill: COLORS.muted }, majorGridlines: null, line: { style: "solid", fill: COLORS.rule, width: 1 } },
      yAxis: { visible: false, majorGridlines: null },
      chartFill: COLORS.white,
      plotAreaFill: COLORS.white,
    });
    styleChart(chart);
    const meta = varianceSummary.find((r) => r.segment === cfg.segment);
    addText(slide, `k=${meta.k} · silhouette ${meta.silhouette.toFixed(3).replace(".", ",")} · ARI ${meta.ari.toFixed(3).replace(".", ",")}`,
      { left: cfg.left + 10, top: 535, width: cfg.width - 20, height: 32 }, { fontSize: 17, color: COLORS.muted, alignment: "center" });
  });
  addCallout(slide, { left: 165, top: 575, width: 950, height: 72 }, COLORS.warm, COLORS.warmBorder,
    "Siete formas recurrentes: mañana o tarde en laborables; transición al mediodía y la tarde en fines de semana.", { fontSize: 23, bold: true });
}

// 13. Changes table
{
  const slide = createContentSlide("Cambio de forma y estabilidad", [
    "La distancia en scores mide cambio de forma dentro del mismo segmento.",
    "General San Martín conserva el cluster laborable, pero se mueve más que cualquier otra estación entre 2019 y 2025.",
  ], ["subte_fpca_work/resultados/cambios_2019_2025_por_segmento.csv"]);
  const values = [
    ["Segmento", "Estación", "Distancia", "Cluster 2019 / 2025", "Volumen 2025 / 2019"],
    ...topChanges.map((r) => [
      r.segmento_dia.replace("Domingo/Feriado", "Dom./fer."),
      r.estacion_id,
      r.distancia_scores.toFixed(3).replace(".", ","),
      `${r.cluster_pre} / ${r.cluster_post}`,
      `${Math.round(r.ratio_pax_post_pre * 100)}%`,
    ]),
  ];
  const table = slide.tables.add({
    rows: values.length,
    columns: values[0].length,
    left: 60,
    top: 160,
    width: 1160,
    height: 360,
    columnTracks: [
      { mode: "fixed", value: 160 },
      { mode: "fr", value: 2.3 },
      { mode: "fixed", value: 135 },
      { mode: "fr", value: 1.7 },
      { mode: "fixed", value: 185 },
    ],
    values,
  });
  table.styleOptions = { headerRow: true, bandedRows: true };
  table.borders.assign({ style: "solid", fill: COLORS.rule, width: 1 });
  table.cells.block({ row: 0, column: 0, rowCount: 1, columnCount: 5 }).assign({
    fill: COLORS.h1,
    textStyle: { typeface: BODY, fontSize: 17, color: COLORS.white, bold: true },
    margins: { top: 8, right: 9, bottom: 8, left: 9 },
    anchor: "middle",
  });
  table.cells.block({ row: 1, column: 0, rowCount: 5, columnCount: 5 }).assign({
    textStyle: { typeface: BODY, fontSize: 17, color: COLORS.ink },
    margins: { top: 8, right: 9, bottom: 8, left: 9 },
    anchor: "middle",
  });
  table.cells.block({ row: 1, column: 0, rowCount: 1, columnCount: 5 }).fill = COLORS.warm;
  addCallout(slide, { left: 105, top: 560, width: 1070, height: 86 }, COLORS.blueSoft, COLORS.blueBorder,
    "C · General San Martín: distancia 1,449; conserva LAB-C2 y el volumen 2025 equivale al 41% de 2019.", { fontSize: 26, bold: true });
}

// 14. MaxVol
{
  const slide = createContentSlide("MaxVol selecciona ejemplos reales", [
    "Explicar que MaxVol selecciona perfiles extremos y observados, no centroides ni clusters nuevos.",
    "Los años pandémicos o parciales requieren contexto adicional.",
  ], [
    "subte_fpca_work/resultados/prototipos_maxvol.csv",
    "subte_fpca_work/resultados/interpretacion_clusters_maxvol.md",
  ]);
  const fills = [COLORS.blue, COLORS.warm, COLORS.purple];
  const labels = ["punta matutina", "tarde pospandemia", "tarde concentrada"];
  selectedPrototypes.forEach((r, i) => {
    const x = 65 + i * 405;
    addBox(slide, { left: x, top: 160, width: 350, height: 390 }, fills[i], { borderRadius: 16 });
    addText(slide, r.prototipo_maxvol, { left: x + 24, top: 184, width: 120, height: 30 }, { fontSize: 18, bold: true, color: COLORS.h3 });
    addText(slide, `${r.linea} · ${r.estacion.replaceAll("PZA.", "Pza.").toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase())}`,
      { left: x + 24, top: 228, width: 300, height: 86 }, { typeface: HEAD, fontSize: 32, bold: true, color: COLORS.ink });
    addText(slide, `${r.anio} · ${r.cluster_id}`, { left: x + 24, top: 320, width: 300, height: 30 }, { fontSize: 20, color: COLORS.muted });
    addText(slide, r.hora_pico, { left: x + 24, top: 375, width: 130, height: 52 }, { fontSize: 39, bold: true, color: COLORS.h1 });
    addText(slide, "hora pico", { left: x + 166, top: 390, width: 130, height: 28 }, { fontSize: 19, color: COLORS.muted });
    const share = Math.max(Number(r.share_06_10), Number(r.share_10_16), Number(r.share_16_21), Number(r.share_21_24));
    addText(slide, `${Math.round(share * 100)}%`, { left: x + 24, top: 445, width: 100, height: 44 }, { fontSize: 34, bold: true, color: COLORS.ink });
    addText(slide, "en su franja principal", { left: x + 132, top: 454, width: 190, height: 30 }, { fontSize: 18, color: COLORS.muted });
    addText(slide, labels[i], { left: x + 24, top: 510, width: 300, height: 28 }, { fontSize: 19, bold: true, color: COLORS.h3 });
  });
  addCallout(slide, { left: 175, top: 575, width: 930, height: 72 }, COLORS.blueSoft, COLORS.blueBorder,
    "Son perfiles observados en los bordes del espacio FPCA: ayudan a interpretar, pero no representan promedios.", { fontSize: 23, bold: true });
}

// 15. Coordinated views
{
  const slide = createContentSlide("Vistas coordinadas e interacción", [
    "Explicar linking and brushing con ejemplos de acciones del usuario.",
    "La selección persistente usa la estación como clave y combina selecciones por intersección.",
    "La opacidad disminuye el peso del contexto no seleccionado; el tono y el contorno mantienen visibles las estaciones activas.",
    "El diseño conserva color, posición y etiquetas como señales redundantes para reforzar el mensaje.",
  ], [
    "creacion_dashboard.ipynb, GRAFICOS_VINCULADOS y callbacks",
    "subte_fpca_work/documentacion/actualizar_bitacora.py, secciones 6.5–6.6",
    "Day1_3_Data_Visualization_Color.pdf, valor, saturación, brillo y percepción selectiva",
  ]);
  const values = [
    ["Acción", "Vistas que cambian", "Tarea que resuelve"],
    ["Tipo de día, año y líneas", "Tarjetas, mapa, heatmap, matriz, evolución y FPCA", "Comparar escenarios con el mismo universo"],
    ["Lazo o clic sobre un gráfico", "Las 10 vistas vinculadas resaltan las mismas estaciones", "Seguir casos entre geografía, volumen y forma"],
    ["Cruzar selecciones", "Se conserva la intersección de estaciones", "Aislar casos que cumplen más de un criterio"],
    ["Reproducir o pausar la hora", "El mapa se anima; al pausar, la hora se marca en gráficos temporales", "Relacionar el pulso geográfico con el perfil horario"],
  ];
  const table = slide.tables.add({
    rows: 5,
    columns: 3,
    left: 65,
    top: 150,
    width: 1150,
    height: 390,
    columnTracks: [{ mode: "fr", value: 1.25 }, { mode: "fr", value: 2.25 }, { mode: "fr", value: 2 }],
    values,
  });
  table.styleOptions = { headerRow: true, bandedRows: true };
  table.borders.assign({ style: "solid", fill: COLORS.rule, width: 1 });
  table.cells.block({ row: 0, column: 0, rowCount: 1, columnCount: 3 }).assign({
    fill: COLORS.h1,
    textStyle: { typeface: BODY, fontSize: 18, color: COLORS.white, bold: true },
    margins: { top: 9, right: 10, bottom: 9, left: 10 },
    anchor: "middle",
  });
  table.cells.block({ row: 1, column: 0, rowCount: 4, columnCount: 3 }).assign({
    textStyle: { typeface: BODY, fontSize: 18, color: COLORS.ink },
    margins: { top: 10, right: 10, bottom: 10, left: 10 },
    anchor: "middle",
  });
  addCallout(slide, { left: 110, top: 570, width: 1060, height: 70 }, COLORS.warm, COLORS.warmBorder,
    "Tres recorridos: Resumen de red, Detalle de estación y Patrones FPCA. Los filtros globales se conservan entre pestañas.", { fontSize: 24, bold: true });
}

// 16. Conclusion
{
  const slide = createContentSlide("Conclusiones y alcance", [
    "Cerrar respondiendo la pregunta guía.",
    "Distinguir hallazgos, contribución visual y límites.",
  ], [
    "subte_fpca_work/resultados/resumen_automatico.md",
    "subte_fpca_work/documentacion/generar_presentacion_proyecto.py, secciones 7–9",
  ]);
  addBullets(slide, [
    "La forma horaria agrega información que el total diario no muestra.",
    "Los modelos separados por tipo de día evitan que el calendario domine la comparación.",
    "FPCA y clustering ordenan patrones; MaxVol aporta casos reales para interpretarlos.",
    "Las vistas coordinadas conectan geografía, evolución y perfiles mediante la selección de estaciones.",
  ], { left: 105, top: 160, width: 1070, height: 320, fontSize: 30, spaceAfterPoints: 15 });
  addCallout(slide, { left: 120, top: 515, width: 1040, height: 105 }, COLORS.yellowSoft, COLORS.yellow,
    "Límites: el análisis es descriptivo; 2020–2021 y 2026 requieren contexto; la demanda observada no equivale a capacidad ni explica causas.", { fontSize: 27, bold: true });
  addText(slide, "La contribución principal es una lectura reproducible del pulso de la red.", { left: 170, top: 625, width: 940, height: 60 }, {
    fontSize: 22,
    bold: true,
    color: COLORS.h1,
    alignment: "center",
  });
}

await fs.mkdir(TMP_DIR, { recursive: true });
await fs.mkdir(path.dirname(FINAL_PPTX), { recursive: true });

const inspection = await presentation.inspect({
  kind: "slide,textbox,shape,table,chart,notes",
  include: "id,slide,name,title,textPreview,bbox,rows,cols,chartType",
  maxChars: 50000,
});
await fs.writeFile(path.join(TMP_DIR, "subte-moving-final-inspection.ndjson"), inspection.ndjson, "utf8");

const candidatePath = path.join(TMP_DIR, "candidate-subte-moving-final.pptx");
await (await PresentationFile.exportPptx(presentation)).save(candidatePath);

const requirements = {
  explicitTotalSlideCount: 16,
  requiredNativeTableOwnerSlides: [13, 15],
  requiredNativeChartOwnerSlides: [9, 11, 12],
  materializeLiteralChartWorkbooks: true,
  nativeChartTargetApplication: "portable",
};

const result = await finalizePresentation({
  ...requirements,
  workspaceDir,
  candidatePath,
  finalPath: FINAL_PPTX,
  pythonExecutable: RUNTIME_PYTHON,
  integrityValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_layout_geometry.py"),
  layoutArgs: [
    "--expected-slide-size-emu", "12192000,6858000",
    "--validate-bullet-geometry",
    "--validate-heading-fit",
    "--require-native-table-slide", "13",
    "--require-native-table-slide", "15",
  ],
  requiredNativeTableOwnerSlides: [13, 15],
  requiredNativeChartOwnerSlides: [9, 11, 12],
  materializeLiteralChartWorkbooks: true,
  nativeChartTargetApplication: "portable",
  fontPolicy: { basis: "design", families: [HEAD, BODY] },
  verifyArtifactToolImport: true,
  receiptPath: path.join(TMP_DIR, "subte-moving-final.validation.json"),
});

console.log(JSON.stringify({
  finalPath: result.finalPath,
  receiptPath: result.receiptPath,
  slideCount: presentation.slides.items.length,
  chartOwners: result.nativeChartValidation?.detectedOwnerSlides,
}, null, 2));
