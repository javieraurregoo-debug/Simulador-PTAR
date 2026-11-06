import { fmt, fmtPct, humanKey, unitFor } from "../lib/format.js";

function num(v, digits) {
  if (v === null || v === undefined || v === "") return "—";
  if (typeof v === "boolean") return v ? "Sí" : "No";
  if (typeof v === "number") {
    const d = digits ?? (Math.abs(v) < 10 ? 2 : Math.abs(v) < 100 ? 1 : 0);
    return fmt(v, d);
  }
  return String(v);
}

function valorConUnidad(key, value) {
  const u = unitFor(key);
  if (typeof value === "boolean") return value ? "Sí" : "No";
  if (typeof value !== "number") return String(value);
  return `${num(value)}${u ? ` ${u}` : ""}`;
}

const ETIQUETAS_CORRIENTE = [
  ["dqo_mg_l", "DQO"],
  ["dbo5_mg_l", "DBO₅"],
  ["sst_mg_l", "SST"],
  ["nt_mg_l", "N total"],
  ["pt_mg_l", "P total"],
  ["caudal_m3_d", "Caudal"],
];

function filasCorriente(corriente) {
  if (!corriente) return [];
  return ETIQUETAS_CORRIENTE.map(([key, label]) => [
    label,
    `${num(corriente[key])} ${unitFor(key)}`.trim(),
  ]);
}

function metricasCorriente(corriente) {
  if (!corriente) return [];
  return [
    { label: "DQO", value: num(corriente.dqo_mg_l), unit: "mg/L" },
    { label: "DBO₅", value: num(corriente.dbo5_mg_l), unit: "mg/L" },
    { label: "SST", value: num(corriente.sst_mg_l), unit: "mg/L" },
    { label: "Caudal", value: num(corriente.caudal_m3_d), unit: "m³/d" },
  ];
}

function objetoAFilas(obj, omitir = []) {
  if (!obj) return [];
  return Object.entries(obj)
    .filter(
      ([key, value]) =>
        !omitir.includes(key) &&
        (typeof value === "number" ||
          typeof value === "string" ||
          typeof value === "boolean"),
    )
    .map(([key, value]) => [humanKey(key), valorConUnidad(key, value)]);
}

function buscarEtapa(resultado, id) {
  return (resultado?.etapas || []).find((e) => e.id === id);
}

function construirDetalle(unidad, resultado) {
  if (!resultado) return { metricas: [], bloques: [] };
  const id = unidad.id;

  if (id === "afluente") {
    return {
      metricas: metricasCorriente(resultado.afluente),
      bloques: [
        {
          titulo: "Caracterización",
          filas: filasCorriente(resultado.afluente),
        },
        {
          titulo: "Indicadores de entrada",
          filas: objetoAFilas(resultado.caracterizacion, ["advertencias", "fracciones_cod"]),
        },
      ],
    };
  }

  if (id === "efluente") {
    const global = resultado.limites?.cumple_global;
    return {
      metricas: metricasCorriente(resultado.efluente),
      bloques: [
        {
          titulo: "Calidad final",
          filas: filasCorriente(resultado.efluente),
        },
        {
          titulo: "Cumplimiento",
          filas: [
            ["Estado global", global ? "Cumple" : "No cumple"],
            ...Object.entries(resultado.limites || {})
              .filter(([key, v]) => key !== "cumple_global" && v && typeof v === "object")
              .map(([key, v]) => [
                humanKey(key),
                `${num(v.valor)} ${v.limite || ""} · ${v.cumple ? "cumple" : "excede"}`,
              ]),
          ],
        },
      ],
    };
  }

  if (["anaerobio", "anoxico", "aerobio"].includes(id)) {
    const r = (resultado.reactores || []).find((x) => x.id === id);
    if (!r) return { metricas: [], bloques: [] };
    return {
      metricas: [
        { label: "Volumen", value: num(r.volumen_m3), unit: "m³" },
        { label: "TRH", value: num(r.trh_h), unit: "h" },
        { label: "SST", value: num(r.sst), unit: "mg/L" },
        { label: "OD", value: num(r.do), unit: "mg/L" },
      ],
      bloques: [
        {
          titulo: "Perfil del reactor",
          filas: [
            ["SSV", `${num(r.ssv)} mg/L`],
            ["Sustrato S_S", `${num(r.ss)} mg DQO/L`],
            ["Sustrato X_S", `${num(r.xs)} mg DQO/L`],
            ["Biomasa X_BH", `${num(r.xbh)} mg DQO/L`],
            ["Biomasa X_BA", `${num(r.xba)} mg DQO/L`],
            ["Inerte X_I", `${num(r.xi)} mg DQO/L`],
            ["N-NH₄", `${num(r.nh4)} mg N/L`],
            ["N-NO₃", `${num(r.sno)} mg N/L`],
            ["P-PO₄", `${num(r.spo4, 3)} mg P/L`],
            ["OUR", `${num(r.our_kg_d)} kg O₂/d`],
            ["pH", num(r.ph)],
            ["Alcalinidad", `${num(r.alk)} mg CaCO₃/L`],
          ],
        },
      ],
    };
  }

  if (id === "secundario") {
    const s = resultado.sedimentador_secundario || {};
    const bio = buscarEtapa(resultado, "biologico");
    return {
      metricas: [
        { label: "SST rebose", value: num(s.sst_rebose), unit: "mg/L" },
        { label: "SST purga", value: num(s.sst_purga), unit: "mg/L" },
        { label: "Eficiencia", value: num(s.eficiencia_pct), unit: "%" },
        { label: "Punto de estado", value: num(s.punto_estado), unit: "–" },
      ],
      bloques: [
        {
          titulo: "Operación del clarificador",
          filas: [
            ["Carga de sólidos", `${num(s.carga_solidos_kg_m2_d)} kg/(m²·d)`],
            ["Carga límite", `${num(s.carga_limite_kg_m2_d)} kg/(m²·d)`],
            ["Convergencia", s.convergido ? "Alcanzada" : "No alcanzada"],
            ["Residual numérico", num(s.residual, 6)],
            ["Días simulados", num(s.dias_simulados, 0)],
          ],
        },
        {
          titulo: "Salida del tren biológico",
          filas: filasCorriente(bio?.salida),
        },
      ],
    };
  }

  if (["espesador", "digestor", "deshidratacion"].includes(id)) {
    const etapa = (resultado.tren_lodos?.etapas || []).find((e) => e.id === id);
    if (!etapa) return { metricas: [], bloques: [] };
    return {
      metricas: [
        { label: "Entrada", value: num(etapa.entrada_kg_sst_d), unit: "kg SST/d" },
        { label: "Salida", value: num(etapa.salida_kg_sst_d), unit: "kg SST/d" },
        {
          label: id === "digestor" ? "Biogás" : "Rechazo",
          value: num(id === "digestor" ? etapa.biogas_m3_d : etapa.rechazo_m3_d),
          unit: id === "digestor" ? "m³/d" : "m³/d",
        },
        {
          label: id === "deshidratacion" ? "Torta" : "Concentración",
          value: num(id === "deshidratacion" ? etapa.torta_kg_sst_d : etapa.concentracion_pct),
          unit: id === "deshidratacion" ? "kg SST/d" : "%",
        },
      ],
      bloques: [
        {
          titulo: "Balance de la unidad",
          filas: objetoAFilas(etapa, ["id", "nombre", "detalle"]),
        },
      ],
    };
  }

  const etapa = buscarEtapa(resultado, id);
  if (!etapa) return { metricas: [], bloques: [] };

  return {
    metricas: [
      { label: "DQO salida", value: num(etapa.salida?.dqo_mg_l), unit: "mg/L" },
      { label: "SST salida", value: num(etapa.salida?.sst_mg_l), unit: "mg/L" },
      { label: "Remoción DQO", value: num(etapa.remocion?.dqo_pct), unit: "%" },
      { label: "Remoción SST", value: num(etapa.remocion?.sst_pct), unit: "%" },
    ],
    bloques: [
      { titulo: "Entrada", filas: filasCorriente(etapa.entrada) },
      { titulo: "Salida", filas: filasCorriente(etapa.salida) },
      {
        titulo: "Remoción",
        filas: [
          ["DBO₅", fmtPct(etapa.remocion?.dbo5_pct)],
          ["DQO", fmtPct(etapa.remocion?.dqo_pct)],
          ["SST", fmtPct(etapa.remocion?.sst_pct)],
          ["N total", fmtPct(etapa.remocion?.nt_pct)],
          ["P total", fmtPct(etapa.remocion?.tp_pct)],
        ],
      },
      {
        titulo: "Parámetros de diseño",
        filas: objetoAFilas(etapa.parametros),
      },
      {
        titulo: "Indicadores",
        filas: objetoAFilas(etapa.info),
      },
    ].filter((b) => b.filas.length),
  };
}

export default function UnitInspector({ unidad, resultado, onClose, onFocus }) {
  if (!unidad) return null;
  const detalle = construirDetalle(unidad, resultado);

  return (
    <aside className="unit-inspector" aria-label={`Detalle de ${unidad.nombre}`}>
      <header className="inspector-head">
        <span className={`unit-type tipo-${unidad.tipo}`}>{unidad.tipo}</span>
        <button type="button" className="inspector-close" onClick={onClose} aria-label="Cerrar detalle">
          ×
        </button>
        <h2>{unidad.nombre}</h2>
        <p>{unidad.descripcion}</p>
        <button type="button" className="btn-ghost btn-focus" onClick={() => onFocus(unidad.id)}>
          Enfocar en 3D
        </button>
      </header>

      {detalle.metricas.length ? (
        <div className="inspector-metrics">
          {detalle.metricas.map((m) => (
            <div key={m.label}>
              <small>{m.label}</small>
              <strong>{m.value}</strong>
              <span>{m.unit}</span>
            </div>
          ))}
        </div>
      ) : null}

      <div className="inspector-body">
        {detalle.bloques.map((bloque) => (
          <section key={bloque.titulo} className="inspector-block">
            <h3>{bloque.titulo}</h3>
            <dl>
              {bloque.filas.map(([label, value], i) => (
                <div key={`${label}-${i}`}>
                  <dt>{label}</dt>
                  <dd>{value}</dd>
                </div>
              ))}
            </dl>
          </section>
        ))}

        {!resultado ? (
          <p className="inspector-empty">
            Ejecute una simulación para ver los indicadores de esta unidad.
          </p>
        ) : null}
      </div>
    </aside>
  );
}
