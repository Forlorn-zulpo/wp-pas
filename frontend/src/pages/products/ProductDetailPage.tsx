import { Star, Trash2, Upload } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import {
  STATUS_LABELS,
  assetFileUrl,
  useDeleteAsset,
  useProductQuery,
  useSetPrimaryAsset,
  useUpdateProduct,
  useUploadAsset,
} from "../../lib/products";
import SiteBindingsSection from "./SiteBindingsSection";

export default function ProductDetailPage() {
  const { productId } = useParams<{ productId: string }>();
  const id = productId!;
  const { data: product, isLoading, isError, error } = useProductQuery(id);
  const updateProduct = useUpdateProduct(id);
  const uploadAsset = useUploadAsset(id);
  const setPrimary = useSetPrimaryAsset(id);
  const deleteAsset = useDeleteAsset(id);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [form, setForm] = useState({ title: "", price: "", category: "", brand: "", description: "" });
  const [saveError, setSaveError] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  useEffect(() => {
    if (product) {
      setForm({
        title: product.title,
        price: product.price,
        category: product.category,
        brand: product.brand,
        description: product.description,
      });
    }
  }, [product]);

  if (isLoading) {
    return <div className="p-8 text-sm text-gray-400">加载中...</div>;
  }
  if (isError || !product) {
    return (
      <div className="p-8 text-sm text-red-600">
        加载失败:{error instanceof Error ? error.message : "商品不存在"}
      </div>
    );
  }

  const handleSave = () => {
    setSaveError(null);
    updateProduct.mutate(
      { version: product.version, ...form },
      { onError: (err) => setSaveError(err instanceof Error ? err.message : "保存失败") }
    );
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadError(null);
    uploadAsset.mutate(file, {
      onError: (err) => setUploadError(err instanceof Error ? err.message : "上传失败"),
    });
    e.target.value = "";
  };

  return (
    <div className="mx-auto max-w-3xl p-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">{product.title}</h1>
          <p className="font-mono text-xs text-gray-400">{product.sku}</p>
        </div>
        <span className="rounded-full bg-gray-100 px-3 py-1 text-xs text-gray-600">
          {STATUS_LABELS[product.status]}
        </span>
      </div>

      <section className="mb-6 rounded-xl border border-gray-200 bg-white p-5">
        <h2 className="mb-3 text-sm font-semibold text-gray-700">基本信息</h2>
        <div className="grid grid-cols-2 gap-4">
          <div className="col-span-2">
            <label className="mb-1 block text-xs text-gray-500">标题</label>
            <input
              className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm outline-none focus:border-gray-900"
              value={form.title}
              onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-gray-500">价格</label>
            <input
              className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm outline-none focus:border-gray-900"
              value={form.price}
              onChange={(e) => setForm((f) => ({ ...f, price: e.target.value }))}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-gray-500">分类</label>
            <input
              className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm outline-none focus:border-gray-900"
              value={form.category}
              onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-gray-500">品牌</label>
            <input
              className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm outline-none focus:border-gray-900"
              value={form.brand}
              onChange={(e) => setForm((f) => ({ ...f, brand: e.target.value }))}
            />
          </div>
          <div className="col-span-2">
            <label className="mb-1 block text-xs text-gray-500">描述</label>
            <textarea
              rows={4}
              className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm outline-none focus:border-gray-900"
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            />
          </div>
        </div>

        {saveError && (
          <div className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700">{saveError}</div>
        )}

        <button
          onClick={handleSave}
          disabled={updateProduct.isPending}
          className="mt-4 rounded-lg bg-gray-900 px-4 py-1.5 text-sm text-white hover:bg-gray-700 disabled:opacity-60"
        >
          {updateProduct.isPending ? "保存中..." : "保存"}
        </button>
      </section>

      <section className="rounded-xl border border-gray-200 bg-white p-5">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-700">图片素材</h2>
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadAsset.isPending}
            className="flex items-center gap-1 rounded-lg border border-gray-300 px-3 py-1.5 text-xs hover:bg-gray-50 disabled:opacity-60"
          >
            <Upload size={14} />
            {uploadAsset.isPending ? "上传中..." : "上传图片"}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp,image/gif"
            className="hidden"
            onChange={handleFileChange}
          />
        </div>

        {uploadError && (
          <div className="mb-3 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700">{uploadError}</div>
        )}

        {product.assets.length === 0 ? (
          <p className="py-6 text-center text-sm text-gray-400">暂无图片</p>
        ) : (
          <div className="grid grid-cols-4 gap-3">
            {product.assets.map((asset) => (
              <div key={asset.id} className="group relative overflow-hidden rounded-lg border border-gray-200">
                <img
                  src={assetFileUrl(asset.id)}
                  alt={asset.original_filename}
                  className="aspect-square w-full object-cover"
                />
                {asset.is_primary && (
                  <span className="absolute left-1 top-1 rounded-full bg-gray-900/80 px-1.5 py-0.5 text-[10px] text-white">
                    主图
                  </span>
                )}
                <div className="absolute inset-x-0 bottom-0 flex items-center justify-end gap-1 bg-gradient-to-t from-black/60 to-transparent p-1 opacity-0 transition group-hover:opacity-100">
                  {!asset.is_primary && (
                    <button
                      title="设为主图"
                      onClick={() => setPrimary.mutate(asset.id)}
                      className="rounded bg-white/90 p-1 hover:bg-white"
                    >
                      <Star size={12} />
                    </button>
                  )}
                  <button
                    title="删除"
                    onClick={() => deleteAsset.mutate(asset.id)}
                    className="rounded bg-white/90 p-1 text-red-600 hover:bg-white"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <SiteBindingsSection productId={id} />
    </div>
  );
}
