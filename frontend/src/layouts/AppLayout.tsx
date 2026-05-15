import { Layout } from "antd";
import { Outlet } from "react-router-dom";
import SideNav from "../components/SideNav";
import MobileTabBar from "../components/MobileTabBar";

export default function AppLayout() {
  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Layout.Sider width={240} className="goalcast-sider" breakpoint="md" collapsedWidth={0}>
        <div className="goalcast-logo">⚽ GOALCAST</div>
        <SideNav />
      </Layout.Sider>
      <Layout>
        <Layout.Content className="goalcast-content">
          <Outlet />
        </Layout.Content>
      </Layout>
      <MobileTabBar />
    </Layout>
  );
}
