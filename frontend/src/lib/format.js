const nf = new Intl.NumberFormat("es-CO", {
  maximumFractionDigits: 0,
});

const nf1 = new Intl.NumberFormat("es-CO", {
  minimumFractionDigits: 0,
  maximumFractionDigits: 1,
});

const nf2 = new Intl.NumberFormat("es-CO", {
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});

export function fmt(value, digits = 0) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "—";
  }
  if (digits >= 2) return nf2.format(Number(value));
  if (digits === 1) return nf1.format(Number(value));
  return nf.format(Number(value));
}

export function fmtPct(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "—";
  }
  return `${fmt(value, digits)} %`;
}

export function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

/** Convierte un COD (mg/L) en un color de agua: ámbar sucio → cian limpio. */
export function qualityHex(cod) {
  const t = clamp((Number(cod) - 20) / 430, 0, 1);
  const hue = 195 - 165 * t;
  const sat = 68 - 18 * t;
  const light = 46 - 6 * t;
  return hslToHex(hue, sat, light);
}

export function qualityLabel(cod) {
  const c = Number(cod);
  if (!Number.isFinite(c)) return "sin dato";
  if (c < 40) return "excelente";
  if (c < 90) return "buena";
  if (c < 180) return "regular";
  return "cargada";
}

function hslToHex(h, s, l) {
  const sat = s / 100;
  const lig = l / 100;
  const k = (n) => (n + h / 30) % 12;
  const a = sat * Math.min(lig, 1 - lig);
  const f = (n) => lig - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)));
  const toHex = (x) =>
    Math.round(255 * x)
      .toString(16)
      .padStart(2, "0");
  return `#${toHex(f(0))}${toHex(f(8))}${toHex(f(4))}`;
}

export function humanKey(key) {
  return String(key)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .replace(/\bM3\b/g, "m³")
    .replace(/\bMg\b/g, "mg")
    .replace(/\bKg\b/g, "kg")
    .replace(/\bPct\b/g, "%")
    .replace(/\bDbo5\b/g, "DBO₅")
    .replace(/\bDqo\b/g, "DQO")
    .replace(/\bSst\b/g, "SST")
    .replace(/\bSsv\b/g, "SSV")
    .replace(/\bNtk\b/g, "NTK")
    .replace(/\bNh4\b/g, "NH₄")
    .replace(/\bNo3\b/g, "NO₃")
    .replace(/\bPo4\b/g, "PO₄")
    .replace(/\bOd\b/g, "OD")
    .replace(/\bPh\b/g, "pH")
    .replace(/\bSrt\b/g, "SRT")
    .replace(/\bSvi\b/g, "SVI")
    .replace(/\bOur\b/g, "OUR");
}

const UNIDADES = {
  caudal_m3_d: "m³/d",
  entrada_m3_d: "m³/d",
  salida_m3_d: "m³/d",
  rechazo_m3_d: "m³/d",
  filtrado_m3_d: "m³/d",
  torta_m3_d: "m³/d",
  recirculacion_m3_d: "m³/d",
  aire_m3_d: "m³/d",
  biogas_m3_d: "m³/d",
  metano_m3_d: "m³/d",
  volumen_m3: "m³",
  area_m2: "m²",
  energia_kwh_d: "kWh/d",
  energia_termica_kwh_d: "kWh/d",
  energia_aireacion_kw: "kW",
  potencia_sopladores_kw: "kW",
  carga_kg_d: "kg/d",
  carga_dqo_kg_d: "kg/d",
  carga_dbo5_kg_d: "kg/d",
  carga_sst_kg_d: "kg/d",
  kg_sst_d: "kg SST/d",
  solidos_kg_d: "kg/d",
  lodo_m3_d: "m³/d",
  torta_kg_sst_d: "kg SST/d",
  trh_h: "h",
  trh_s: "s",
  srt_d: "d",
  sor_m3_m2_d: "m³/(m²·d)",
  carga_solidos_kg_m2_d: "kg/(m²·d)",
  flujo_limite_kg_m2_d: "kg/(m²·d)",
  produccion_especifica_kg_sst_kg_dqo: "kg SST/kg DQO",
  fm_kg_cod_kg_ssv_d: "kg DQO/(kg SSV·d)",
  our_kg_o2_d: "kg O₂/d",
  aire_m3_por_m3_agua: "m³ aire/m³",
  inactivacion_log: "log",
  ct: "mg·min/L",
  dosis_cloro_mg_l: "mg/L",
  dosis_uv_mj_cm2: "mJ/cm²",
  recirculacion_pct: "%",
  autosuficiencia_energetica_pct: "%",
  recuperacion_agua_pct: "%",
  eficiencia_pct: "%",
  remocion_sst_pct: "%",
  remocion_cod_pct: "%",
  remocion_arena_pct: "%",
  remocion_dbo_pct: "%",
  eliminacion_pct: "%",
  cierre_pct: "%",
  punto_estado: "–",
  camiones_dia: "camiones/d",
  energia_kwh_por_m3: "kWh/m³",
  energia_especifica_kwh_kg_dqo: "kWh/kg DQO",
  concentracion_entrada_pct: "%",
  concentracion_pct: "%",
  inactivacion_log: "log",
  carga_kg_m2_d: "kg/(m²·d)",
  perdida_carga_m: "m",
  coliformes_salida: "UFC/100 mL",
};

export function unitFor(key) {
  if (UNIDADES[key]) return UNIDADES[key];
  if (key.endsWith("_mg_l")) return "mg/L";
  if (key.endsWith("_pct")) return "%";
  if (key.endsWith("_m3_d")) return "m³/d";
  if (key.endsWith("_m3")) return "m³";
  if (key.endsWith("_kg_d")) return "kg/d";
  if (key.endsWith("_kw")) return "kW";
  if (key.endsWith("_d")) return "d";
  if (key.endsWith("_h")) return "h";
  if (key.endsWith("_m")) return "m";
  if (key.endsWith("_c")) return "°C";
  if (key.endsWith("_ntu")) return "NTU";
  return "";
}

export function isNumeric(value) {
  return typeof value === "number" && Number.isFinite(value);
}

export function shortStage(nombre) {
  return String(nombre)
    .replace("Reactor A2O + sedimentador secundario", "A2O + clarificador")
    .replace("Sedimentador primario", "Primario")
    .replace("Sedimentador secundario", "Secundario")
    .replace("Rejillas de desbaste", "Rejillas")
    .replace("Espesador de lodos", "Espesador")
    .replace("Digestor anaerobio", "Digestor")
    .replace("Deshidratación", "Deshidratación")
    .replace("Desinfección", "Desinfección");
}
