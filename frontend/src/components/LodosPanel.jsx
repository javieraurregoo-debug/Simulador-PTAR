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

function Cierre({ titulo, datos, etiquetas }) {
  if (!datos) return null;
  const cierre = Number(datos.cierre_pct || 0);
  const ok = datos.estado === "cerrado";
  return (
    <div className="closure-card">
      <div className="closure-head">
        <h3>{titulo}</h3>
        <span className={`state-badge ${ok ? "is-ok" : "is-warn"}`}>
          {ok ? "Cerrado" : "Revisar"}
        </span>
      </div>
      <div className="closure-rows">
        {etiquetas.map(([key, label]) =>
          datos[key] !== undefined ? (
            <div key={key}>
              <span>{label}</span>
              <b>{fmt(datos[key], 1)} kg/d</b>
            </div>
          ) : null,
        )}
      </div>
      <div className="closure-total">
        <span>Cierre de masa</span>
        <b>{fmtPct(cierre)}</b>
      </div>
      <div className="bar">
        <span
          style={{
            width: `${Math.min(100, cierre)}%`,
            background: ok ? "#34d399" : "#fbbf24",
          }}
        />
      </div>
      <small className="closure-note">Rango aceptable: 85 % – 115 %</small>
    </div>
  );
}

export default function LodosPanel({ resultado }) {
  if (!resultado) {
    return (
      <section className="panel">
        <h2>Tren de lodos</h2>
        <p className="panel-empty">Ejecute una simulación para ver el balance de lodos.</p>
      </section>
    );
  }

  const tren = resultado.tren_lodos || {};
  const res = tren.resumen || {};
  const etapas = tren.etapas || [];
  const k = resultado.kpis || {};
  const balance = resultado.balance || {};
  const esp = etapas.find((e) => e.id === "espesador");
  const dig = etapas.find((e) => e.id === "digestor");
  const des = etapas.find((e) => e.id === "deshidratacion");

  return (
    <div className="panel-stack">
      <section className="panel">
        <header className="panel-head">
          <div>
            <h2>Tren de lodos</h2>
            <p>
              Espesamiento, digestión anaerobia y deshidratación. Los rechazos se
              recirculan a la cabecera de la planta.
            </p>
          </div>
        </header>

        <div className="sludge-strip">
          <div className="sludge-node">
            <span>1</span>
            <strong>Espesador</strong>
            <small>{fmt(esp?.salida_m3_d, 1)} m³/d</small>
            <em>{fmt(esp?.salida_kg_sst_d, 1)} kg SST/d</em>
          </div>
          <i className="flow-arrow">→</i>
          <div className="sludge-node">
            <span>2</span>
            <strong>Digestor</strong>
            <small>{fmt(dig?.volumen_m3)} m³</small>
            <em>{fmt(dig?.biogas_m3_d)} m³ biogás/d</em>
          </div>
          <i className="flow-arrow">→</i>
          <div className="sludge-node">
            <span>3</span>
            <strong>Deshidratación</strong>
            <small>{fmt(des?.torta_m3_d, 1)} m³/d de torta</small>
            <em>{fmt(des?.torta_kg_sst_d, 1)} kg SST/d</em>
          </div>
        </div>

        <div className="metric-grid">
          <Metric label="Lodo primario" value={fmt(res.lodo_primario_kg_sst_d)} unit="kg SST/d" />
          <Metric label="Purga biológica" value={fmt(res.purga_kg_sst_d)} unit="kg SST/d" />
          <Metric label="Sólidos de entrada" value={fmt(res.solidos_entrada_kg_d)} unit="kg SST/d" />
          <Metric label="Concentración de entrada" value={fmt(res.concentracion_entrada_pct, 2)} unit="%" />
          <Metric label="Torta producida" value={fmt(res.torta_kg_sst_d)} unit="kg SST/d" />
          <Metric label="Torta en volumen" value={fmt(res.torta_m3_d, 1)} unit="m³/d" />
          <Metric label="Biogás" value={fmt(res.biogas_m3_d)} unit="m³/d" />
          <Metric label="Metano" value={fmt(res.metano_m3_d)} unit="m³/d" />
          <Metric label="Energía eléctrica" value={fmt(res.energia_kwh_d)} unit="kWh/d" />
          <Metric label="Energía térmica" value={fmt(res.energia_termica_kwh_d)} unit="kWh/d" />
          <Metric label="Recirculación de rechazos" value={fmt(res.recirculacion_m3_d, 1)} unit="m³/d" />
          <Metric label="Producción específica" value={fmt(res.produccion_especifica_kg_sst_kg_dqo, 3)} unit="kg SST/kg DQO" />
        </div>
      </section>

      <section className="panel">
        <header className="panel-head">
          <div>
            <h2>Detalle por unidad</h2>
            <p>Balances másicos y volumétricos de cada etapa del tren de lodos.</p>
          </div>
        </header>

        <div className="table-wrap">
          <table className="data-table sludge-table">
            <thead>
              <tr>
                <th>Unidad</th>
                <th>Entrada (m³/d)</th>
                <th>Entrada (kg SST/d)</th>
                <th>Salida (m³/d)</th>
                <th>Salida (kg SST/d)</th>
                <th>Indicador</th>
                <th>Detalle</th>
              </tr>
            </thead>
            <tbody>
              {etapas.map((e) => (
                <tr key={e.id}>
                  <td>
                    <b>{e.nombre}</b>
                  </td>
                  <td>{fmt(e.entrada_m3_d, 1)}</td>
                  <td>{fmt(e.entrada_kg_sst_d, 1)}</td>
                  <td>{fmt(e.salida_m3_d ?? e.torta_m3_d, 1)}</td>
                  <td>{fmt(e.salida_kg_sst_d ?? e.torta_kg_sst_d, 1)}</td>
                  <td>
                    {e.id === "espesador"
                      ? `${fmt(e.concentracion_pct, 1)} % SST`
                      : e.id === "digestor"
                        ? `${fmt(e.vs_destruido_kg_d, 1)} kg VS destruidos/d`
                        : `${fmt(e.camiones_dia, 1)} camiones/d`}
                  </td>
                  <td>{e.detalle}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="two-col">
        <section className="panel">
          <header className="panel-head">
            <div>
              <h2>Energía y circularidad</h2>
              <p>Valorización del biogás en cogeneración (CHP).</p>
            </div>
          </header>
          <div className="metric-grid compact">
            <Metric label="Biogás" value={fmt(res.biogas_m3_d)} unit="m³/d" />
            <Metric label="Energía eléctrica" value={fmt(res.energia_kwh_d)} unit="kWh/d" />
            <Metric label="Energía específica" value={fmt(res.energia_kwh_por_m3, 3)} unit="kWh/m³" />
            <Metric label="Autosuficiencia" value={fmt(k.autosuficiencia_energetica_pct, 1)} unit="%" />
            <Metric label="COD destruido" value={fmt(res.cod_destruido_kg_d)} unit="kg DQO/d" />
            <Metric label="Rechazos recirculados" value={fmtPct(res.recirculacion_pct, 2)} />
          </div>
          <p className="panel-note">
            La recirculación de rechazos aporta {fmt(res.rechazo_sst_mg_l)} mg/L de SST y{" "}
            {fmt(res.rechazo_dbo5_mg_l)} mg/L de DBO₅ equivalente a la cabecera, por lo que
            se recomienda su control en la operación real.
          </p>
        </section>

        <section className="panel">
          <header className="panel-head">
            <div>
              <h2>Cierre de balance</h2>
              <p>Verificación de conservación de masa del tren completo.</p>
            </div>
          </header>
          <div className="closure-grid">
            <Cierre
              titulo="DQO"
              datos={balance.dqo}
              etiquetas={[
                ["entrada_kg_d", "Entrada"],
                ["efluente_kg_d", "Efluente"],
                ["lodo_kg_d", "Lodo (como DQO)"],
                ["biogas_kg_d", "DQO destruida en digestor"],
                ["oxidada_kg_d", "DQO oxidada en reactor"],
                ["residuos_pretratamiento_kg_d", "Residuos de pretratamiento"],
                ["salida_total_kg_d", "Salida total"],
              ]}
            />
            <Cierre
              titulo="SST"
              datos={balance.sst}
              etiquetas={[
                ["entrada_kg_d", "Entrada"],
                ["efluente_kg_d", "Efluente"],
                ["torta_kg_d", "Torta deshidratada"],
                ["destruido_kg_d", "Sólidos volatilizados"],
                ["residuos_pretratamiento_kg_d", "Residuos de pretratamiento"],
                ["salida_total_kg_d", "Salida total"],
              ]}
            />
          </div>
        </section>
      </div>
    </div>
  );
}
