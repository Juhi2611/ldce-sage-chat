import { getAdminToken } from "./session";

const API_BASE = import.meta.env.VITE_API_URL || "/api";

export interface SuggestionItem {
  label: string;
  question: string;
  source: "mined" | "default";
}

export interface ChatRequest {
  query: string;
  session_id: string;
  algorithm?: "naive_bayes" | "decision_tree" | "knn";
}

export interface ChatResponse {
  answer_markdown: string;
  intent: string;
  department?: string | null;
  topic?: string | null;
  confidence: number;
  resolved: boolean;
  suggestions: SuggestionItem[];
  enquiry_id?: number | null;
  source_url?: string | null;
  is_smalltalk: boolean;
}

export interface FeedbackRequest {
  enquiry_id: number;
  rating: "up" | "down";
}

export interface CategoryTile {
  id: string;
  title: string;
  icon: string;
  question: string;
}

export interface DepartmentItem {
  id: string;
  name: string;
  canonical_name: string;
  code: string;
  degree: string;
  intake: number;
  overview: string;
  highlights: string[];
  icon?: string;
  starter_question?: string;
}

export interface StatCard {
  title: string;
  value: string;
  change: string;
  trend: "up" | "down" | "neutral";
}

export interface CategoryDistributionItem {
  category: string;
  count: number;
  percentage: number;
}

export interface DepartmentBreakdownItem {
  department: string;
  count: number;
  percentage: number;
}

export interface TrendItem {
  time: string;
  count: number;
}

export interface TimeOfDayItem {
  name: string;
  value: number;
}

export interface TemporalPatternItem {
  period: string;
  count: number;
  topCategory: string;
}

export interface AnalyticsOverviewResponse {
  stats: StatCard[];
  categoryDistribution: CategoryDistributionItem[];
  trafficTrend: TrendItem[];
  temporalPattern: TemporalPatternItem[];
  recentLogCount: number;
}

export interface MinedRuleItem {
  id: number;
  antecedent: string;
  consequent: string;
  support: number;
  confidence: number;
  lift: number;
  status: "Useful" | "Weak";
}

export interface ClusterItem {
  cluster_id: number;
  label: string;
  size_pct: number;
  top_terms: string[];
}

export interface ModelMetricItem {
  model_name: string;
  accuracy: number;
  precision: number;
  recall: number;
  f1_score: number;
  confusion_matrix: number[][];
  holdout_accuracy?: number | null;
  is_active: boolean;
}

export interface EnquiryLogItem {
  id: number;
  session_id: string;
  raw_question: string;
  predicted_category?: string | null;
  predicted_department?: string | null;
  confidence: number;
  resolved: boolean;
  created_at: string;
  is_synthetic: boolean;
  user_rating?: string | null;
}

export interface EnquiriesResponse {
  items: EnquiryLogItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface EnquiriesQueryParams {
  search?: string;
  category?: string;
  department?: string;
  page?: number;
  page_size?: number;
  include_synthetic?: boolean;
}

export interface KDDStatusResponse {
  run_id?: string | null;
  status: "idle" | "pending" | "running" | "done" | "error";
  current_step: number;
  summary?: {
    run_id: string;
    include_synthetic: boolean;
    preprocessing?: {
      rows_before: number;
      duplicates_removed: number;
      nulls_handled: number;
      rows_after: number;
    };
    classification?: Array<{
      model_name: string;
      accuracy: number;
      f1_score: number;
      holdout_accuracy?: number;
    }>;
    best_model?: string;
    n_clusters?: number;
    n_rules_total?: number;
    n_rules_useful?: number;
  } | null;
  error?: string | null;
  include_synthetic?: boolean;
}

export interface RetrainResponse {
  status: string;
  algorithm: string;
  categories_trained: number;
}

class ApiError extends Error {
  status: number;
  data?: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  requireAdmin = false,
): Promise<T> {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  const headers = new Headers(options.headers || {});

  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  if (requireAdmin) {
    const token = getAdminToken();
    if (token) {
      headers.set("X-Admin-Token", token);
    }
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`;
    let errorData: unknown;
    try {
      errorData = await response.json();
      if (errorData && typeof errorData === "object" && "detail" in errorData) {
        errorDetail = String((errorData as { detail: unknown }).detail);
      }
    } catch {
      // Ignore JSON parse errors on non-200 responses
    }

    throw new ApiError(errorDetail, response.status, errorData);
  }

  return response.json();
}

export const api = {
  // Chat & Feedback
  chat: (data: ChatRequest) =>
    request<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  sendFeedback: (data: FeedbackRequest) =>
    request<{ status: string; enquiry_id: number; rating: string }>("/feedback", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getCategories: () => request<CategoryTile[]>("/categories"),

  getDepartments: () => request<DepartmentItem[]>("/departments"),

  // Analytics
  getAnalyticsSummary: (includeSynthetic = true) =>
    request<AnalyticsOverviewResponse>(`/analytics/summary?include_synthetic=${includeSynthetic}`),

  getAnalyticsCategories: (includeSynthetic = true) =>
    request<CategoryDistributionItem[]>(
      `/analytics/categories?include_synthetic=${includeSynthetic}`,
    ),

  getAnalyticsDepartments: (includeSynthetic = true) =>
    request<DepartmentBreakdownItem[]>(
      `/analytics/departments?include_synthetic=${includeSynthetic}`,
    ),

  getAnalyticsTrend: (granularity: "day" | "month" = "month", includeSynthetic = true) =>
    request<TrendItem[]>(
      `/analytics/trend?granularity=${granularity}&include_synthetic=${includeSynthetic}`,
    ),

  getAnalyticsTimeOfDay: (includeSynthetic = true) =>
    request<TimeOfDayItem[]>(`/analytics/time-of-day?include_synthetic=${includeSynthetic}`),

  getAnalyticsRules: () => request<MinedRuleItem[]>("/analytics/rules"),

  getAnalyticsClusters: () => request<ClusterItem[]>("/analytics/clusters"),

  getAnalyticsModelMetrics: () => request<ModelMetricItem[]>("/analytics/model-metrics"),

  getEnquiries: (params: EnquiriesQueryParams = {}) => {
    const q = new URLSearchParams();
    if (params.search) q.set("search", params.search);
    if (params.category) q.set("category", params.category);
    if (params.department) q.set("department", params.department);
    if (params.page) q.set("page", String(params.page));
    if (params.page_size) q.set("page_size", String(params.page_size));
    if (params.include_synthetic !== undefined) {
      q.set("include_synthetic", String(params.include_synthetic));
    }
    return request<EnquiriesResponse>(`/enquiries?${q.toString()}`);
  },

  // Admin
  verifyAdminToken: (token: string) =>
    request<{ valid: boolean }>(
      "/admin/verify-token",
      {
        headers: { "X-Admin-Token": token },
      },
      false,
    ),

  triggerKDD: (includeSynthetic = true) =>
    request<KDDStatusResponse>(
      "/admin/run-kdd",
      {
        method: "POST",
        body: JSON.stringify({ include_synthetic: includeSynthetic }),
      },
      true,
    ),

  getKDDStatus: () => request<KDDStatusResponse>("/admin/run-kdd/status", {}, true),

  retrainClassifier: (algorithm: string) =>
    request<RetrainResponse>(
      "/admin/retrain",
      {
        method: "POST",
        body: JSON.stringify({ algorithm }),
      },
      true,
    ),
};
