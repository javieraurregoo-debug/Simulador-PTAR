import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api/client.js";

/**
 * Encapsula la petición de simulación: aborta la anterior, expone estados de
 * carga/error y devuelve el resultado junto con el estado de caché del API.
 */
export function useSimulation() {
  const [resultado, setResultado] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState(null);
  const [cache, setCache] = useState(null);
  const abortRef = useRef(null);

  const simular = useCallback(async (payload) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setCargando(true);
    setError(null);
    try {
      const { data, cache: estadoCache } = await api.simular(
        payload,
        controller.signal,
      );
      setResultado(data);
      setCache(estadoCache);
      return data;
    } catch (err) {
      if (err.name !== "AbortError") {
        setError(err.message || "No fue posible completar la simulación.");
      }
      return null;
    } finally {
      if (abortRef.current === controller) {
        setCargando(false);
      }
    }
  }, []);

  useEffect(() => () => abortRef.current?.abort(), []);

  return {
    resultado,
    cargando,
    error,
    cache,
    simular,
    limpiarError: () => setError(null),
  };
}
