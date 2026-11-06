import { fmt } from "../lib/format.js";

const FRACCIONES = [
  ["si", "S_I", "COD soluble inerte"],
  ["ss", "S_S", "Sustrato soluble biodegradable"],
  ["xs", "X_S", "Sustrato particulado"],
  ["xi", "X_I", "Inerte particulado"],
  ["xbh", "X_BH", "Biomasa heterótrofa"],
  ["xba", "X_BA", "Biomasa autótrofa"],
];

const LIMITACIONES = [
  "Modelo determinista de régimen permanente; no reproduce dinámica horaria ni eventos de lluvia.",
  "ASM1 reducido: no incluye productos de almacenamiento interno ni eliminación biológica de fósforo (EBPR).",
  "El fósforo se remueve por asimilación en la biomasa y precipitación implícita; para límites estrictos de P se requiere dosificación química.",
  "La desinfección usa cinéticas de Chick-Watson calibradas; el decaimiento en el tiempo no se modela.",
  "Los caudales de recirculación y purga se consideran constantes y completamente mezclados.",
  "Los costos de inversión, operación y mantenimiento no forman parte del alcance del gemelo digital.",
];

export default function ModeloPanel({ resultado, catalogo }) {
  const ecuaciones = catalogo?.ecuaciones || [];
  const caracterizacion = resultado?.caracterizacion || {};
  const fracciones = caracterizacion.fracciones_cod || {};
  const suma = FRACCIONES.reduce((acc, [key]) => acc + Number(fracciones[key] || 0), 0);

  return (
    <div className="panel-stack">
      <div className="two-col">
        <section className="panel">
          <header className="panel-head">
            <div>
              <h2>Ecuaciones del modelo</h2>
              <p>Formulación utilizada por el simulador para DBO₅, DQO, SST y procesos asociados.</p>
            </div>
          </header>
          <div className="equation-list">
            {ecuaciones.map((e) => (
              <article key={e.id} className="equation-card">
                <header>
                  <h3>{e.nombre}</h3>
                  <span>{e.unidad}</span>
                </header>
                <code>{e.expresion}</code>
                <p>{e.descripcion}</p>
                {e.variables ? (
                  <dl>
                    {Object.entries(e.variables).map(([k, v]) => (
                      <div key={k}>
                        <dt>{k}</dt>
                        <dd>{v}</dd>
                      </div>
                    ))}
                  </dl>
                ) : null}
              </article>
            ))}
          </div>
        </section>

        <div className="panel-stack">
          <section className="panel">
            <header className="panel-head">
              <div>
                <h2>Fraccionamiento del COD</h2>
                <p>Traducción de DBO₅, DQO y SST a las fracciones de ASM1.</p>
              </div>
            </header>

            {resultado ? (
              <>
                <div className="fraction-total">
                  <div>
                    <small>DQO reconstruida</small>
                    <strong>{fmt(suma, 1)} mg/L</strong>
                  </div>
                  <div>
                    <small>DQO de entrada</small>
                    <strong>{fmt(resultado.afluente?.dqo_mg_l, 1)} mg/L</strong>
                  </div>
                </div>
                <div className="fraction-list">
                  {FRACCIONES.map(([key, sigla, nombre]) => {
                    const valor = Number(fracciones[key] || 0);
                    const pct = suma > 0 ? (valor / suma) * 100 : 0;
                    return (
                      <div key={key}>
                        <span>
                          <b>{sigla}</b> {nombre}
                        </span>
                        <div className="bar">
                          <span style={{ width: `${Math.min(100, pct)}%` }} />
                        </div>
                        <em>{fmt(valor, 1)} mg/L</em>
                      </div>
                    );
                  })}
                </div>
                <p className="panel-note">
                  Relación DQO/DBO₅ = {fmt(caracterizacion.relacion_dqo_dbo5, 2)} · SSV/SST ={" "}
                  {fmt(caracterizacion.relacion_ssv_sst, 2)}. El reparto conserva la DQO
                  medida y usa la DBO₅ para estimar el COD biodegradable.
                </p>
              </>
            ) : (
              <p className="panel-empty">Ejecute una simulación para ver el fraccionamiento.</p>
            )}
          </section>

          <section className="panel">
            <header className="panel-head">
              <div>
                <h2>Alcance y limitaciones</h2>
                <p>Lectura crítica de los resultados del gemelo digital.</p>
              </div>
            </header>
            <ul className="limitations">
              {LIMITACIONES.map((l) => (
                <li key={l}>{l}</li>
              ))}
            </ul>
          </section>
        </div>
      </div>

      <div className="two-col">
        <section className="panel">
          <header className="panel-head">
            <div>
              <h2>Referencias</h2>
              <p>Base bibliográfica de las ecuaciones y parámetros cinéticos.</p>
            </div>
          </header>
          <ul className="reference-list">
            {(resultado?.meta?.referencias || []).map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
        </section>

        <section className="panel">
          <header className="panel-head">
            <div>
              <h2>Metadatos de la simulación</h2>
              <p>Trazabilidad del cálculo ejecutado por el API.</p>
            </div>
          </header>
          <dl className="meta-list">
            <div>
              <dt>Versión del modelo</dt>
              <dd>{resultado?.meta?.version_modelo || "—"}</dd>
            </div>
            <div>
              <dt>Duración del cálculo</dt>
              <dd>{resultado ? `${fmt(resultado.meta?.duracion_ms, 0)} ms` : "—"}</dd>
            </div>
            <div>
              <dt>Unidades</dt>
              <dd>caudal m³/d · concentración mg/L · carga kg/d · energía kWh/d</dd>
            </div>
            <div>
              <dt>Escenario</dt>
              <dd>{caracterizacion.caudal_m3_d ? `${fmt(caracterizacion.caudal_m3_d)} m³/d` : "—"}</dd>
            </div>
            {caracterizacion.carga_dqo_kg_d ? (
              <div>
                <dt>Carga de DQO</dt>
                <dd>{fmt(caracterizacion.carga_dqo_kg_d)} kg/d</dd>
              </div>
            ) : null}
          </dl>
          <p className="panel-note">
            Los resultados son una herramienta de ingeniería conceptual y docencia; no
            sustituyen la calibración con datos de planta ni el diseño detallado.
          </p>
        </section>
      </div>
    </div>
  );
}
