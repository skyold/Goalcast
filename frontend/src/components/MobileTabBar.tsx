import { NavLink } from "react-router-dom";
import {
  HomeOutlined, FireOutlined, LineChartOutlined,
  BarChartOutlined, UserOutlined,
} from "@ant-design/icons";

const tabs = [
  { to: "/", label: "浏览", icon: <HomeOutlined /> },
  { to: "/dropping", label: "跌水", icon: <FireOutlined /> },
  { to: "/trends/home_win", label: "趋势", icon: <LineChartOutlined /> },
  { to: "/analysis", label: "推荐", icon: <BarChartOutlined /> },
  { to: "/my", label: "我的", icon: <UserOutlined /> },
];

export default function MobileTabBar() {
  return (
    <div className="mobile-tabbar">
      {tabs.map((t) => (
        <NavLink key={t.to} to={t.to} end={t.to === "/"}
                 className={({ isActive }) => `tab ${isActive ? "on" : ""}`}>
          <div className="ico">{t.icon}</div>
          <div className="label">{t.label}</div>
        </NavLink>
      ))}
    </div>
  );
}
