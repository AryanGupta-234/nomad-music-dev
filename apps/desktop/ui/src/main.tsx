import React from "react";
import ReactDOM from "react-dom/client";
import "./nomad-runtime";
import App from "./App";
import "./styles.css";
import "./nomad-polish.css";
import "./nomad-production.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
