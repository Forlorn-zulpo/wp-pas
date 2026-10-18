import {
  LayoutDashboard,
  Package,
  Upload,
  Factory,
  ListTodo,
  Images,
  Bot,
  Cpu,
  SlidersHorizontal,
  ClipboardCheck,
  Globe,
  Link2,
  Send,
  Users,
  ScrollText,
  LogOut,
} from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import { ROLE_LABELS, useAuthStore } from "../../store/auth";

interface NavItem {
  to: string;
  label: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
}

const NAV_SECTIONS: { title: string; items: NavItem[] }[] = [
  {
    title: "概览",
    items: [{ to: "/app/dashboard", label: "仪表盘", icon: LayoutDashboard }],
  },
  {
    title: "商品",
    items: [
      { to: "/app/products", label: "商品中心", icon: Package },
      { to: "/app/imports", label: "导入", icon: Upload },
      { to: "/app/images", label: "图片素材", icon: Images },
    ],
  },
  {
    title: "采集",
    items: [
      { to: "/app/suppliers", label: "供应商", icon: Factory },
      { to: "/app/collection-jobs", label: "采集任务", icon: ListTodo },
    ],
  },
  {
    title: "AI",
    items: [
      { to: "/app/ai/providers", label: "AI 服务商", icon: Bot },
      { to: "/app/ai/models", label: "AI 模型", icon: Cpu },
      { to: "/app/ai/task-policies", label: "任务策略", icon: SlidersHorizontal },
    ],
  },
  {
    title: "审核与发布",
    items: [
      { to: "/app/reviews", label: "审核中心", icon: ClipboardCheck },
      { to: "/app/sites", label: "站点管理", icon: Globe },
      { to: "/app/site-products", label: "站点商品绑定", icon: Link2 },
      { to: "/app/publications", label: "发布任务", icon: Send },
    ],
  },
  {
    title: "系统",
    items: [
      { to: "/app/team/members", label: "团队成员", icon: Users },
      { to: "/app/settings/audit-logs", label: "审计日志", icon: ScrollText },
    ],
  },
];

export default function AppLayout() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  return (
    <div className="flex min-h-screen bg-gray-50 text-gray-900">
      <aside className="flex w-60 flex-shrink-0 flex-col border-r border-gray-200 bg-white">
        <div className="flex h-14 items-center border-b border-gray-200 px-4">
          <span className="text-sm font-semibold">商品运营后台</span>
        </div>
        <nav className="flex-1 overflow-y-auto px-2 py-3">
          {NAV_SECTIONS.map((section) => (
            <div key={section.title} className="mb-4">
              <p className="mb-1 px-2 text-xs font-medium uppercase tracking-wide text-gray-400">
                {section.title}
              </p>
              <ul className="space-y-0.5">
                {section.items.map(({ to, label, icon: Icon }) => (
                  <li key={to}>
                    <NavLink
                      to={to}
                      className={({ isActive }) =>
                        `flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm transition ${
                          isActive
                            ? "bg-gray-900 text-white"
                            : "text-gray-600 hover:bg-gray-100"
                        }`
                      }
                    >
                      <Icon size={16} />
                      {label}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>
        <div className="border-t border-gray-200 p-3">
          <div className="mb-2 px-1">
            <p className="truncate text-sm font-medium">{user?.full_name || user?.email}</p>
            <p className="text-xs text-gray-400">
              {user ? ROLE_LABELS[user.role] : ""}
            </p>
          </div>
          <button
            onClick={logout}
            className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-sm text-gray-600 hover:bg-gray-100"
          >
            <LogOut size={16} />
            退出登录
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
