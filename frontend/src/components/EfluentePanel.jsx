import { fmt, fmtPct } from "../lib/format.js";

const LIMITES = [
  { key: "dbo5_mg_l", label: "DBO₅", unit: "mg/L" },
  { key: "dqo_mg_l", label: "DQO", unit: "mg/L" },
  { key: "sst_mg_l", label: "SST", unit: "mg/L" },
  { key: "nt_mg_l", label: "N total", unit: "mg/L" },
  { key: "pt_mg_l", label: "P total", unit: "mg/L" },
  { key: "ph", label: "pH", unit: "–" },
  { key: "coliformes_ufc_100ml", label: "Coliformes", unit: "UFC/100 mL" },
];

const EFICIENCIAS = [
  { key: "dqo", label: "DQO", color: "#38bdf8" },
  { key: "dbo5", label: "DBO₅", color: "#a78bfa" },
  { key: "sst", label: "SST", color: "#fbbf24" },
  { key: "nt", label: "N total", color: "#34d399" },
  { key: "tp", label: "P total", color: "#f472b6" },
];

const COMPONENTES = [
  { key: "dbo5", label: "Materia orgánica", peso: "30 %" },
  { key: "dqo", label: "DQO", peso: "20 %" },
  { key: "sst", label: "Sólidos", peso: "20 %" },
  { key: "nutrientes", label: "Nutrientes", peso: "20 %" },
  { key: "patogenos", label: "Patógenos", peso: "10 %" },
];

export default function EfluentePanel({ resultado }) {
  if (!resultado) {
    return (
      <section className="panel">
        <h2>Calidad del efluente</h2>
        <p className="panel-empty">Ejecute una simulación para evaluar la descarga.</p>
      </section>
    );
  }

  const ef = resultado.efluente || {};
  const limites = resultado.limites || {};
  const k = resultado.kpis || {};
  const ica = k.indice_calidad || {};
  const comp = ica.componentes || {};
  const caracterizacion = resultado.caracterizacion || {};
  const cumple = Boolean(limites.cumple_global);
  const icaValor = Number(ica.valor || 0);

  return (
    <div className="panel-stack">
      <section className={`panel verdict-panel ${cumple ? "is-ok" : "is-warn"}`}>
        <div className="verdict-main">
          <span className="verdict-icon" aria-hidden="true">
            {cumple ? "✓" : "!"}
          </span>
          <div>
            <h2>{cumple ? "El efluente cumple los límites" : "Hay parámetros fuera de límite"}</h2>
            <p>
              {cumple
                ? "Todos los parámetros evaluados están por debajo de la referencia configurada."
                : "Revise la tabla de cumplimiento y ajuste la operación del tren."}
            </p>
          </div>
        </div>
        <div className="verdict-kpis">
          <div>
            <small>Índice de calidad</small>
            <strong>{fmt(ica.valor, 1)}</strong>
            <span>{ica.clasificacion || "—"}</span>
          </div>
          <div>
            <small>Caudal</small>
            <strong>{fmt(ef.caudal_m3_d)}</strong>
            <span>m³/d</span>
          </div>
          <div>
            <small>Recuperación</small>
            <strong>{fmt(k.recuperacion_agua_pct, 1)}</strong>
            <span>%</span>
          </div>
        </div>
      </section>

      <div className="two-col">
        <section className="panel">
          <header className="panel-head">
            <div>
              <h2>Características finales</h2>
              <p>Concentraciones a la salida de la desinfección.</p>
            </div>
          </header>

          <div className="metric-grid compact">
            <div className="metric-card">
              <small>DQO</small>
              <strong>{fmt(ef.dqo_mg_l, 1)}</strong>
              <span>mg/L</span>
            </div>
            <div className="metric-card">
              <small>DBO₅</small>
              <strong>{fmt(ef.dbo5_mg_l, 1)}</strong>
              <span>mg/L</span>
            </div>
            <div className="metric-card">
              <small>SST</small>
              <strong>{fmt(ef.sst_mg_l, 1)}</strong>
              <span>mg/L</span>
            </div>
            <div className="metric-card">
              <small>N total</small>
              <strong>{fmt(ef.nt_mg_l, 1)}</strong>
              <span>mg/L</span>
            </div>
            <div className="metric-card">
              <small>P total</small>
              <strong>{fmt(ef.pt_mg_l, 2)}</strong>
              <span>mg/L</span>
            </div>
            <div className="metric-card">
              <small>pH</small>
              <strong>{fmt(ef.ph, 2)}</strong>
              <span>–</span>
            </div>
            <div className="metric-card">
              <small>Coliformes</small>
              <strong>{fmt(ef.coliformes_ufc_100ml)}</strong>
              <span>UFC/100 mL</span>
            </div>
            <div className="metric-card">
              <small>Turbiedad</small>
              <strong>{fmt(ef.turbiedad_ntu, 1)}</strong>
              <span>NTU</span>
            </div>
            <div className="metric-card">
              <small>N-NH₄</small>
              <strong>{fmt(ef.n_nh4_mg_l, 2)}</strong>
              <span>mg N/L</span>
            </div>
            <div className="metric-card">
              <small>N-NO₃</small>
              <strong>{fmt(ef.n_no3_mg_l, 2)}</strong>
              <span>mg N/L</span>
            </div>
            <div className="metric-card">
              <small>Alcalinidad</small>
              <strong>{fmt(ef.alcalinidad_mg_l)}</strong>
              <span>mg CaCO₃/L</span>
            </div>
            <div className="metric-card">
              <small>Temperatura</small>
              <strong>{fmt(ef.temperatura_c, 1)}</strong>
              <span>°C</span>
            </div>
          </div>
        </section>

        <section className="panel">
          <header className="panel-head">
            <div>
              <h2>Cumplimiento</h2>
              <p>Comparación con los límites configurados en el panel.</p>
            </div>
          </header>
          <div className="table-wrap">
            <table className="data-table limits-table">
              <thead>
                <tr>
                  <th>Parámetro</th>
                  <th>Valor</th>
                  <th>Límite</th>
                  <th>Estado</th>
                </tr>
              </thead>
              <tbody>
                {LIMITES.map((item) => {
                  const v = limites[item.key];
                  if (!v) return null;
                  return (
                    <tr key={item.key}>
                      <td>{item.label}</td>
                      <td>
                        {fmt(v.valor, v.valor < 10 ? 2 : 1)} {item.unit !== "–" ? item.unit : ""}
                      </td>
                      <td>{v.limite || "—"}</td>
                      <td>
                        <span className={`state-badge ${v.cumple ? "is-ok" : "is-warn"}`}>
                          {v.cumple ? "Cumple" : "Excede"}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <div className="two-col">
        <section className="panel">
          <header className="panel-head">
            <div>
              <h2>Índice de calidad del agua</h2>
              <p>Índice simplificado 0–100 adaptado del ICA de la NSF.</p>
            </div>
          </header>
          <div className="ica-layout">
            <div
              className="ica-ring"
              style={{ "--ica": `${Math.min(100, icaValor) * 3.6}deg` }}
            >
              <div>
                <strong>{fmt(ica.valor, 1)}</strong>
                <span>{ica.clasificacion || "—"}</span>
              </div>
            </div>
            <div className="ica-bars">
              {COMPONENTES.map((c) => (
                <div key={c.key}>
                  <span>
                    {c.label} <em>{c.peso}</em>
                  </span>
                  <div className="bar">
                    <span style={{ width: `${Math.min(100, Number(comp[c.key] || 0))}%` }} />
                  </div>
                  <b>{fmt(comp[c.key], 1)}</b>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="panel">
          <header className="panel-head">
            <div>
              <h2>Remoción global</h2>
              <p>Eficiencia másica entre el afluente y el efluente tratado.</p>
            </div>
          </header>
          <div className="efficiency-list">
            {EFICIENCIAS.map((e) => {
              const valor = Number(k[e.key]?.eficiencia_pct || 0);
              return (
                <div key={e.key}>
                  <span>{e.label}</span>
                  <div className="bar">
                    <span style={{ width: `${Math.min(100, valor)}%`, background: e.color }} />
                  </div>
                  <b>{fmtPct(valor)}</b>
                </div>
              );
            })}
          </div>

          <div className="relation-grid">
            <div>
              <small>DQO/DBO₅ entrada</small>
              <b>{fmt(caracterizacion.relacion_dqo_dbo5, 2)}</b>
            </div>
            <div>
              <small>SSV/SST entrada</small>
              <b>{fmt(caracterizacion.relacion_ssv_sst, 2)}</b>
            </div>
            <div>
              <small>COD particulado/SST</small>
              <b>{fmt(caracterizacion.relacion_cod_sst, 2)}</b>
            </div>
          </div>

          {caracterizacion.advertencias?.length ? (
            <div className="warning-box">
              <h3>Advertencias de caracterización</h3>
              <ul>
                {caracterizacion.advertencias.map((a) => (
                  <li key={a}>{a}</li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="panel-note ok-note">
              La caracterización de entrada es consistente con los rangos típicos.
            </p>
          )}
        </section>
      </div>
    </div>
  );
}
