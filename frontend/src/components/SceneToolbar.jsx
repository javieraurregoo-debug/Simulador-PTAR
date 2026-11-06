import { qualityHex } from "../lib/format.js";

const VISTAS = [
  { id: "iso", label: "Isométrica", icon: "◩" },
  { id: "aerea", label: "Aérea", icon: "⌖" },
  { id: "agua", label: "Tren de agua", icon: "≈" },
  { id: "lodos", label: "Tren de lodos", icon: "◍" },
];

const TOGGLES = [
  { id: "etiquetas", label: "Etiquetas" },
  { id: "flujos", label: "Flujos" },
  { id: "calidad", label: "Calidad" },
  { id: "rotacion", label: "Rotación" },
];

export default function SceneToolbar({ toggles, onToggle, onView, onReset }) {
  return (
    <>
      <div className="scene-toolbar">
        <div className="toolbar-group" role="group" aria-label="Vistas de cámara">
          {VISTAS.map((v) => (
            <button
              type="button"
              key={v.id}
              className="tool-btn"
              onClick={() => onView(v.id)}
              title={v.label}
            >
              <span aria-hidden="true">{v.icon}</span>
              {v.label}
            </button>
          ))}
          <button type="button" className="tool-btn tool-reset" onClick={onReset} title="Vista inicial">
            ⟲
          </button>
        </div>

        <div className="toolbar-toggles">
          {TOGGLES.map((t) => (
            <button
              type="button"
              key={t.id}
              className={`toggle-chip ${toggles[t.id] ? "is-on" : ""}`}
              aria-pressed={Boolean(toggles[t.id])}
              onClick={() => onToggle(t.id)}
            >
              <span className="toggle-dot" />
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="scene-legend" aria-label="Leyenda de calidad del agua">
        <div className="legend-quality">
          <span>Carga orgánica</span>
          <div
            className="legend-gradient"
            style={{
              background: `linear-gradient(90deg, ${qualityHex(20)}, ${qualityHex(
                150,
              )}, ${qualityHex(300)}, ${qualityHex(450)})`,
            }}
          />
          <div className="legend-scale">
            <small>20</small>
            <small>150</small>
            <small>300</small>
            <small>450+ mg/L DQO</small>
          </div>
        </div>
        <div className="legend-pipes">
          <span>
            <i className="pipe-dot pipe-agua" /> Agua
          </span>
          <span>
            <i className="pipe-dot pipe-lodo" /> Lodo
          </span>
          <span>
            <i className="pipe-dot pipe-recirc" /> Recirculación
          </span>
          <span>
            <i className="pipe-dot pipe-rechazo" /> Rechazo
          </span>
        </div>
      </div>
    </>
  );
}
