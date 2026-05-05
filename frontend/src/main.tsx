import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { loadConfig } from "./config";
import App from "./App";
import "./index.css";

loadConfig().then(() => {
  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}).catch((err) => {
  console.error("[boot] Fatal render error", err);
  document.body.innerHTML = "<pre>Application failed to start.</pre>";
});
