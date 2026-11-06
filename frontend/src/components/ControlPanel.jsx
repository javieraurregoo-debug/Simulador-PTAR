import { fmt } from "../lib/format.js";

const GRUPOS = [
  {
    id: "influente",
    titulo: "Agua residual cruda",
    descripcion:
      "Caracterización convencional que se fracciona en COD, nitrógeno y fósforo para el modelo ASM1 reducido.",
    abierto: true,
    campos: [
      {
        path: "influente.caudal_m3_d",
        label: "Caudal medio",
        unidad: "m³/d",
        min: 100,
        max: 200000,
        step: 100,
      },
      {
        path: "influente.dbo5_mg_l",
        label: "DBO₅",
        unidad: "mg/L",
        min: 10,
        max: 5000,
        step: 10,
      },
      {
        path: "influente.dqo_mg_l",
        label: "DQO total",
        unidad: "mg/L",
        min: 20,
        max: 15000,
        step: 10,
      },
      {
        path: "influente.sst_mg_l",
        label: "SST",
        unidad: "mg/L",
        min: 10,
        max: 8000,
        step: 10,
      },
      {
        path: "influente.ssv_mg_l",
        label: "SSV",
        unidad: "mg/L",
        min: 0,
        max: 8000,
        step: 10,
      },
      {
        path: "influente.ntk_mg_l",
        label: "NTK",
        unidad: "mg N/L",
        min: 0,
        max: 2000,
        step: 1,
      },
      {
        path: "influente.nh4_mg_l",
        label: "N-NH₄",
        unidad: "mg N/L",
        min: 0,
        max: 2000,
        step: 1,
      },
      {
        path: "influente.pt_mg_l",
        label: "Fósforo total",
        unidad: "mg P/L",
        min: 0,
        max: 400,
        step: 0.5,
      },
      {
        path: "influente.po4_mg_l",
        label: "P-PO₄",
        unidad: "mg P/L",
        min: 0,
        max: 400,
        step: 0.5,
      },
      {
        path: "influente.ph",
        label: "pH",
        unidad: "–",
        min: 4,
        max: 10,
        step: 0.1,
      },
      {
        path: "influente.temperatura_c",
        label: "Temperatura",
        unidad: "°C",
        min: 2,
        max: 45,
        step: 0.5,
      },
      {
        path: "influente.alcalinidad_mg_l",
        label: "Alcalinidad",
        unidad: "mg CaCO₃/L",
        min: 5,
        max: 3000,
        step: 10,
      },
    ],
  },
  {
    id: "biologico",
    titulo: "Reactor A2O",
    descripcion:
      "Volúmenes, recirculaciones y control del lodo. La purga y el área del clarificador definen la SRT y la calidad del efluente.",
    abierto: true,
    campos: [
      {
        path: "diseno.biologico.volumen_anaerobio_m3",
        label: "Volumen anaerobio",
        unidad: "m³",
        min: 10,
        max: 100000,
        step: 50,
      },
      {
        path: "diseno.biologico.volumen_anoxico_m3",
        label: "Volumen anóxico",
        unidad: "m³",
        min: 10,
        max: 100000,
        step: 50,
      },
      {
        path: "diseno.biologico.volumen_aerobio_m3",
        label: "Volumen aerobio",
        unidad: "m³",
        min: 10,
        max: 500000,
        step: 100,
      },
      {
        path: "diseno.biologico.ras",
        label: "Recirculación RAS",
        unidad: "Q/Q",
        min: 0.1,
        max: 3,
        step: 0.05,
      },
      {
        path: "diseno.biologico.recirculacion_interna",
        label: "Recirculación interna",
        unidad: "Q/Q",
        min: 0,
        max: 6,
        step: 0.1,
      },
      {
        path: "diseno.biologico.purga_m3_d",
        label: "Purga de lodos",
        unidad: "m³/d",
        min: 0.1,
        max: 50000,
        step: 5,
      },
      {
        path: "diseno.biologico.od_aerobio_mg_l",
        label: "OD aerobio",
        unidad: "mg/L",
        min: 0.2,
        max: 8,
        step: 0.1,
      },
      {
        path: "diseno.biologico.od_anoxico_mg_l",
        label: "OD anóxico",
        unidad: "mg/L",
        min: 0,
        max: 1,
        step: 0.05,
      },
      {
        path: "diseno.biologico.svi_ml_g",
        label: "SVI",
        unidad: "mL/g",
        min: 40,
        max: 400,
        step: 5,
      },
      {
        path: "diseno.biologico.area_secundario_m2",
        label: "Área clarificador",
        unidad: "m²",
        min: 10,
        max: 50000,
        step: 10,
      },
      {
        path: "diseno.biologico.dias_simulacion",
        label: "Días de simulación",
        unidad: "d",
        min: 30,
        max: 365,
        step: 10,
      },
    ],
  },
  {
    id: "primario",
    titulo: "Pretratamiento y primario",
    descripcion:
      "Las rejillas retiran sólidos gruesos, el desarenador separa arenas y el sedimentador primario alivia la carga del reactor.",
    campos: [
      {
        path: "diseno.pretratamiento.abertura_rejillas_mm",
        label: "Abertura de rejillas",
        unidad: "mm",
        min: 3,
        max: 100,
        step: 1,
      },
      {
        path: "diseno.pretratamiento.velocidad_rejillas_m_s",
        label: "Velocidad en rejillas",
        unidad: "m/s",
        min: 0.2,
        max: 1.5,
        step: 0.05,
      },
      {
        path: "diseno.pretratamiento.trh_desarenador_s",
        label: "TRH desarenador",
        unidad: "s",
        min: 10,
        max: 600,
        step: 5,
      },
      {
        path: "diseno.primario.n_unidades",
        label: "Unidades primarias",
        unidad: "–",
        min: 1,
        max: 8,
        step: 1,
      },
      {
        path: "diseno.primario.diametro_m",
        label: "Diámetro",
        unidad: "m",
        min: 2,
        max: 60,
        step: 0.5,
      },
      {
        path: "diseno.primario.profundidad_m",
        label: "Profundidad",
        unidad: "m",
        min: 1,
        max: 8,
        step: 0.1,
      },
      {
        path: "diseno.primario.v50_m_d",
        label: "Velocidad límite v₅₀",
        unidad: "m/d",
        min: 5,
        max: 200,
        step: 1,
      },
    ],
  },
  {
    id: "desinfeccion",
    titulo: "Desinfección",
    descripcion:
      "El método y la dosis determinan la inactivación de coliformes y el consumo de reactivos.",
    campos: [
      {
        path: "diseno.desinfeccion.metodo",
        label: "Método",
        tipo: "select",
        opciones: [
          { value: "cloro", label: "Cloro" },
          { value: "uv", label: "Radiación UV" },
          { value: "ozono", label: "Ozono" },
          { value: "ninguno", label: "Sin desinfección" },
        ],
      },
      {
        path: "diseno.desinfeccion.dosis_cloro_mg_l",
        label: "Dosis de cloro",
        unidad: "mg/L",
        min: 0,
        max: 50,
        step: 0.5,
      },
      {
        path: "diseno.desinfeccion.tiempo_contacto_min",
        label: "Tiempo de contacto",
        unidad: "min",
        min: 0,
        max: 240,
        step: 5,
      },
      {
        path: "diseno.desinfeccion.dosis_uv_mj_cm2",
        label: "Dosis UV",
        unidad: "mJ/cm²",
        min: 0,
        max: 500,
        step: 5,
      },
    ],
  },
  {
    id: "limites",
    titulo: "Límites de descarga",
    descripcion:
      "Referencia normativa configurable para evaluar el cumplimiento del efluente.",
    campos: [
      {
        path: "limites.dbo5_mg_l",
        label: "DBO₅ máxima",
        unidad: "mg/L",
        min: 1,
        max: 500,
        step: 5,
      },
      {
        path: "limites.dqo_mg_l",
        label: "DQO máxima",
        unidad: "mg/L",
        min: 1,
        max: 1000,
        step: 10,
      },
      {
        path: "limites.sst_mg_l",
        label: "SST máximos",
        unidad: "mg/L",
        min: 1,
        max: 500,
        step: 5,
      },
      {
        path: "limites.nt_mg_l",
        label: "N total máximo",
        unidad: "mg/L",
        min: 1,
        max: 200,
        step: 1,
      },
      {
        path: "limites.pt_mg_l",
        label: "P total máximo",
        unidad: "mg/L",
        min: 0.1,
        max: 50,
        step: 0.5,
      },
      {
        path: "limites.ph_min",
        label: "pH mínimo",
        unidad: "–",
        min: 0,
        max: 14,
        step: 0.1,
      },
      {
        path: "limites.ph_max",
        label: "pH máximo",
        unidad: "–",
        min: 0,
        max: 14,
        step: 0.1,
      },
      {
        path: "limites.coliformes_ufc_100ml",
        label: "Coliformes",
        unidad: "UFC/100 mL",
        min: 1,
        max: 1e9,
        step: 100,
      },
    ],
  },
];

function leer(obj, path) {
  return path.split(".").reduce((acc, key) => (acc == null ? acc : acc[key]), obj);
}

function Campo({ campo, payload, onChange }) {
  const valor = leer(payload, campo.path);
  const id = `campo-${campo.path.replace(/\./g, "-")}`;

  if (campo.tipo === "select") {
    return (
      <label className="field field-select" htmlFor={id}>
        <span className="field-label">{campo.label}</span>
        <select
          id={id}
          value={valor ?? ""}
          onChange={(e) => onChange(campo.path, e.target.value)}
        >
          {campo.opciones.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </label>
    );
  }

  return (
    <label className="field" htmlFor={id}>
      <span className="field-label">
        {campo.label}
        {campo.unidad && campo.unidad !== "–" ? (
          <em>{campo.unidad}</em>
        ) : null}
      </span>
      <input
        id={id}
        type="number"
        inputMode="decimal"
        value={valor ?? ""}
        min={campo.min}
        max={campo.max}
        step={campo.step}
        onChange={(e) => {
          const n = e.target.valueAsNumber;
          if (Number.isFinite(n)) onChange(campo.path, n);
        }}
      />
    </label>
  );
}

export default function ControlPanel({ payload, onChange, onReset, presetNombre }) {
  if (!payload) {
    return (
      <aside className="control-panel">
        <div className="panel-skeleton" aria-hidden="true" />
      </aside>
    );
  }

  const q = Number(leer(payload, "influente.caudal_m3_d") || 0);
  const dbo = Number(leer(payload, "influente.dbo5_mg_l") || 0);
  const dqo = Number(leer(payload, "influente.dqo_mg_l") || 0);
  const carga = (q * dbo) / 1000;

  return (
    <aside className="control-panel" aria-label="Parámetros de diseño">
      <div className="control-head">
        <div>
          <h2>Parámetros</h2>
          <p>{presetNombre || "Escenario personalizado"}</p>
        </div>
        <button type="button" className="btn-ghost" onClick={onReset}>
          Restablecer
        </button>
      </div>

      <div className="control-summary">
        <div>
          <small>Carga DBO₅</small>
          <b>{fmt(carga)} kg/d</b>
        </div>
        <div>
          <small>DQO/DBO₅</small>
          <b>{dbo > 0 ? fmt(dqo / dbo, 2) : "—"}</b>
        </div>
        <div>
          <small>Caudal</small>
          <b>{fmt(q)} m³/d</b>
        </div>
      </div>

      <div className="control-scroll">
        {GRUPOS.map((grupo) => (
          <details key={grupo.id} className="field-group" open={grupo.abierto}>
            <summary>
              <span>{grupo.titulo}</span>
              <i aria-hidden="true" />
            </summary>
            <p className="field-group-desc">{grupo.descripcion}</p>
            <div className="field-grid">
              {grupo.campos.map((campo) => (
                <Campo
                  key={campo.path}
                  campo={campo}
                  payload={payload}
                  onChange={onChange}
                />
              ))}
            </div>
          </details>
        ))}

        <p className="control-note">
          Los valores se validan contra rangos fisicoquímicos. Modificar un
          parámetro marca la simulación como pendiente; pulse{" "}
          <strong>Simular cambios</strong> para recalcular el tren completo.
        </p>
      </div>
    </aside>
  );
}

export { GRUPOS };
