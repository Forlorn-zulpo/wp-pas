import { ROLE_LABELS, useAuthStore } from "../store/auth";

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user);

  return (
    <div className="p-8">
      <h1 className="mb-1 text-2xl font-semibold">仪表盘</h1>
      <p className="mb-6 text-sm text-gray-500">
        欢迎回来,{user?.full_name || user?.email}({user ? ROLE_LABELS[user.role] : ""})
      </p>

      <div className="rounded-xl border border-dashed border-gray-300 bg-white p-6 text-sm text-gray-500">
        商品、任务与成本统计面板将在阶段 2/5/13 实现后接入真实数据,
        当前阶段仅完成认证、权限与布局骨架。
      </div>
    </div>
  );
}
