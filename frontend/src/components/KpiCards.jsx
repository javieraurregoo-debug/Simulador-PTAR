import { fmt, fmtPct } from "../lib/format.js";

const PARAMETROS = [
  {
    key: "dbo5",
    nombre: "DBO₅",
    sigla: "DBO",
    color: "#a78bfa",
    descripcion: "Materia orgánica biodegradable",
  },
  {
    key: "dqo",
    nombre: "DQO",
    sigla: "DQO",
    color: "#38bdf8",
    descripcion: "Demanda química de oxígeno",
  },
  {
    key: "sst",
    nombre: "SST",
    sigla: "SST",
    color: "#fbbf24",
    descripcion: "Sólidos suspendidos totales",
  },
  {
    key: "nt",
    nombre: "N total",
    sigla: "N",
    color: "#34d399",
    descripcion: "Nitrógeno total",
  },
];

function nivelEficiencia(valor) {
  if (valor >= 90) return "alta";
  if (valor >= 75) return "media";
  if (valor >= 60) return "baja";
  return "critica";
}

function TarjetaParametro({ item, datos }) {
  const d = datos || {};
  const eficiencia = Number(d.eficiencia_pct || 0);
  const nivel = nivelEficiencia(eficiencia);
  return (
    <article className={`kpi-card nivel-${nivel}`} style={{ "--kpi-color": item.color }}>
      <div className="kpi-head">
        <span className="kpi-icon">{item.sigla}</span>
        <div>
          <h3>{item.nombre}</h3>
          <p>{item.descripcion}</p>
        </div>
      </div>
      <div className="kpi-values">
        <div>
          <strong>{fmt(d.salida, d.salida < 10 ? 1 : 0)}</strong>
          <span>mg/L salida</span>
        </div>
        <div className="kpi-entrada">
          <small>entrada</small>
          <b>{fmt(d.entrada)}</b>
        </div>
      </div>
      <div className="kpi-bar">
        <span style={{ width: `${Math.min(100, eficiencia)}%` }} />
      </div>
      <div className="kpi-foot">
        <span>Remoción</span>
        <b>{fmtPct(eficiencia)}</b>
      </div>
    </article>
  );
}

export default function KpiCards({ resultado }) {
  if (!resultado) {
    return (
      <section className="kpi-grid skeleton-grid" aria-hidden="true">
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <div className="kpi-card skeleton" key={i} />
        ))}
      </section>
    );
  }

  const { kpis } = resultado;
  const ica = kpis.indice_calidad || {};
  return (
    <section className="kpi-grid" aria-label="Indicadores de desempeño">
      {PARAMETROS.map((item) => (
        <TarjetaParametro key={item.key} item={item} datos={kpis[item.key]} />
      ))}

      <article className="kpi-card kpi-utility" style={{ "--kpi-color": "#22d3ee" }}>
        <div className="kpi-head">
          <span className="kpi-icon">⚡</span>
          <div>
            <h3>Energía</h3>
            <p>Biogás y aireación</p>
          </div>
        </div>
        <div className="kpi-utility-main">
          <strong>{fmt(kpis.autosuficiencia_energetica_pct)} %</strong>
          <span>autosuficiencia</span>
        </div>
        <div className="kpi-mini-grid">
          <div>
            <small>Aireación</small>
            <b>{fmt(kpis.energia_aireacion_kw, 1)} kW</b>
          </div>
          <div>
            <small>Biogás</small>
            <b>{fmt(kpis.energia_biogas_kwh_d)} kWh/d</b>
          </div>
        </div>
      </article>

      <article className="kpi-card kpi-utility" style={{ "--kpi-color": "#a3e635" }}>
        <div className="kpi-head">
          <span className="kpi-icon">◈</span>
          <div>
            <h3>Lodos</h3>
            <p>Producción y calidad</p>
          </div>
        </div>
        <div className="kpi-utility-main">
          <strong>{fmt(kpis.produccion_lodo_kg_sst_d)}</strong>
          <span>kg SST/d de torta</span>
        </div>
        <div className="kpi-mini-grid">
          <div>
            <small>Índice de calidad</small>
            <b>{fmt(ica.valor, 1)} / 100</b>
          </div>
          <div>
            <small>Clasificación</small>
            <b>{ica.clasificacion || "—"}</b>
          </div>
        </div>
      </article>
    </section>
  );
}
