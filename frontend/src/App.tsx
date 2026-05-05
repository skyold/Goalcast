import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ConfigProvider, theme } from "antd";
import AppLayout from "./layouts/AppLayout";
import DashboardPage from "./pages/DashboardPage";
import BoardPage from "./pages/BoardPage";
import TokenStatsPage from "./pages/TokenStatsPage";
import PipelineMonitor from "./pages/PipelineMonitor";
import "./index.css";

function App() {
  return (
    <ConfigProvider
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          // Primary accent — Goalcast green
          colorPrimary:        "#00FF9D",
          colorPrimaryBg:      "rgba(0,255,157,0.08)",
          colorPrimaryBorder:  "rgba(0,255,157,0.28)",

          // Surface colors
          colorBgContainer:    "#0f1220",
          colorBgElevated:     "#0b0d17",
          colorBgLayout:       "#060810",
          colorBgSpotlight:    "#0f1220",

          // Border
          colorBorder:         "rgba(255,255,255,0.07)",
          colorBorderSecondary:"rgba(255,255,255,0.04)",

          // Text
          colorText:           "#e8eaf0",
          colorTextSecondary:  "#9ba3b8",
          colorTextTertiary:   "#555d72",
          colorTextDisabled:   "#3a3f52",

          // Success / warning / error
          colorSuccess:        "#4ade80",
          colorWarning:        "#ff9500",
          colorError:          "#ef4444",

          borderRadius:        8,
          fontFamily:          "'Space Grotesk', sans-serif",
          fontFamilyCode:      "'JetBrains Mono', monospace",
        },
        components: {
          Table: {
            headerBg:          "#0b0d17",
            rowHoverBg:        "rgba(255,255,255,0.04)",
            borderColor:       "rgba(255,255,255,0.07)",
          },
          Card: {
            colorBgContainer:  "#0f1220",
            colorBorderSecondary: "rgba(255,255,255,0.07)",
          },
          Drawer: {
            colorBgContainer:  "#0b0d17",
          },
          Input: {
            colorBgContainer:  "#0f1220",
            activeBorderColor: "#00FF9D",
          },
          Select: {
            colorBgContainer:  "#0f1220",
          },
        },
      }}
    >
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard"   element={<DashboardPage />} />
            <Route path="/board"       element={<BoardPage />} />
            <Route path="/pipeline"    element={<PipelineMonitor />} />
            <Route path="/token-stats" element={<TokenStatsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
}

export default App;
