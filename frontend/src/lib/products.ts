import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest, getTokens } from "./api";

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

export interface Variant {
  id: string;
  sku: string;
  options: Record<string, string>;
  price_override: string | null;
  stock_quantity: number;
  barcode: string;
  version: number;
}

export interface Asset {
  id: string;
  storage_key: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  width: number | null;
  height: number | null;
  position: number;
  is_primary: boolean;
  status: string;
}

export interface ProductDetail extends Product {
  variants: Variant[];
  assets: Asset[];
}

export function useProductQuery(id: string) {
  return useQuery({
    queryKey: ["products", "detail", id],
    queryFn: () => apiRequest<ProductDetail>(`/products/${id}`),
    enabled: !!id,
  });
}

export function useUpdateProduct(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      apiRequest<ProductDetail>(`/products/${id}`, { method: "PATCH", body: payload }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["products", "detail", id] });
      void queryClient.invalidateQueries({ queryKey: ["products"] });
    },
  });
}

export function assetFileUrl(assetId: string): string {
  return `/api/v1/assets/${assetId}/file`;
}

export function useUploadAsset(productId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const tokens = getTokens();
      const form = new FormData();
      form.append("file", file);
      const resp = await fetch(`/api/v1/products/${productId}/assets`, {
        method: "POST",
        headers: tokens ? { Authorization: `Bearer ${tokens.access_token}` } : {},
        body: form,
      });
      if (!resp.ok) {
        const body = await resp.json().catch(() => null);
        throw new Error(body?.error?.message ?? `上传失败 (${resp.status})`);
      }
      return resp.json() as Promise<Asset>;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["products", "detail", productId] });
    },
  });
}

export function useSetPrimaryAsset(productId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (assetId: string) =>
      apiRequest<Asset>(`/assets/${assetId}/primary`, { method: "POST" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["products", "detail", productId] });
    },
  });
}

export function useDeleteAsset(productId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (assetId: string) => apiRequest<void>(`/assets/${assetId}`, { method: "DELETE" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["products", "detail", productId] });
    },
  });
}

export interface ImportJob {
  id: string;
  filename: string;
  status: string;
  total_rows: number;
  success_rows: number;
  error_rows: number;
  errors: { row: number; field: string; message: string }[];
  created_at: string;
}

export function useImportsQuery() {
  return useQuery({
    queryKey: ["imports"],
    queryFn: () => apiRequest<ImportJob[]>("/imports"),
  });
}

export function useUploadCsvImport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const tokens = getTokens();
      const form = new FormData();
      form.append("file", file);
      const resp = await fetch("/api/v1/imports", {
        method: "POST",
        headers: tokens ? { Authorization: `Bearer ${tokens.access_token}` } : {},
        body: form,
      });
      if (!resp.ok) {
        const body = await resp.json().catch(() => null);
        throw new Error(body?.error?.message ?? `导入失败 (${resp.status})`);
      }
      return resp.json() as Promise<ImportJob>;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["imports"] });
      void queryClient.invalidateQueries({ queryKey: ["products"] });
    },
  });
}
