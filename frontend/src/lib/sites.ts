import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "./api";

export type SitePlatform = "shopify" | "woocommerce" | "wordpress" | "generic";
export type SiteProductStatus =
  | "bound"
  | "pending_review"
  | "approved"
  | "published"
  | "unpublished"
  | "failed";

export interface Site {
  id: string;
  name: string;
  platform: SitePlatform;
  base_url: string;
  status: "active" | "inactive";
  has_credentials: boolean;
  capabilities: Record<string, unknown>;
  last_connection_test_at: string | null;
  last_connection_test_ok: boolean | null;
  version: number;
  created_at: string;
}

export const PLATFORM_LABELS: Record<SitePlatform, string> = {
  shopify: "Shopify",
  woocommerce: "WooCommerce",
  wordpress: "WordPress",
  generic: "通用",
};

export function useSitesQuery() {
  return useQuery({ queryKey: ["sites"], queryFn: () => apiRequest<Site[]>("/sites") });
}

export interface CreateSitePayload {
  name: string;
  platform: SitePlatform;
  base_url: string;
  credentials?: Record<string, string>;
}

export function useCreateSite() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateSitePayload) =>
      apiRequest<Site>("/sites", { method: "POST", body: payload }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["sites"] }),
  });
}

export function useTestConnection() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (siteId: string) =>
      apiRequest<{ ok: boolean; message: string; tested_at: string }>(
        `/sites/${siteId}/test-connection`,
        { method: "POST" }
      ),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["sites"] }),
  });
}

export interface SiteProductOverride {
  title: string | null;
  description: string | null;
  price: string | null;
  category: string | null;
  tags: string[];
  asset_ids: string[];
}

export interface SiteProduct {
  id: string;
  product_id: string;
  site_id: string;
  status: SiteProductStatus;
  version: number;
  created_at: string;
  override: SiteProductOverride;
}

export function useSiteProductsQuery(params: { productId?: string; siteId?: string }) {
  const qs = new URLSearchParams();
  if (params.productId) qs.set("product_id", params.productId);
  if (params.siteId) qs.set("site_id", params.siteId);
  return useQuery({
    queryKey: ["site-products", params],
    queryFn: () => apiRequest<SiteProduct[]>(`/site-products?${qs.toString()}`),
    enabled: !!(params.productId || params.siteId),
  });
}

export function useBindProductToSite(productId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (siteId: string) =>
      apiRequest<SiteProduct>("/site-products", {
        method: "POST",
        body: { product_id: productId, site_id: siteId },
      }),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["site-products", { productId }] }),
  });
}

export function useUnbindSiteProduct(productId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (siteProductId: string) =>
      apiRequest<void>(`/site-products/${siteProductId}`, { method: "DELETE" }),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["site-products", { productId }] }),
  });
}

export interface PublicationPreview {
  site_product_id: string;
  title: string;
  description: string;
  price: string;
  category: string;
  tags: string[];
  asset_ids: string[];
  overridden_fields: string[];
}

export function usePublicationPreview(siteProductId: string | null) {
  return useQuery({
    queryKey: ["publication-preview", siteProductId],
    queryFn: () => apiRequest<PublicationPreview>(`/publication-previews/${siteProductId}`),
    enabled: !!siteProductId,
  });
}

export interface PublicationItem {
  id: string;
  site_product_id: string;
  status: "pending" | "processing" | "success" | "failed";
  attempt_count: number;
  external_id: string | null;
  error_message: string;
}

export interface PublicationJob {
  id: string;
  site_id: string;
  status: "pending" | "processing" | "completed" | "partial" | "failed";
  total_items: number;
  success_items: number;
  failed_items: number;
  created_at: string;
  items: PublicationItem[];
}

export function usePublishSiteProduct(productId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ siteId, siteProductId }: { siteId: string; siteProductId: string }) =>
      apiRequest<PublicationJob>("/publications", {
        method: "POST",
        body: { site_id: siteId, site_product_ids: [siteProductId] },
      }),
    onSuccess: () =>
      void queryClient.invalidateQueries({ queryKey: ["site-products", { productId }] }),
  });
}

export function useUpdateOverride(productId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ siteProductId, patch }: { siteProductId: string; patch: Record<string, unknown> }) =>
      apiRequest<SiteProduct>(`/site-products/${siteProductId}/override`, {
        method: "PATCH",
        body: patch,
      }),
    onSuccess: (_, { siteProductId }) => {
      void queryClient.invalidateQueries({ queryKey: ["site-products", { productId }] });
      void queryClient.invalidateQueries({ queryKey: ["publication-preview", siteProductId] });
    },
  });
}
