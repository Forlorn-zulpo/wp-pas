import { Navigate, Route, Routes } from "react-router-dom";
import ProtectedRoute from "./components/ProtectedRoute";
import AppLayout from "./components/layout/AppLayout";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import ProductsPage from "./pages/products/ProductsPage";
import ProductDetailPage from "./pages/products/ProductDetailPage";
import ImportsPage from "./pages/imports/ImportsPage";
import SitesPage from "./pages/sites/SitesPage";
import PublicationsPage from "./pages/publications/PublicationsPage";
import SuppliersPage from "./pages/suppliers/SuppliersPage";
import AIConfigPage from "./pages/ai/AIConfigPage";
import ReviewsPage from "./pages/reviews/ReviewsPage";
import PlaceholderPage from "./pages/PlaceholderPage";

const PLACEHOLDERS: { path: string; title: string; phase: string }[] = [
  { path: "images", title: "图片素材(独立素材库,目前通过商品详情页管理)", phase: "阶段 2 后续" },
  { path: "collection-jobs", title: "采集任务(队列已建,无具体供应商抓取器)", phase: "阶段 6" },
  { path: "site-products", title: "站点商品绑定(已整合进商品详情页)", phase: "阶段 3 完成" },
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
          <Route path="products/:productId" element={<ProductDetailPage />} />
          <Route path="imports" element={<ImportsPage />} />
          <Route path="sites" element={<SitesPage />} />
          <Route path="publications" element={<PublicationsPage />} />
          <Route path="suppliers" element={<SuppliersPage />} />
          <Route path="ai/providers" element={<AIConfigPage />} />
          <Route path="ai/models" element={<AIConfigPage />} />
          <Route path="ai/task-policies" element={<AIConfigPage />} />
          <Route path="reviews" element={<ReviewsPage />} />
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
