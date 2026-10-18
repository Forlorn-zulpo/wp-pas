import { Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import AppLayout from "./components/layout/AppLayout";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import ProductsPage from "./pages/products/ProductsPage";
import PlaceholderPage from "./pages/PlaceholderPage";

const PLACEHOLDERS: { path: string; title: string; phase: string }[] = [
  { path: "imports", title: "导入", phase: "阶段 2" },
  { path: "images", title: "图片素材", phase: "阶段 2" },
  { path: "suppliers", title: "供应商", phase: "阶段 5" },
  { path: "collection-jobs", title: "采集任务", phase: "阶段 5" },
  { path: "ai/providers", title: "AI 服务商", phase: "阶段 5" },
  { path: "ai/models", title: "AI 模型", phase: "阶段 5" },
  { path: "ai/task-policies", title: "AI 任务策略", phase: "阶段 5" },
  { path: "reviews", title: "审核中心", phase: "阶段 5" },
  { path: "sites", title: "站点管理", phase: "阶段 3" },
  { path: "site-products", title: "站点商品绑定", phase: "阶段 3" },
  { path: "publications", title: "发布任务", phase: "阶段 3/4" },
  { path: "team/members", title: "团队成员", phase: "阶段 1 后续" },
  { path: "settings/audit-logs", title: "审计日志", phase: "阶段 2 后续" },
];

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route element={<ProtectedRoute />}>
        <Route path="/app" element={<AppLayout />}>
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="products" element={<ProductsPage />} />
          {PLACEHOLDERS.map(({ path, title, phase }) => (
            <Route key={path} path={path} element={<PlaceholderPage title={title} phase={phase} />} />
          ))}
        </Route>
      </Route>

      <Route path="/" element={<Navigate to="/app/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/app/dashboard" replace />} />
    </Routes>
  );
}
