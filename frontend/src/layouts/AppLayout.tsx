import { Layout } from "antd";
import { Outlet } from "react-router-dom";
import dayjs from "dayjs";
import SideNav from "../components/SideNav";
import MobileTabBar from "../components/MobileTabBar";
import { useWebSocket } from "../hooks/useWebSocket";
import { useAppStore } from "../store/appStore";

export default function AppLayout() {
  // Restore WS lifecycle (dropped during T3 rewrite; required by PipelineMonitor and live status indicator).
  useWebSocket();
  const wsConnected = useAppStore((s) => s.wsConnected);
  const today = dayjs().format("YYYY-MM-DD ddd");

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Layout.Sider width={240} className="goalcast-sider" breakpoint="md" collapsedWidth={0}>
        <div className="goalcast-logo">⚽ GOALCAST</div>
        <SideNav />
      </Layout.Sider>
      <Layout>
        <Layout.Header className="goalcast-header">
          <div className="goalcast-header-title">Goalcast · OddAlerts Browse</div>
          <div className="goalcast-header-meta">
            <span className="goalcast-header-date">{today}</span>
            <span
              className={`goalcast-ws-dot ${wsConnected ? "on" : "off"}`}
              aria-label={wsConnected ? "WS 已连接" : "WS 未连接"}
              title={wsConnected ? "WS 已连接" : "WS 未连接"}
            />
            <span className="goalcast-ws-label">{wsConnected ? "在线" : "离线"}</span>
          </div>
        </Layout.Header>
        <Layout.Content className="goalcast-content">
          <Outlet />
        </Layout.Content>
      </Layout>
      <MobileTabBar />
    </Layout>
  );
}
