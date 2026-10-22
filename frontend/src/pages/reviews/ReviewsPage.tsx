import { useState } from "react";
import { useDecideReview, useReviewsQuery } from "../../lib/phase5";

export default function ReviewsPage() {
  const [statusFilter, setStatusFilter] = useState("pending");
  const { data: reviews, isLoading } = useReviewsQuery(statusFilter);
  const decide = useDecideReview();

  return (
    <div className="p-8">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">审核中心</h1>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-lg border border-gray-300 px-2 py-1.5 text-sm"
        >
          <option value="pending">待审核</option>
          <option value="approved">已通过</option>
          <option value="rejected">已拒绝</option>
        </select>
      </div>

      {isLoading && <div className="text-sm text-gray-400">加载中...</div>}

      {reviews && reviews.length === 0 && (
        <div className="rounded-xl border border-dashed border-gray-300 bg-white p-10 text-center text-sm text-gray-400">
          没有符合条件的审核记录
        </div>
      )}

      {reviews && reviews.length > 0 && (
        <div className="space-y-2">
          {reviews.map((r) => (
            <div key={r.id} className="flex items-center justify-between rounded-xl border border-gray-200 bg-white p-4">
              <div>
                <p className="font-mono text-xs text-gray-400">绑定 ID: {r.site_product_id.slice(0, 8)}</p>
                {r.notes && <p className="mt-1 text-sm text-gray-600">{r.notes}</p>}
                <p className="mt-1 text-xs text-gray-400">{new Date(r.created_at).toLocaleString("zh-CN")}</p>
              </div>
              {r.status === "pending" && (
                <div className="flex gap-2">
                  <button
                    onClick={() => decide.mutate({ id: r.id, decision: "approve" })}
                    className="rounded-lg bg-green-600 px-3 py-1.5 text-xs text-white hover:bg-green-700"
                  >
                    通过
                  </button>
                  <button
                    onClick={() => decide.mutate({ id: r.id, decision: "reject" })}
                    className="rounded-lg bg-red-50 px-3 py-1.5 text-xs text-red-600 hover:bg-red-100"
                  >
                    拒绝
                  </button>
                </div>
              )}
              {r.status !== "pending" && (
                <span className={`rounded-full px-2 py-0.5 text-xs ${r.status === "approved" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                  {r.status === "approved" ? "已通过" : "已拒绝"}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
