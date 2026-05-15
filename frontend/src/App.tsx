import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ConfigProvider, theme } from "antd";
import AppLayout from "./layouts/AppLayout";
import BettingPage from "./pages/BettingPage";
import FixtureDetailPage from "./pages/FixtureDetailPage";
import DroppingOddsPage from "./pages/DroppingOddsPage";
import TrendsPage from "./pages/TrendsPage";
import LeaguePage from "./pages/LeaguePage";
import TeamPage from "./pages/TeamPage";
import AnalysisReportsPage from "./pages/AnalysisReportsPage";
import FavoritesPage from "./pages/FavoritesPage";
import BetHistoryPage from "./pages/BetHistoryPage";
import SettingsPage from "./pages/SettingsPage";
import PipelineMonitor from "./pages/PipelineMonitor";
import ChatPanel from "./pages/ChatPanel";
import BoardPage from "./pages/BoardPage";
import DashboardPage from "./pages/DashboardPage";
import TokenStatsPage from "./pages/TokenStatsPage";
import "./index.css";

function App() {
  return (
    <ConfigProvider
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          colorPrimary: "#00FF9D",
          colorPrimaryBg: "rgba(0,255,157,0.08)",
          colorPrimaryBorder: "rgba(0,255,157,0.28)",
          colorBgContainer: "#0f1220",
          colorBgElevated: "#0b0d17",
          colorBgLayout: "#060810",
          colorText: "#e8eaf0",
          colorTextSecondary: "#9ba3b8",
          colorTextTertiary: "#555d72",
          colorSuccess: "#4ade80",
          colorWarning: "#ff9500",
          colorError: "#ef4444",
          borderRadius: 8,
          fontFamily: "'Space Grotesk', sans-serif",
          fontFamilyCode: "'JetBrains Mono', monospace",
        },
      }}
    >
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<BettingPage />} />
            <Route path="/fixture/:id" element={<FixtureDetailPage />} />
            <Route path="/dropping" element={<DroppingOddsPage />} />
            <Route path="/trends" element={<Navigate to="/trends/home_win" replace />} />
            <Route path="/trends/:type" element={<TrendsPage />} />
            <Route path="/league/:id" element={<LeaguePage />} />
            <Route path="/team/:id" element={<TeamPage />} />
            <Route path="/analysis" element={<AnalysisReportsPage />} />
            <Route path="/analysis/pipeline" element={<PipelineMonitor />} />
            <Route path="/analysis/chat" element={<ChatPanel />} />
            <Route path="/my" element={<FavoritesPage />} />
            <Route path="/my/bets" element={<BetHistoryPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/legacy/dashboard" element={<DashboardPage />} />
            <Route path="/legacy/board" element={<BoardPage />} />
            <Route path="/legacy/token-stats" element={<TokenStatsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
}

export default App;
