const BASE = import.meta.env.VITE_API_URL || "";

function detalleError(payload, status) {
  if (!payload) return `Error HTTP ${status}`;
  if (typeof payload.detail === "string") return payload.detail;
  if (Array.isArray(payload.detail)) {
    return payload.detail
      .map((d) => `${(d.loc || []).slice(-1)[0] || "campo"}: ${d.msg}`)
      .join(" · ");
  }
  return `Error HTTP ${status}`;
}

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { Accept: "application/json", ...(options.headers || {}) },
    ...options,
  });
  let payload = null;
  try {
    payload = await res.json();
  } catch {
    payload = null;
  }
  if (!res.ok) {
    const error = new Error(detalleError(payload, res.status));
    error.status = res.status;
    error.payload = payload;
    throw error;
  }
  return { res, payload };
}

export const api = {
  async catalogo(signal) {
    const { payload } = await request("/api/catalogo", { signal });
    return payload;
  },

  async presets(signal) {
    const { payload } = await request("/api/presets", { signal });
    return payload;
  },

  async preset(id, signal) {
    const { payload } = await request(`/api/presets/${id}`, { signal });
    return payload;
  },

  async simular(payload, signal) {
    const { res, payload: data } = await request("/api/simulaciones", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal,
    });
    return {
      data,
      cache: res.headers.get("X-Simulation-Cache") || "MISS",
      version: res.headers.get("X-Model-Version") || "",
    };
  },
};
