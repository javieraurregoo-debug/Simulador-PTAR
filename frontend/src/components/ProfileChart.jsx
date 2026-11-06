import { fmt, shortStage } from "../lib/format.js";

const SERIES = [
  { key: "dqo", label: "DQO", color: "#38bdf8" },
  { key: "dbo5", label: "DBO₅", color: "#a78bfa" },
  { key: "sst", label: "SST", color: "#fbbf24" },
  { key: "nt", label: "N total", color: "#34d399" },
];

const W = 760;
const H = 280;
const M = { top: 18, right: 18, bottom: 58, left: 46 };
const ANCHO = W - M.left - M.right;
const ALTO = H - M.top - M.bottom;

function escalaLog(valor) {
  return Math.log10(Math.max(Number(valor) || 0.5, 0.5));
}

export default function ProfileChart({ perfil }) {
  const datos = Array.isArray(perfil) ? perfil : [];
  if (datos.length < 2) {
    return (
      <section className="panel profile-panel">
        <header className="panel-head">
          <h2>Perfil de concentraciones</h2>
        </header>
        <p className="panel-empty">Ejecute una simulación para graficar el tren.</p>
      </section>
    );
  }

  const valores = datos.flatMap((d) => SERIES.map((s) => Number(d[s.key]) || 0.5));
  const minLog = Math.floor(Math.log10(Math.max(Math.min(...valores), 0.5)));
  const maxLog = Math.ceil(Math.log10(Math.max(...valores)));
  const rango = Math.max(maxLog - minLog, 1);
  const ticks = [];
  for (let p = minLog; p <= maxLog; p += 1) ticks.push(Math.pow(10, p));

  const x = (i) => M.left + (i / (datos.length - 1)) * ANCHO;
  const y = (v) =>
    M.top + ALTO - ((escalaLog(v) - minLog) / rango) * ALTO;

  return (
    <section className="panel profile-panel">
      <header className="panel-head panel-head-row">
        <div>
          <h2>Perfil de concentraciones</h2>
          <p>Evolución de DBO₅, DQO, SST y nitrógeno a lo largo del tren (escala logarítmica).</p>
        </div>
        <div className="chart-legend">
          {SERIES.map((s) => (
            <span key={s.key}>
              <i style={{ background: s.color }} />
              {s.label}
            </span>
          ))}
        </div>
      </header>

      <div className="chart-wrap">
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Perfil de concentraciones por etapa">
          {ticks.map((t) => (
            <g key={t}>
              <line
                x1={M.left}
                x2={W - M.right}
                y1={y(t)}
                y2={y(t)}
                className="chart-grid"
              />
              <text x={M.left - 8} y={y(t) + 4} textAnchor="end" className="chart-axis">
                {t >= 1000 ? `${t / 1000}k` : t}
              </text>
            </g>
          ))}

          {SERIES.map((s) => {
            const puntos = datos.map((d, i) => `${x(i)},${y(d[s.key] || 0.5)}`).join(" ");
            return (
              <g key={s.key}>
                <polyline
                  points={puntos}
                  fill="none"
                  stroke={s.color}
                  strokeWidth="2.4"
                  strokeLinejoin="round"
                  strokeLinecap="round"
                />
                {datos.map((d, i) => (
                  <circle
                    key={`${s.key}-${i}`}
                    cx={x(i)}
                    cy={y(d[s.key] || 0.5)}
                    r="3.4"
                    fill="#07131f"
                    stroke={s.color}
                    strokeWidth="2"
                  >
                    <title>
                      {d.etapa}: {s.label} = {fmt(d[s.key], 1)} mg/L
                    </title>
                  </circle>
                ))}
              </g>
            );
          })}

          {datos.map((d, i) => (
            <text
              key={d.etapa}
              x={x(i)}
              y={H - M.bottom + 18}
              textAnchor="middle"
              className="chart-xlabel"
              transform={`rotate(-32 ${x(i)} ${H - M.bottom + 18})`}
            >
              {shortStage(d.etapa)}
            </text>
          ))}

          <text x={M.left - 8} y={M.top - 4} textAnchor="end" className="chart-axis">
            mg/L
          </text>
        </svg>
      </div>
    </section>
  );
}
