import { Link, useLocation } from "react-router-dom";
import { Menu } from "antd";
import {
  HomeOutlined, FireOutlined, LineChartOutlined,
  BarChartOutlined, ApiOutlined, MessageOutlined,
  StarOutlined, SettingOutlined,
} from "@ant-design/icons";

export default function SideNav() {
  const location = useLocation();
  const items = [
    {
      key: "browse", label: "浏览", type: "group" as const,
      children: [
        { key: "/", icon: <HomeOutlined />, label: <Link to="/">主页</Link> },
        { key: "/dropping", icon: <FireOutlined />, label: <Link to="/dropping">跌水榜</Link> },
        { key: "/trends/home_win", icon: <LineChartOutlined />,
          label: <Link to="/trends/home_win">趋势榜</Link> },
      ],
    },
    {
      key: "analysis", label: "分析", type: "group" as const,
      children: [
        { key: "/analysis", icon: <BarChartOutlined />, label: <Link to="/analysis">分析报告</Link> },
        { key: "/analysis/pipeline", icon: <ApiOutlined />,
          label: <Link to="/analysis/pipeline">Pipeline</Link> },
        { key: "/analysis/chat", icon: <MessageOutlined />,
          label: <Link to="/analysis/chat">对话</Link> },
      ],
    },
    {
      key: "my", label: "我的", type: "group" as const,
      children: [
        { key: "/my", icon: <StarOutlined />, label: <Link to="/my">收藏</Link> },
        { key: "/settings", icon: <SettingOutlined />, label: <Link to="/settings">设置</Link> },
      ],
    },
  ];
  return (
    <Menu
      mode="inline"
      theme="dark"
      selectedKeys={[location.pathname]}
      style={{ height: "100%", borderRight: 0, background: "transparent" }}
      items={items}
    />
  );
}
