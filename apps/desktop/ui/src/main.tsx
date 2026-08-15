import React from "react";
import ReactDOM from "react-dom/client";
import AppStable from "./AppStable";
import "./styles.css";
import "./nomad-polish.css";
import "./AppStable.css";
import "./AppStableFix.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AppStable />
  </React.StrictMode>,
);
