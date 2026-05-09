import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ConfigProvider, theme } from "antd";
import AppLayout from "./layouts/AppLayout";
import PipelinePage from "./pages/PipelinePage";
import "./index.css";

function App() {
  return (
    <ConfigProvider
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          colorPrimary:         "#00FF9D",
          colorPrimaryBg:       "rgba(0,255,157,0.08)",
          colorPrimaryBorder:   "rgba(0,255,157,0.28)",

          colorBgContainer:     "#0f1220",
          colorBgElevated:      "#0b0d17",
          colorBgLayout:        "#060810",

          colorBorder:          "rgba(255,255,255,0.07)",
          colorBorderSecondary: "rgba(255,255,255,0.04)",

          colorText:            "#e8eaf0",
          colorTextSecondary:   "#9ba3b8",
          colorTextTertiary:    "#555d72",
          colorTextDisabled:    "#3a3f52",

          colorSuccess:         "#4ade80",
          colorWarning:         "#f59e0b",
          colorError:           "#ef4444",

          borderRadius:         8,
          fontFamily:           "'Space Grotesk', sans-serif",
          fontFamilyCode:       "'JetBrains Mono', monospace",
        },
        components: {
          Drawer:      { colorBgContainer: "#0b0d17" },
          Switch:      { colorPrimary: "#00FF9D" },
          InputNumber: { colorBgContainer: "#0f1220", activeBorderColor: "#00FF9D" },
          Select:      { colorBgContainer: "#0f1220" },
        },
      }}
    >
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Navigate to="/pipeline" replace />} />
            <Route path="/pipeline" element={<PipelinePage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
}

export default App;
