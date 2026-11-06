import ProfileChart from "./ProfileChart.jsx";
import { fmt, fmtPct } from "../lib/format.js";

function Metric({ label, value, unit, nota }) {
  return (
    <div className="metric-card">
      <small>{label}</small>
      <strong>{value}</strong>
      {unit ? <span>{unit}</span> : null}
      {nota ? <em>{nota}</em> : null}
    </div>
  );
}

function Badge({ ok, children }) {
  return <span className={`state-badge ${ok ? "is-ok" : "is-warn"}`}>{children}</span>;
}

export default function OperacionPanel({ resultado }) {
  if (!resultado) {
    return (
      <section className="panel">
        <h2>Operación biológica</h2>
        <p className="panel-empty">Ejecute una simulación para ver la operación del reactor.</p>
      </section>
    );
  }

  const op = resultado.operacion_biologica || {};
  const reactores = resultado.reactores || [];
  const sed = resultado.sedimentador_secundario || {};
  const k = resultado.kpis || {};
  const aireKwh = Number(k.energia_aireacion_kw || 0) * 24;
  const biogasKwh = Number(k.energia_biogas_kwh_d || 0);
  const autosuf = Number(k.autosuficiencia_energetica_pct || 0);
  const puntoEstado = Number(sed.punto_estado || 0);

  return (
    <div className="panel-stack">
      <section className="panel">
        <header className="panel-head">
          <div>
            <h2>Operación biológica</h2>
            <p>
              Indicadores de edad del lodo, carga másica y transferencia de oxígeno del
              reactor A2O.
            </p>
          </div>
          <Badge ok={Number(op.srt_d || 0) >= 10}>
            {Number(op.srt_d || 0) >= 10 ? "Nitrificación estable" : "SRT bajo"}
          </Badge>
        </header>

        <div className="metric-grid">
          <Metric label="SRT" value={fmt(op.srt_d, 1)} unit="d" nota="edad del lodo" />
          <Metric label="F/M" value={fmt(op.fm_kg_cod_kg_ssv_d, 3)} unit="kg DQO/(kg SSV·d)" />
          <Metric label="MLSS" value={fmt(op.mlss_mg_l)} unit="mg/L" />
          <Metric label="MLVSS" value={fmt(op.mlvss_mg_l)} unit="mg/L" />
          <Metric label="TRH total" value={fmt(op.trh_h, 1)} unit="h" />
          <Metric label="Carga volumétrica" value={fmt(op.carga_volumetrica_kg_cod_m3_d, 2)} unit="kg DQO/(m³·d)" />
          <Metric label="OUR" value={fmt(op.our_kg_o2_d)} unit="kg O₂/d" />
          <Metric label="Aireación" value={fmt(op.aire_m3_d)} unit="m³/d" />
          <Metric label="Sopladores" value={fmt(op.potencia_sopladores_kw, 1)} unit="kW" />
          <Metric label="Lodo purgado" value={fmt(op.lodo_purgado_kg_d)} unit="kg SST/d" />
          <Metric label="Nitrificación" value={fmt(op.nitrificacion_kg_n_d)} unit="kg N/d" />
          <Metric label="Desnitrificación" value={fmt(op.desnitrificacion_kg_n_d)} unit="kg N/d" />
        </div>
      </section>

      <section className="panel">
        <header className="panel-head">
          <div>
            <h2>Perfil por zonas</h2>
            <p>Volúmenes, tiempos de retención y condiciones de cada reactor.</p>
          </div>
        </header>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Zona</th>
                <th>V (m³)</th>
                <th>TRH (h)</th>
                <th>SST</th>
                <th>SSV</th>
                <th>OD</th>
                <th>N-NH₄</th>
                <th>N-NO₃</th>
                <th>P-PO₄</th>
                <th>OUR</th>
              </tr>
            </thead>
            <tbody>
              {reactores.map((r) => (
                <tr key={r.id}>
                  <td>
                    <b>{r.nombre}</b>
                  </td>
                  <td>{fmt(r.volumen_m3)}</td>
                  <td>{fmt(r.trh_h, 2)}</td>
                  <td>{fmt(r.sst)}</td>
                  <td>{fmt(r.ssv)}</td>
                  <td>{fmt(r.do, 2)}</td>
                  <td>{fmt(r.nh4, 2)}</td>
                  <td>{fmt(r.sno, 2)}</td>
                  <td>{fmt(r.spo4, 2)}</td>
                  <td>{fmt(r.our_kg_d, 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="table-note">
          Concentraciones en mg/L; OUR en kg O₂/d. El oxígeno disuelto se fija como
          consigna de control en cada zona.
        </p>
      </section>

      <div className="two-col">
        <section className="panel">
          <header className="panel-head">
            <div>
              <h2>Clarificador secundario</h2>
              <p>Estado del manto de lodos y flujo límite de sólidos.</p>
            </div>
            <Badge ok={puntoEstado > 0 && puntoEstado < 1}>
              {puntoEstado > 0 && puntoEstado < 1 ? "Operación segura" : "Revisar carga"}
            </Badge>
          </header>

          <div className="metric-grid compact">
            <Metric label="SST rebose" value={fmt(sed.sst_rebose, 1)} unit="mg/L" />
            <Metric label="SST purga" value={fmt(sed.sst_purga)} unit="mg/L" />
            <Metric label="Eficiencia" value={fmtPct(sed.eficiencia_pct, 2)} />
            <Metric label="Punto de estado" value={fmt(sed.punto_estado, 2)} unit="–" />
            <Metric label="Carga aplicada" value={fmt(sed.carga_solidos_kg_m2_d, 1)} unit="kg/(m²·d)" />
            <Metric label="Carga límite" value={fmt(sed.carga_limite_kg_m2_d, 1)} unit="kg/(m²·d)" />
          </div>

          <div className="gauge">
            <div className="gauge-track">
              <span
                style={{
                  width: `${Math.min(100, Math.max(0, (puntoEstado / 1.4) * 100))}%`,
                }}
              />
              <i style={{ left: "71.4%" }} title="Límite de operación estable" />
            </div>
            <div className="gauge-scale">
              <small>0</small>
              <small>1,0 · límite</small>
              <small>1,4</small>
            </div>
          </div>

          <p className="panel-note">
            {sed.convergido
              ? `Solución convergida en ${fmt(sed.dias_simulados, 0)} días simulados (residual ${fmt(sed.residual, 6)}).`
              : "La integración no alcanzó el criterio de convergencia; revise los parámetros."}
          </p>
        </section>

        <section className="panel">
          <header className="panel-head">
            <div>
              <h2>Energía</h2>
              <p>Demanda de aireación frente a la electricidad producida con biogás.</p>
            </div>
            <Badge ok={autosuf >= 50}>{fmtPct(autosuf)} autosuficiencia</Badge>
          </header>

          <div className="energy-bars">
            <div>
              <span>Aireación</span>
              <b>{fmt(aireKwh)} kWh/d</b>
              <div className="bar"><span style={{ width: "100%" }} /></div>
            </div>
            <div>
              <span>Biogás (CHP)</span>
              <b>{fmt(biogasKwh)} kWh/d</b>
              <div className="bar bar-green">
                <span style={{ width: `${Math.min(100, autosuf)}%` }} />
              </div>
            </div>
          </div>

          <div className="metric-grid compact">
            <Metric label="Autosuficiencia" value={fmt(autosuf, 1)} unit="%" />
            <Metric label="Energía específica" value={fmt(k.energia_especifica_kwh_kg_dqo, 3)} unit="kWh/kg DQO" />
            <Metric label="Carga removida" value={fmt(k.carga_dqo_removida_kg_d)} unit="kg DQO/d" />
            <Metric label="Recuperación de agua" value={fmtPct(k.recuperacion_agua_pct)} />
          </div>
        </section>
      </div>

      <ProfileChart perfil={resultado.perfil} />
    </div>
  );
}
