import { Upload } from "lucide-react";
import { useRef, useState } from "react";
import { useImportsQuery, useUploadCsvImport } from "../../lib/products";

const STATUS_LABELS: Record<string, string> = {
  pending: "等待中",
  processing: "处理中",
  completed: "完成",
  completed_with_errors: "部分成功",
  failed: "失败",
};

const STATUS_COLORS: Record<string, string> = {
  completed: "bg-green-100 text-green-700",
  completed_with_errors: "bg-amber-100 text-amber-700",
  failed: "bg-red-100 text-red-700",
  pending: "bg-gray-100 text-gray-600",
  processing: "bg-blue-100 text-blue-700",
};

export default function ImportsPage() {
  const { data: jobs, isLoading } = useImportsQuery();
  const upload = useUploadCsvImport();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadError(null);
    upload.mutate(file, {
      onSuccess: (job) => setExpandedId(job.id),
      onError: (err) => setUploadError(err instanceof Error ? err.message : "导入失败"),
    });
    e.target.value = "";
  };

  return (
    <div className="p-8">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">商品导入</h1>
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={upload.isPending}
          className="flex items-center gap-1 rounded-lg bg-gray-900 px-3 py-1.5 text-sm text-white hover:bg-gray-700 disabled:opacity-60"
        >
          <Upload size={14} />
          {upload.isPending ? "导入中..." : "上传 CSV"}
        </button>
        <input ref={fileInputRef} type="file" accept=".csv" className="hidden" onChange={handleFileChange} />
      </div>

      <p className="mb-4 text-xs text-gray-500">
        CSV 需包含列:<code className="rounded bg-gray-100 px-1">sku, title, price</code>,可选
        <code className="rounded bg-gray-100 px-1">category, brand, description, currency</code>。
        重复或非法行会被单独标记,不影响文件内其它行的导入。
      </p>

      {uploadError && (
        <div className="mb-4 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{uploadError}</div>
      )}

      {isLoading && <div className="text-sm text-gray-400">加载中...</div>}

      {jobs && jobs.length === 0 && (
        <div className="rounded-xl border border-dashed border-gray-300 bg-white p-10 text-center text-sm text-gray-400">
          还没有导入记录
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
                <div>
                  <span className="font-medium">{job.filename}</span>
                  <span className="ml-2 text-xs text-gray-400">
                    {new Date(job.created_at).toLocaleString("zh-CN")}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-500">
                    成功 {job.success_rows} / 共 {job.total_rows}
                  </span>
                  <span className={`rounded-full px-2 py-0.5 text-xs ${STATUS_COLORS[job.status]}`}>
                    {STATUS_LABELS[job.status] ?? job.status}
                  </span>
                </div>
              </button>

              {expandedId === job.id && job.errors.length > 0 && (
                <div className="border-t border-gray-100 px-4 py-3">
                  <p className="mb-2 text-xs font-medium text-gray-500">错误详情 ({job.errors.length})</p>
                  <div className="max-h-48 overflow-y-auto">
                    <table className="w-full text-xs">
                      <tbody>
                        {job.errors.map((err, i) => (
                          <tr key={i} className="border-b border-gray-50">
                            <td className="py-1 pr-3 text-gray-400">第 {err.row} 行</td>
                            <td className="py-1 pr-3 text-gray-500">{err.field}</td>
                            <td className="py-1 text-red-600">{err.message}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
