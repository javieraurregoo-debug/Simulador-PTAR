import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import "./styles.css";

// Sin StrictMode: la doble invocación de efectos en desarrollo lanzaría dos
// simulaciones pesadas al montar la aplicación.
createRoot(document.getElementById("root")).render(<App />);
