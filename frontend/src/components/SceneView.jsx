import { useEffect, useRef } from "react";
import { PlantScene } from "../three/PlantScene.js";

export default function SceneView({
  catalogo,
  resultado,
  seleccion,
  onSelect,
  toggles,
  sceneApiRef,
}) {
  const montajeRef = useRef(null);
  const escenaRef = useRef(null);
  const selectRef = useRef(onSelect);
  const togglesRef = useRef(toggles);

  useEffect(() => {
    selectRef.current = onSelect;
  }, [onSelect]);

  useEffect(() => {
    togglesRef.current = toggles;
  }, [toggles]);

  useEffect(() => {
    if (!catalogo || !montajeRef.current) return undefined;
    const escena = new PlantScene(montajeRef.current, {
      onSelect: (id) => selectRef.current?.(id),
    });
    escenaRef.current = escena;
    escena.setCatalog(catalogo.unidades);
    escena.setToggles(togglesRef.current);
    if (sceneApiRef) {
      sceneApiRef.current = {
        setView: (v) => escena.setView(v),
        focusUnit: (id) => escena.focusUnit(id),
        resetView: () => escena.resetView(),
      };
    }
    return () => {
      if (sceneApiRef) sceneApiRef.current = null;
      escena.dispose();
      escenaRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [catalogo]);

  useEffect(() => {
    if (escenaRef.current && resultado) {
      escenaRef.current.update(resultado);
    }
  }, [resultado]);

  useEffect(() => {
    if (!escenaRef.current) return;
    escenaRef.current.setToggles(toggles);
    // Al reactivar el coloreado por calidad hay que reaplicar los datos.
    if (resultado) escenaRef.current.update(resultado);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [toggles]);

  useEffect(() => {
    escenaRef.current?.setSelected(seleccion || null);
  }, [seleccion]);

  return <div className="scene-mount" ref={montajeRef} />;
}
