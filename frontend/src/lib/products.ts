import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "./api";

export type ProductStatus = "draft" | "active" | "archived";

export interface Product {
  id: string;
  sku: string;
  title: string;
  description: string;
  category: string;
  brand: string;
  status: ProductStatus;
  price: string;
  cost_price: string | null;
  currency: string;
  attributes: Record<string, unknown>;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface PagedProducts {
  items: Product[];
  total: number;
  page: number;
  page_size: number;
}

export interface ProductListParams {
  page: number;
  pageSize: number;
  search?: string;
  status?: ProductStatus;
  category?: string;
  sortBy?: string;
  sortDir?: "asc" | "desc";
}

function buildQuery(params: ProductListParams): string {
  const qs = new URLSearchParams();
  qs.set("page", String(params.page));
  qs.set("page_size", String(params.pageSize));
  if (params.search) qs.set("search", params.search);
  if (params.status) qs.set("status", params.status);
  if (params.category) qs.set("category", params.category);
  if (params.sortBy) qs.set("sort_by", params.sortBy);
  if (params.sortDir) qs.set("sort_dir", params.sortDir);
  return qs.toString();
}

export function useProductsQuery(params: ProductListParams) {
  return useQuery({
    queryKey: ["products", params],
    queryFn: () => apiRequest<PagedProducts>(`/products?${buildQuery(params)}`),
    placeholderData: (prev) => prev,
  });
}

export interface BulkUpdatePayload {
  ids: string[];
  status?: ProductStatus;
  category?: string;
  brand?: string;
}

export function useBulkUpdateProducts() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: BulkUpdatePayload) =>
      apiRequest<{ updated_count: number; not_found_ids: string[] }>("/products/bulk-update", {
        method: "POST",
        body: payload,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["products"] });
    },
  });
}

export function useArchiveProduct() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiRequest<void>(`/products/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["products"] });
    },
  });
}

export const STATUS_LABELS: Record<ProductStatus, string> = {
  draft: "草稿",
  active: "上架",
  archived: "已归档",
};
