import { Eye, Link2, Unlink } from "lucide-react";
import { useState } from "react";
import {
  PLATFORM_LABELS,
  useBindProductToSite,
  usePublicationPreview,
  useSiteProductsQuery,
  useSitesQuery,
  useUnbindSiteProduct,
  useUpdateOverride,
} from "../../lib/sites";

const STATUS_LABELS: Record<string, string> = {
  bound: "已绑定",
  pending_review: "待审核",
  approved: "已通过审核",
  published: "已发布",
  unpublished: "已下架",
  failed: "失败",
};

export default function SiteBindingsSection({ productId }: { productId: string }) {
  const { data: sites } = useSitesQuery();
  const { data: bindings, isLoading } = useSiteProductsQuery({ productId });
  const bind = useBindProductToSite(productId);
  const unbind = useUnbindSiteProduct(productId);
  const updateOverride = useUpdateOverride(productId);
  const [selectedSiteId, setSelectedSiteId] = useState("");
  const [previewingId, setPreviewingId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [overrideTitle, setOverrideTitle] = useState("");

  const { data: preview } = usePublicationPreview(previewingId);

  const boundSiteIds = new Set((bindings ?? []).map((b) => b.site_id));
  const availableSites = (sites ?? []).filter((s) => !boundSiteIds.has(s.id));

  return (
    <section className="mt-6 rounded-xl border border-gray-200 bg-white p-5">
      <h2 className="mb-3 text-sm font-semibold text-gray-700">站点绑定</h2>

      {availableSites.length > 0 && (
        <div className="mb-4 flex items-center gap-2">
          <select
            className="rounded-lg border border-gray-300 px-2 py-1.5 text-sm"
            value={selectedSiteId}
            onChange={(e) => setSelectedSiteId(e.target.value)}
          >
            <option value="">选择站点...</option>
            {availableSites.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}({PLATFORM_LABELS[s.platform]})
              </option>
            ))}
          </select>
          <button
            disabled={!selectedSiteId || bind.isPending}
            onClick={() => bind.mutate(selectedSiteId, { onSuccess: () => setSelectedSiteId("") })}
            className="flex items-center gap-1 rounded-lg bg-gray-900 px-3 py-1.5 text-xs text-white disabled:opacity-50"
          >
            <Link2 size={12} />
            绑定
          </button>
        </div>
      )}

      {isLoading && <p className="text-sm text-gray-400">加载中...</p>}

      {bindings && bindings.length === 0 && (
        <p className="py-4 text-center text-sm text-gray-400">该商品还未绑定到任何站点</p>
      )}

      {bindings && bindings.length > 0 && (
        <div className="space-y-2">
          {bindings.map((b) => {
            const site = sites?.find((s) => s.id === b.site_id);
            return (
              <div key={b.id} className="rounded-lg border border-gray-100 p-3">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-sm font-medium">{site?.name ?? b.site_id}</span>
                    <span className="ml-2 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                      {STATUS_LABELS[b.status]}
                    </span>
                    {b.override.title && (
                      <span className="ml-2 text-xs text-amber-600">已自定义标题</span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => {
                        setPreviewingId(b.id);
                        setEditingId(null);
                      }}
                      title="发布预览"
                      className="rounded p-1 text-gray-400 hover:text-gray-900"
                    >
                      <Eye size={14} />
                    </button>
                    <button
                      onClick={() => {
                        setEditingId(editingId === b.id ? null : b.id);
                        setOverrideTitle(b.override.title ?? "");
                      }}
                      className="text-xs text-gray-500 hover:underline"
                    >
                      覆盖字段
                    </button>
                    <button
                      onClick={() => unbind.mutate(b.id)}
                      title="解除绑定"
                      className="rounded p-1 text-gray-400 hover:text-red-600"
                    >
                      <Unlink size={14} />
                    </button>
                  </div>
                </div>

                {editingId === b.id && (
                  <div className="mt-2 flex items-center gap-2 border-t border-gray-100 pt-2">
                    <input
                      placeholder="该站点专属标题,留空则沿用内部商品标题"
                      className="flex-1 rounded-lg border border-gray-300 px-2 py-1 text-xs"
                      value={overrideTitle}
                      onChange={(e) => setOverrideTitle(e.target.value)}
                    />
                    <button
                      onClick={() =>
                        updateOverride.mutate({
                          siteProductId: b.id,
                          patch: { title: overrideTitle || null },
                        })
                      }
                      className="rounded-lg bg-gray-900 px-2 py-1 text-xs text-white"
                    >
                      保存
                    </button>
                  </div>
                )}

                {previewingId === b.id && preview && (
                  <div className="mt-2 rounded-lg bg-gray-50 p-2 text-xs">
                    <p>
                      <span className="text-gray-400">标题:</span> {preview.title}
                    </p>
                    <p>
                      <span className="text-gray-400">价格:</span> {preview.price}
                    </p>
                    <p>
                      <span className="text-gray-400">已覆盖字段:</span>{" "}
                      {preview.overridden_fields.length > 0 ? preview.overridden_fields.join(", ") : "无,完全继承内部商品"}
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
