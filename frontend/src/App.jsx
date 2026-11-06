import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "./api/client.js";
import Header from "./components/Header.jsx";
import Tabs from "./components/Tabs.jsx";
import ControlPanel from "./components/ControlPanel.jsx";
import SceneView from "./components/SceneView.jsx";
import SceneToolbar from "./components/SceneToolbar.jsx";
import UnitInspector from "./components/UnitInspector.jsx";
import KpiCards from "./components/KpiCards.jsx";
import OperacionPanel from "./components/OperacionPanel.jsx";
import EfluentePanel from "./components/EfluentePanel.jsx";
import LodosPanel from "./components/LodosPanel.jsx";
import ModeloPanel from "./components/ModeloPanel.jsx";
import { useSimulation } from "./hooks/useSimulation.js";

const TABS = [
  { id: "planta", label: "Vista 3D" },
  { id: "operacion", label: "Operación" },
  { id: "efluente", label: "Efluente" },
  { id: "lodos", label: "Lodos" },
  { id: "modelo", label: "Modelo" },
];

function normalizarPreset(preset, limitesDefault) {
  return {
    influente: { ...preset.influente },
    diseno: JSON.parse(JSON.stringify(preset.diseno || {})),
    limites: { ...(limitesDefault || {}) },
  };
}

function fijarValor(payload, path, value) {
  const copia = JSON.parse(JSON.stringify(payload));
  const claves = path.split(".");
  let objetivo = copia;
  claves.slice(0, -1).forEach((clave) => {
    if (objetivo[clave] === undefined || objetivo[clave] === null) {
      objetivo[clave] = {};
    }
    objetivo = objetivo[clave];
  });
  objetivo[claves[claves.length - 1]] = value;
  return copia;
}

function tabInicial() {
  const hash = window.location.hash.replace("#", "");
  return TABS.some((t) => t.id === hash) ? hash : "planta";
}

export default function App() {
  const [catalogo, setCatalogo] = useState(null);
  const [presets, setPresets] = useState([]);
  const [presetId, setPresetId] = useState("municipal");
  const [payload, setPayload] = useState(null);
  const [dirty, setDirty] = useState(false);
  const [tab, setTab] = useState(tabInicial);
  const [seleccion, setSeleccion] = useState(null);
  const [toggles, setToggles] = useState({
    etiquetas: true,
    flujos: true,
    calidad: true,
    rotacion: false,
  });
  const [version, setVersion] = useState("");
  const [bootError, setBootError] = useState(null);
  const [presetError, setPresetError] = useState(null);
  const [reinicio, setReinicio] = useState(0);

  const sceneApiRef = useRef(null);
  const bootRef = useRef(false);
  const { resultado, cargando, error, cache, simular, limpiarError } = useSimulation();

  const presetActual = useMemo(
    () => presets.find((p) => p.id === presetId),
    [presets, presetId],
  );

  useEffect(() => {
    if (bootRef.current) return undefined;
    bootRef.current = true;
    const controller = new AbortController();

    (async () => {
      try {
        setBootError(null);
        const [cat, presetInicial] = await Promise.all([
          api.catalogo(controller.signal),
          api.preset("municipal", controller.signal),
        ]);
        if (controller.signal.aborted) return;
        setCatalogo(cat);
        setPresets(cat.presets || []);
        const inicial = normalizarPreset(presetInicial, cat.limites_default);
        setPayload(inicial);
        const data = await simular(inicial);
        if (data?.meta?.version_modelo) setVersion(data.meta.version_modelo);
      } catch (err) {
        if (err.name === "AbortError") return;
        setBootError(
          `${err.message}. Verifique que el API esté disponible en http://127.0.0.1:8000.`,
        );
      }
    })();

    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reinicio]);

  const cambiarPreset = useCallback(
    async (id) => {
      if (!catalogo) return;
      setPresetId(id);
      setSeleccion(null);
      setDirty(false);
      setPresetError(null);
      try {
        const preset = await api.preset(id);
        const siguiente = normalizarPreset(preset, catalogo.limites_default);
        setPayload(siguiente);
        const data = await simular(siguiente);
        if (data?.meta?.version_modelo) setVersion(data.meta.version_modelo);
      } catch (err) {
        setPresetError(err.message || "No fue posible cargar el escenario.");
      }
    },
    [catalogo, simular],
  );

  const cambiarCampo = useCallback((path, value) => {
    setPayload((prev) => (prev ? fijarValor(prev, path, value) : prev));
    setDirty(true);
  }, []);

  const simularAhora = useCallback(async () => {
    if (!payload) return;
    setPresetError(null);
    const data = await simular(payload);
    if (data) {
      setDirty(false);
      if (data.meta?.version_modelo) setVersion(data.meta.version_modelo);
    }
  }, [payload, simular]);

  const restablecer = useCallback(() => {
    cambiarPreset(presetId);
  }, [cambiarPreset, presetId]);

  const alternarToggle = useCallback((id) => {
    setToggles((prev) => ({ ...prev, [id]: !prev[id] }));
  }, []);

  const cambiarTab = useCallback((id) => {
    setTab(id);
    window.history.replaceState(null, "", `#${id}`);
  }, []);

  useEffect(() => {
    const alCambiarHash = () => setTab(tabInicial());
    window.addEventListener("hashchange", alCambiarHash);
    return () => window.removeEventListener("hashchange", alCambiarHash);
  }, []);

  const unidadSeleccionada = useMemo(
    () => catalogo?.unidades?.find((u) => u.id === seleccion) || null,
    [catalogo, seleccion],
  );

  const tabItems = useMemo(
    () =>
      TABS.map((t) =>
        t.id === "efluente" && resultado
          ? {
              ...t,
              badge: resultado.limites?.cumple_global ? "OK" : "!",
            }
          : t,
      ),
    [resultado],
  );

  const mensajeError = error || presetError;

  if (bootError) {
    return (
      <div className="app-shell">
        <Header
          presets={presets}
          presetId={presetId}
          onPreset={cambiarPreset}
          onSimular={simularAhora}
          cargando={cargando}
          dirty={dirty}
          cache={cache}
          version={version}
        />
        <main className="boot-error">
          <h2>No se pudo iniciar el gemelo digital</h2>
          <p>{bootError}</p>
          <button
            type="button"
            className="btn-primary"
            onClick={() => {
              bootRef.current = false;
              setReinicio((n) => n + 1);
            }}
          >
            Reintentar conexión
          </button>
        </main>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <Header
        presets={presets}
        presetId={presetId}
        onPreset={cambiarPreset}
        onSimular={simularAhora}
        cargando={cargando}
        dirty={dirty}
        cache={cache}
        version={version}
      />

      <main className="layout">
        <ControlPanel
          payload={payload}
          onChange={cambiarCampo}
          onReset={restablecer}
          presetNombre={presetActual?.nombre}
        />

        <section className="workspace">
          <div className="scenario-bar">
            <div className="scenario-text">
              <span className="scenario-dot" aria-hidden="true" />
              <div>
                <strong>{presetActual?.nombre || "Escenario personalizado"}</strong>
                <p>
                  {presetActual?.descripcion ||
                    "Parámetros editados manualmente desde el panel de control."}
                </p>
              </div>
            </div>
            <div className="scenario-meta">
              {dirty ? <span className="dirty-chip">Cambios sin simular</span> : null}
              <span className="model-chip">ASM1 reducido · A2O</span>
            </div>
          </div>

          {mensajeError ? (
            <div className="error-banner" role="alert">
              <strong>No se pudo completar la simulación.</strong>
              <span>{mensajeError}</span>
              <button
                type="button"
                onClick={() => {
                  limpiarError();
                  setPresetError(null);
                }}
                aria-label="Cerrar mensaje"
              >
                ×
              </button>
            </div>
          ) : null}

          <Tabs value={tab} onChange={cambiarTab} items={tabItems} />

          <div className={`view-planta ${tab === "planta" ? "is-active" : ""}`}>
            <section className="scene-panel" aria-label="Gemelo digital 3D de la PTAR">
              {catalogo ? (
                <SceneView
                  catalogo={catalogo}
                  resultado={resultado}
                  seleccion={seleccion}
                  onSelect={setSeleccion}
                  toggles={toggles}
                  sceneApiRef={sceneApiRef}
                />
              ) : (
                <div className="scene-loading">
                  <span className="spinner" />
                  Cargando geometría de la planta…
                </div>
              )}

              <SceneToolbar
                toggles={toggles}
                onToggle={alternarToggle}
                onView={(v) => sceneApiRef.current?.setView(v)}
                onReset={() => sceneApiRef.current?.resetView()}
              />

              {unidadSeleccionada ? (
                <UnitInspector
                  unidad={unidadSeleccionada}
                  resultado={resultado}
                  onClose={() => setSeleccion(null)}
                  onFocus={(id) => sceneApiRef.current?.focusUnit(id)}
                />
              ) : null}

              {cargando ? (
                <div className="sim-overlay">
                  <span className="spinner big" />
                  <strong>Resolviendo el tren completo…</strong>
                  <small>
                    Integración del reactor A2O, clarificador y línea de lodos
                  </small>
                </div>
              ) : null}

              {!resultado && !cargando && !error ? (
                <div className="sim-overlay soft">
                  <strong>Sin resultados todavía</strong>
                  <small>Pulse Simular para ejecutar el modelo.</small>
                </div>
              ) : null}
            </section>

            <KpiCards resultado={resultado} />
          </div>

          {tab === "operacion" ? <OperacionPanel resultado={resultado} /> : null}
          {tab === "efluente" ? <EfluentePanel resultado={resultado} /> : null}
          {tab === "lodos" ? <LodosPanel resultado={resultado} /> : null}
          {tab === "modelo" ? (
            <ModeloPanel resultado={resultado} catalogo={catalogo} />
          ) : null}
        </section>
      </main>

      <footer className="app-footer">
        <span>PTAR Digital · gemelo digital docente</span>
        <span>
          Modelo ASM1 reducido + clarificador de Vesilind · resultados de ingeniería
          conceptual
        </span>
      </footer>
    </div>
  );
}
