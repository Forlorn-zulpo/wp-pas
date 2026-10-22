import { Plus } from "lucide-react";
import { useState } from "react";
import type { CollectionMethod } from "../../lib/phase5";
import { COLLECTION_METHOD_LABELS, useCreateSupplier, useSuppliersQuery } from "../../lib/phase5";

export default function SuppliersPage() {
  const { data: suppliers, isLoading } = useSuppliersQuery();
  const createSupplier = useCreateSupplier();
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [website, setWebsite] = useState("");
  const [method, setMethod] = useState<CollectionMethod>("manual");

  const submit = () => {
    createSupplier.mutate(
      { name, website, collection_method: method },
      { onSuccess: () => { setShowForm(false); setName(""); setWebsite(""); } }
    );
  };

  return (
    <div className="p-8">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">供应商</h1>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="flex items-center gap-1 rounded-lg bg-gray-900 px-3 py-1.5 text-sm text-white hover:bg-gray-700"
        >
          <Plus size={14} />
          新建供应商
        </button>
      </div>

      {showForm && (
        <div className="mb-4 rounded-xl border border-gray-200 bg-white p-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs text-gray-500">名称</label>
              <input
                className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-gray-500">官网</label>
              <input
                className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm"
                value={website}
                onChange={(e) => setWebsite(e.target.value)}
              />
            </div>
            <div className="col-span-2">
              <label className="mb-1 block text-xs text-gray-500">采集方式</label>
              <select
                className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm"
                value={method}
                onChange={(e) => setMethod(e.target.value as CollectionMethod)}
              >
                {Object.entries(COLLECTION_METHOD_LABELS).map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="mt-3 flex gap-2">
            <button
              onClick={submit}
              disabled={!name || createSupplier.isPending}
              className="rounded-lg bg-gray-900 px-3 py-1.5 text-sm text-white disabled:opacity-50"
            >
              创建
            </button>
            <button onClick={() => setShowForm(false)} className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm">
              取消
            </button>
          </div>
        </div>
      )}

      {isLoading && <div className="text-sm text-gray-400">加载中...</div>}

      {suppliers && suppliers.length === 0 && !showForm && (
        <div className="rounded-xl border border-dashed border-gray-300 bg-white p-10 text-center text-sm text-gray-400">
          还没有供应商
        </div>
      )}

      {suppliers && suppliers.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
          <table className="w-full text-sm">
            <thead className="border-b border-gray-200 bg-gray-50 text-left text-xs text-gray-500">
              <tr>
                <th className="px-3 py-2">名称</th>
                <th className="px-3 py-2">采集方式</th>
                <th className="px-3 py-2">状态</th>
                <th className="px-3 py-2">凭据</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {suppliers.map((s) => (
                <tr key={s.id}>
                  <td className="px-3 py-2 font-medium">{s.name}</td>
                  <td className="px-3 py-2 text-gray-500">{COLLECTION_METHOD_LABELS[s.collection_method]}</td>
                  <td className="px-3 py-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs ${s.status === "active" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}>
                      {s.status === "active" ? "启用" : "停用"}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-xs text-gray-400">{s.has_credentials ? "已配置" : "无"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
