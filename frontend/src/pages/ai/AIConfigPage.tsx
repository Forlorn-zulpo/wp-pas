import { useState } from "react";
import type { AIProviderType, AITaskType } from "../../lib/phase5";
import {
  PROVIDER_TYPE_LABELS,
  TASK_TYPE_LABELS,
  useAIModelsQuery,
  useAIProvidersQuery,
  useAITaskPoliciesQuery,
  useAIUsageSummaryQuery,
  useCreateAIModel,
  useCreateAIProvider,
  useCreateAITaskPolicy,
} from "../../lib/phase5";

export default function AIConfigPage() {
  const { data: providers } = useAIProvidersQuery();
  const { data: models } = useAIModelsQuery();
  const { data: policies } = useAITaskPoliciesQuery();
  const { data: usage } = useAIUsageSummaryQuery();

  const createProvider = useCreateAIProvider();
  const createModel = useCreateAIModel();
  const createPolicy = useCreateAITaskPolicy();

  const [providerForm, setProviderForm] = useState({ name: "", provider_type: "anthropic" as AIProviderType, api_key: "" });
  const [modelForm, setModelForm] = useState({ provider_id: "", model_id: "", supports_vision: false });
  const [policyForm, setPolicyForm] = useState({ task_type: "title_generation" as AITaskType, model_id: "" });

  return (
    <div className="p-8">
      <h1 className="mb-4 text-2xl font-semibold">AI 配置</h1>

      <div className="grid grid-cols-2 gap-4">
        <section className="rounded-xl border border-gray-200 bg-white p-4">
          <h2 className="mb-2 text-sm font-semibold">服务商</h2>
          <div className="mb-3 space-y-1">
            {providers?.map((p) => (
              <div key={p.id} className="flex items-center justify-between text-sm">
                <span>{p.name}({PROVIDER_TYPE_LABELS[p.provider_type]})</span>
                <span className={p.has_api_key ? "text-xs text-green-600" : "text-xs text-gray-400"}>
                  {p.has_api_key ? "已配置Key" : "未配置"}
                </span>
              </div>
            ))}
          </div>
          <div className="flex flex-wrap gap-1">
            <input
              placeholder="名称"
              className="w-24 rounded border border-gray-300 px-2 py-1 text-xs"
              value={providerForm.name}
              onChange={(e) => setProviderForm((f) => ({ ...f, name: e.target.value }))}
            />
            <select
              className="rounded border border-gray-300 px-2 py-1 text-xs"
              value={providerForm.provider_type}
              onChange={(e) => setProviderForm((f) => ({ ...f, provider_type: e.target.value as AIProviderType }))}
            >
              {Object.entries(PROVIDER_TYPE_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
            <input
              placeholder="API Key"
              type="password"
              className="w-24 rounded border border-gray-300 px-2 py-1 text-xs"
              value={providerForm.api_key}
              onChange={(e) => setProviderForm((f) => ({ ...f, api_key: e.target.value }))}
            />
            <button
              onClick={() => createProvider.mutate(providerForm, { onSuccess: () => setProviderForm({ name: "", provider_type: "anthropic", api_key: "" }) })}
              disabled={!providerForm.name}
              className="rounded bg-gray-900 px-2 py-1 text-xs text-white disabled:opacity-50"
            >
              添加
            </button>
          </div>
        </section>

        <section className="rounded-xl border border-gray-200 bg-white p-4">
          <h2 className="mb-2 text-sm font-semibold">模型</h2>
          <div className="mb-3 space-y-1">
            {models?.map((m) => (
              <div key={m.id} className="text-sm">
                {m.display_name || m.model_id}
                {m.supports_vision && <span className="ml-1 text-xs text-blue-600">视觉</span>}
              </div>
            ))}
          </div>
          <div className="flex flex-wrap gap-1">
            <select
              className="rounded border border-gray-300 px-2 py-1 text-xs"
              value={modelForm.provider_id}
              onChange={(e) => setModelForm((f) => ({ ...f, provider_id: e.target.value }))}
            >
              <option value="">选择服务商</option>
              {providers?.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
            <input
              placeholder="model_id"
              className="w-28 rounded border border-gray-300 px-2 py-1 text-xs"
              value={modelForm.model_id}
              onChange={(e) => setModelForm((f) => ({ ...f, model_id: e.target.value }))}
            />
            <button
              onClick={() => createModel.mutate(modelForm, { onSuccess: () => setModelForm({ provider_id: "", model_id: "", supports_vision: false }) })}
              disabled={!modelForm.provider_id || !modelForm.model_id}
              className="rounded bg-gray-900 px-2 py-1 text-xs text-white disabled:opacity-50"
            >
              添加
            </button>
          </div>
        </section>

        <section className="rounded-xl border border-gray-200 bg-white p-4">
          <h2 className="mb-2 text-sm font-semibold">任务策略</h2>
          <div className="mb-3 space-y-1">
            {policies?.map((p) => (
              <div key={p.id} className="text-sm">{TASK_TYPE_LABELS[p.task_type]}</div>
            ))}
          </div>
          <div className="flex flex-wrap gap-1">
            <select
              className="rounded border border-gray-300 px-2 py-1 text-xs"
              value={policyForm.task_type}
              onChange={(e) => setPolicyForm((f) => ({ ...f, task_type: e.target.value as AITaskType }))}
            >
              {Object.entries(TASK_TYPE_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
            <select
              className="rounded border border-gray-300 px-2 py-1 text-xs"
              value={policyForm.model_id}
              onChange={(e) => setPolicyForm((f) => ({ ...f, model_id: e.target.value }))}
            >
              <option value="">选择模型</option>
              {models?.map((m) => <option key={m.id} value={m.id}>{m.display_name || m.model_id}</option>)}
            </select>
            <button
              onClick={() => createPolicy.mutate(policyForm, { onSuccess: () => setPolicyForm({ task_type: "title_generation", model_id: "" }) })}
              disabled={!policyForm.model_id}
              className="rounded bg-gray-900 px-2 py-1 text-xs text-white disabled:opacity-50"
            >
              添加
            </button>
          </div>
        </section>

        <section className="rounded-xl border border-gray-200 bg-white p-4">
          <h2 className="mb-2 text-sm font-semibold">用量统计</h2>
          {usage && usage.length === 0 && <p className="text-xs text-gray-400">暂无调用记录</p>}
          {usage?.map((u) => (
            <div key={u.task_type} className="flex justify-between text-xs text-gray-600">
              <span>{TASK_TYPE_LABELS[u.task_type]}</span>
              <span>{u.call_count} 次 · ${u.total_cost}</span>
            </div>
          ))}
        </section>
      </div>
    </div>
  );
}
