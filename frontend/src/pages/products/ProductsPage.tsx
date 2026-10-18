import { useState } from "react";
import { ArchiveIcon, SearchIcon } from "lucide-react";
import {
  STATUS_LABELS,
  useArchiveProduct,
  useBulkUpdateProducts,
  useProductsQuery,
} from "../../lib/products";
import type { ProductStatus } from "../../lib/products";

const STATUS_BADGE: Record<ProductStatus, string> = {
  draft: "bg-gray-100 text-gray-600",
  active: "bg-green-100 text-green-700",
  archived: "bg-amber-100 text-amber-700",
};

export default function ProductsPage() {
  const [page, setPage] = useState(1);
  const pageSize = 20;
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [status, setStatus] = useState<ProductStatus | undefined>(undefined);
  const [sortBy, setSortBy] = useState("created_at");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const { data, isLoading, isError, error, isFetching } = useProductsQuery({
    page,
    pageSize,
    search: search || undefined,
    status,
    sortBy,
    sortDir,
  });

  const bulkUpdate = useBulkUpdateProducts();
  const archiveProduct = useArchiveProduct();

  const toggleSort = (field: string) => {
    if (sortBy === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(field);
      setSortDir("asc");
    }
  };

  const toggleSelectAll = () => {
    if (!data) return;
    if (selected.size === data.items.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(data.items.map((p) => p.id)));
    }
  };

  const toggleSelectOne = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const totalPages = data ? Math.max(1, Math.ceil(data.total / pageSize)) : 1;

  return (
    <div className="p-8">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">商品中心</h1>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setPage(1);
            setSearch(searchInput);
          }}
          className="flex items-center gap-1"
        >
          <div className="relative">
            <SearchIcon size={14} className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="搜索标题或 SKU"
              className="w-56 rounded-lg border border-gray-300 py-1.5 pl-7 pr-3 text-sm outline-none focus:border-gray-900"
            />
          </div>
        </form>

        <select
          value={status ?? ""}
          onChange={(e) => {
            setPage(1);
            setStatus((e.target.value || undefined) as ProductStatus | undefined);
          }}
          className="rounded-lg border border-gray-300 px-2 py-1.5 text-sm"
        >
          <option value="">全部状态</option>
          {Object.entries(STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>

        {selected.size > 0 && (
          <div className="ml-auto flex items-center gap-2 text-sm text-gray-600">
            已选 {selected.size} 项
            <button
              onClick={() =>
                bulkUpdate.mutate(
                  { ids: Array.from(selected), status: "active" },
                  { onSuccess: () => setSelected(new Set()) }
                )
              }
              className="rounded-lg bg-gray-900 px-3 py-1.5 text-white hover:bg-gray-700"
            >
              批量上架
            </button>
          </div>
        )}
      </div>

      {isLoading && (
        <div className="rounded-xl border border-gray-200 bg-white p-10 text-center text-sm text-gray-400">
          加载中...
        </div>
      )}

      {isError && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-700">
          加载失败:{error instanceof Error ? error.message : "未知错误"}
        </div>
      )}

      {data && data.items.length === 0 && !isLoading && (
        <div className="rounded-xl border border-dashed border-gray-300 bg-white p-10 text-center text-sm text-gray-400">
          没有匹配的商品
        </div>
      )}

      {data && data.items.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
          <table className="w-full text-sm">
            <thead className="border-b border-gray-200 bg-gray-50 text-left text-xs text-gray-500">
              <tr>
                <th className="w-10 px-3 py-2">
                  <input
                    type="checkbox"
                    checked={selected.size === data.items.length}
                    onChange={toggleSelectAll}
                  />
                </th>
                <th
                  className="cursor-pointer px-3 py-2"
                  onClick={() => toggleSort("sku")}
                >
                  SKU {sortBy === "sku" && (sortDir === "asc" ? "↑" : "↓")}
                </th>
                <th className="cursor-pointer px-3 py-2" onClick={() => toggleSort("title")}>
                  标题 {sortBy === "title" && (sortDir === "asc" ? "↑" : "↓")}
                </th>
                <th className="px-3 py-2">分类</th>
                <th className="cursor-pointer px-3 py-2" onClick={() => toggleSort("price")}>
                  价格 {sortBy === "price" && (sortDir === "asc" ? "↑" : "↓")}
                </th>
                <th className="px-3 py-2">状态</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.items.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50">
                  <td className="px-3 py-2">
                    <input
                      type="checkbox"
                      checked={selected.has(p.id)}
                      onChange={() => toggleSelectOne(p.id)}
                    />
                  </td>
                  <td className="px-3 py-2 font-mono text-xs text-gray-600">{p.sku}</td>
                  <td className="px-3 py-2 font-medium">{p.title}</td>
                  <td className="px-3 py-2 text-gray-500">{p.category || "—"}</td>
                  <td className="px-3 py-2">
                    {p.currency} {p.price}
                  </td>
                  <td className="px-3 py-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs ${STATUS_BADGE[p.status]}`}>
                      {STATUS_LABELS[p.status]}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-right">
                    {p.status !== "archived" && (
                      <button
                        onClick={() => archiveProduct.mutate(p.id)}
                        title="归档(非永久删除)"
                        className="text-gray-400 hover:text-red-600"
                      >
                        <ArchiveIcon size={16} />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="flex items-center justify-between border-t border-gray-200 px-3 py-2 text-xs text-gray-500">
            <span>
              共 {data.total} 条{isFetching ? " · 更新中..." : ""}
            </span>
            <div className="flex items-center gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="rounded border border-gray-300 px-2 py-1 disabled:opacity-40"
              >
                上一页
              </button>
              <span>
                {page} / {totalPages}
              </span>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
                className="rounded border border-gray-300 px-2 py-1 disabled:opacity-40"
              >
                下一页
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
