import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { apiRequest } from "../../lib/api";
import type { PublicationJob } from "../../lib/sites";

const STATUS_COLORS: Record<string, string> = {
  completed: "bg-green-100 text-green-700",
  partial: "bg-amber-100 text-amber-700",
  failed: "bg-red-100 text-red-700",
  pending: "bg-gray-100 text-gray-600",
  processing: "bg-blue-100 text-blue-700",
};

const STATUS_LABELS: Record<string, string> = {
  completed: "全部成功",
  partial: "部分成功",
  failed: "全部失败",
  pending: "等待中",
  processing: "处理中",
};

export default function PublicationsPage() {
  const { data: jobs, isLoading } = useQuery({
    queryKey: ["publications"],
    queryFn: () => apiRequest<PublicationJob[]>("/publications"),
  });
  const [expandedId, setExpandedId] = useState<string | null>(null);

  return (
    <div className="p-8">
      <h1 className="mb-4 text-2xl font-semibold">发布任务</h1>
      <p className="mb-4 text-xs text-gray-500">
        在商品详情页的"站点绑定"区块点发布按钮会在这里生成一条记录。失败的单项可以单独重试,不影响同批次已成功的商品。
      </p>

      {isLoading && <div className="text-sm text-gray-400">加载中...</div>}

      {jobs && jobs.length === 0 && (
        <div className="rounded-xl border border-dashed border-gray-300 bg-white p-10 text-center text-sm text-gray-400">
          还没有发布记录
        </div>
      )}

      {jobs && jobs.length > 0 && (
        <div className="space-y-2">
          {jobs.map((job) => (
            <div key={job.id} className="rounded-xl border border-gray-200 bg-white">
              <button
                onClick={() => setExpandedId((id) => (id === job.id ? null : job.id))}
                className="flex w-full items-center justify-between px-4 py-3 text-left text-sm"
              >
                <span className="text-xs text-gray-400">
                  {new Date(job.created_at).toLocaleString("zh-CN")}
                </span>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-500">
                    成功 {job.success_items} / 失败 {job.failed_items} / 共 {job.total_items}
                  </span>
                  <span className={`rounded-full px-2 py-0.5 text-xs ${STATUS_COLORS[job.status]}`}>
                    {STATUS_LABELS[job.status] ?? job.status}
                  </span>
                </div>
              </button>
              {expandedId === job.id && (
                <div className="border-t border-gray-100 px-4 py-3">
                  <table className="w-full text-xs">
                    <tbody>
                      {job.items.map((item) => (
                        <tr key={item.id} className="border-b border-gray-50">
                          <td className="py-1 pr-3 font-mono text-gray-400">
                            {item.site_product_id.slice(0, 8)}
                          </td>
                          <td className="py-1 pr-3">{item.status}</td>
                          <td className="py-1 pr-3 text-gray-500">{item.external_id ?? "—"}</td>
                          <td className="py-1 text-red-600">{item.error_message}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
