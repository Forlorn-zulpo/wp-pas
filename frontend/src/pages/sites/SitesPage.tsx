import { Plug, Plus } from "lucide-react";
import { useState } from "react";
import type { CreateSitePayload, SitePlatform } from "../../lib/sites";
import { PLATFORM_LABELS, useCreateSite, useSitesQuery, useTestConnection } from "../../lib/sites";

function NewSiteForm({ onClose }: { onClose: () => void }) {
  const createSite = useCreateSite();
  const [form, setForm] = useState<CreateSitePayload>({
    name: "",
    platform: "woocommerce",
    base_url: "",
    credentials: {},
  });
  const [error, setError] = useState<string | null>(null);

  const submit = () => {
    setError(null);
    createSite.mutate(form, {
      onSuccess: onClose,
      onError: (err) => setError(err instanceof Error ? err.message : "创建失败"),
    });
  };

  return (
    <div className="mb-4 rounded-xl border border-gray-200 bg-white p-4">
      <h2 className="mb-3 text-sm font-semibold">新建站点</h2>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="mb-1 block text-xs text-gray-500">名称</label>
          <input
            className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-gray-500">平台</label>
          <select
            className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm"
            value={form.platform}
            onChange={(e) => setForm((f) => ({ ...f, platform: e.target.value as SitePlatform }))}
          >
            {Object.entries(PLATFORM_LABELS).map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </select>
        </div>
        <div className="col-span-2">
          <label className="mb-1 block text-xs text-gray-500">站点地址</label>
          <input
            placeholder="https://your-store.com"
            className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm"
            value={form.base_url}
            onChange={(e) => setForm((f) => ({ ...f, base_url: e.target.value }))}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-gray-500">API Key / Consumer Key</label>
          <input
            className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm"
            onChange={(e) =>
              setForm((f) => ({ ...f, credentials: { ...f.credentials, key: e.target.value } }))
            }
          />
        </div>
        <div>
          <label className="mb-1 block text-xs text-gray-500">API Secret</label>
          <input
            type="password"
            className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm"
            onChange={(e) =>
              setForm((f) => ({ ...f, credentials: { ...f.credentials, secret: e.target.value } }))
            }
          />
        </div>
      </div>
      {error && <div className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700">{error}</div>}
      <div className="mt-3 flex gap-2">
        <button
          onClick={submit}
          disabled={createSite.isPending || !form.name || !form.base_url}
          className="rounded-lg bg-gray-900 px-3 py-1.5 text-sm text-white disabled:opacity-50"
        >
          {createSite.isPending ? "创建中..." : "创建"}
        </button>
        <button onClick={onClose} className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm">
          取消
        </button>
      </div>
    </div>
  );
}

export default function SitesPage() {
  const { data: sites, isLoading } = useSitesQuery();
  const testConnection = useTestConnection();
  const [showForm, setShowForm] = useState(false);
  const [testingId, setTestingId] = useState<string | null>(null);

  return (
    <div className="p-8">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">站点管理</h1>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="flex items-center gap-1 rounded-lg bg-gray-900 px-3 py-1.5 text-sm text-white hover:bg-gray-700"
        >
          <Plus size={14} />
          新建站点
        </button>
      </div>

      {showForm && <NewSiteForm onClose={() => setShowForm(false)} />}

      {isLoading && <div className="text-sm text-gray-400">加载中...</div>}

      {sites && sites.length === 0 && !showForm && (
        <div className="rounded-xl border border-dashed border-gray-300 bg-white p-10 text-center text-sm text-gray-400">
          还没有配置站点
        </div>
      )}

      {sites && sites.length > 0 && (
        <div className="grid grid-cols-2 gap-3">
          {sites.map((site) => (
            <div key={site.id} className="rounded-xl border border-gray-200 bg-white p-4">
              <div className="mb-1 flex items-center justify-between">
                <h3 className="font-medium">{site.name}</h3>
                <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                  {PLATFORM_LABELS[site.platform]}
                </span>
              </div>
              <p className="mb-2 truncate text-xs text-gray-400">{site.base_url}</p>
              <div className="mb-3 flex items-center gap-3 text-xs">
                <span className={site.has_credentials ? "text-green-600" : "text-gray-400"}>
                  {site.has_credentials ? "凭据已配置" : "未配置凭据"}
                </span>
                {site.last_connection_test_ok !== null && (
                  <span className={site.last_connection_test_ok ? "text-green-600" : "text-red-600"}>
                    {site.last_connection_test_ok ? "上次测试成功" : "上次测试失败"}
                  </span>
                )}
              </div>
              <button
                onClick={() => {
                  setTestingId(site.id);
                  testConnection.mutate(site.id, { onSettled: () => setTestingId(null) });
                }}
                disabled={testingId === site.id}
                className="flex items-center gap-1 rounded-lg border border-gray-300 px-3 py-1.5 text-xs hover:bg-gray-50 disabled:opacity-60"
              >
                <Plug size={12} />
                {testingId === site.id ? "测试中..." : "测试连接"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
