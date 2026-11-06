export default function Header({
  presets,
  presetId,
  onPreset,
  onSimular,
  cargando,
  dirty,
  cache,
  version,
}) {
  return (
    <header className="topbar">
      <div className="brand">
        <div className="brand-mark" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
        <div className="brand-text">
          <h1>PTAR Digital</h1>
          <p>Gemelo 3D · tren A2O · ASM1 reducido</p>
        </div>
      </div>

      <div className="topbar-actions">
        <label className="preset-select">
          <span>Escenario</span>
          <select value={presetId} onChange={(e) => onPreset(e.target.value)}>
            {presets.map((p) => (
              <option key={p.id} value={p.id}>
                {p.nombre}
              </option>
            ))}
          </select>
        </label>

        <div className="status-pill" title="Versión del modelo y estado de caché">
          <span className={`status-dot ${cache === "HIT" ? "is-hit" : ""}`} />
          <span>{version ? `v${version}` : "modelo"}</span>
          {cache ? <b>{cache}</b> : null}
        </div>

        <button
          type="button"
          className={`btn-primary ${dirty ? "is-dirty" : ""}`}
          onClick={onSimular}
          disabled={cargando}
        >
          {cargando ? (
            <>
              <span className="spinner" /> Simulando
            </>
          ) : (
            <>
              <span className="play-icon" aria-hidden="true" />
              {dirty ? "Simular cambios" : "Simular"}
            </>
          )}
        </button>
      </div>
    </header>
  );
}
