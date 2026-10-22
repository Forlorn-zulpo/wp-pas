import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "./api";

// ---------- Suppliers ----------
export type CollectionMethod = "api" | "http_static" | "browser" | "manual";

export interface Supplier {
  id: string;
  name: string;
  website: string;
  status: "active" | "inactive";
  collection_method: CollectionMethod;
  has_credentials: boolean;
  notes: string;
  version: number;
  created_at: string;
}

export const COLLECTION_METHOD_LABELS: Record<CollectionMethod, string> = {
  api: "官方 API",
  http_static: "静态页面解析",
  browser: "浏览器自动化",
  manual: "手动录入",
};

export function useSuppliersQuery() {
  return useQuery({ queryKey: ["suppliers"], queryFn: () => apiRequest<Supplier[]>("/suppliers") });
}

export function useCreateSupplier() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { name: string; website?: string; collection_method?: CollectionMethod; notes?: string }) =>
      apiRequest<Supplier>("/suppliers", { method: "POST", body: payload }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["suppliers"] }),
  });
}

// ---------- AI config ----------
export type AIProviderType = "anthropic" | "openai" | "gemini" | "deepseek" | "openai_compatible";
export type AITaskType =
  | "product_recognition"
  | "title_generation"
  | "description_generation"
  | "attribute_extraction"
  | "category_suggestion"
  | "image_analysis"
  | "image_generation"
  | "translation";

export const PROVIDER_TYPE_LABELS: Record<AIProviderType, string> = {
  anthropic: "Anthropic",
  openai: "OpenAI",
  gemini: "Gemini",
  deepseek: "DeepSeek",
  openai_compatible: "OpenAI 兼容(本地/其它)",
};

export const TASK_TYPE_LABELS: Record<AITaskType, string> = {
  product_recognition: "商品识别",
  title_generation: "标题生成",
  description_generation: "描述生成",
  attribute_extraction: "属性提取",
  category_suggestion: "分类建议",
  image_analysis: "图片分析",
  image_generation: "图片生成",
  translation: "翻译",
};

export interface AIProvider {
  id: string;
  name: string;
  provider_type: AIProviderType;
  base_url: string;
  has_api_key: boolean;
  is_active: boolean;
  version: number;
}

export interface AIModel {
  id: string;
  provider_id: string;
  model_id: string;
  display_name: string;
  supports_vision: boolean;
  supports_image_generation: boolean;
  is_active: boolean;
}

export interface AITaskPolicy {
  id: string;
  task_type: AITaskType;
  model_id: string;
  max_tokens: number;
  is_active: boolean;
  version: number;
}

export interface AIUsageSummary {
  task_type: AITaskType;
  call_count: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost: string;
}

export function useAIProvidersQuery() {
  return useQuery({ queryKey: ["ai-providers"], queryFn: () => apiRequest<AIProvider[]>("/ai/providers") });
}
export function useAIModelsQuery() {
  return useQuery({ queryKey: ["ai-models"], queryFn: () => apiRequest<AIModel[]>("/ai/models") });
}
export function useAITaskPoliciesQuery() {
  return useQuery({ queryKey: ["ai-policies"], queryFn: () => apiRequest<AITaskPolicy[]>("/ai/task-policies") });
}
export function useAIUsageSummaryQuery() {
  return useQuery({ queryKey: ["ai-usage"], queryFn: () => apiRequest<AIUsageSummary[]>("/ai/usage/summary") });
}

export function useCreateAIProvider() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { name: string; provider_type: AIProviderType; base_url?: string; api_key?: string }) =>
      apiRequest<AIProvider>("/ai/providers", { method: "POST", body: payload }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["ai-providers"] }),
  });
}

export function useCreateAIModel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      provider_id: string;
      model_id: string;
      display_name?: string;
      supports_vision?: boolean;
      supports_image_generation?: boolean;
    }) => apiRequest<AIModel>("/ai/models", { method: "POST", body: payload }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["ai-models"] }),
  });
}

export function useCreateAITaskPolicy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { task_type: AITaskType; model_id: string; max_tokens?: number }) =>
      apiRequest<AITaskPolicy>("/ai/task-policies", { method: "POST", body: payload }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["ai-policies"] }),
  });
}

export function useGenerateTitle() {
  return useMutation({
    mutationFn: (productId: string) =>
      apiRequest<{ suggested_title: string }>(`/products/${productId}/ai/generate-title`, {
        method: "POST",
      }),
  });
}

// ---------- Reviews ----------
export interface ReviewItem {
  id: string;
  site_product_id: string;
  status: "pending" | "approved" | "rejected";
  notes: string;
  created_at: string;
}

export function useReviewsQuery(status?: string) {
  const qs = status ? `?status=${status}` : "";
  return useQuery({
    queryKey: ["reviews", status],
    queryFn: () => apiRequest<ReviewItem[]>(`/reviews${qs}`),
  });
}

export function useRequestReview() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (siteProductId: string) =>
      apiRequest<ReviewItem>("/reviews", { method: "POST", body: { site_product_id: siteProductId } }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["reviews"] }),
  });
}

export function useDecideReview() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, decision, notes }: { id: string; decision: "approve" | "reject"; notes?: string }) =>
      apiRequest<ReviewItem>(`/reviews/${id}/${decision}`, { method: "POST", body: { notes: notes ?? "" } }),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["reviews"] }),
  });
}
