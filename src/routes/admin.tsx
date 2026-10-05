import { createFileRoute } from "@tanstack/react-router";
import {
  Activity,
  AlertCircle,
  ArrowDownRight,
  ArrowUpRight,
  BrainCircuit,
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Database,
  GitBranch,
  KeyRound,
  Layers3,
  Loader2,
  Lock,
  LogOut,
  Play,
  RefreshCw,
  Search,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
} from "lucide-react";
import { useState, useMemo, useEffect } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  api,
  type AnalyticsOverviewResponse,
  type CategoryDistributionItem,
  type DepartmentBreakdownItem,
  type TrendItem,
  type TimeOfDayItem,
  type MinedRuleItem,
  type ClusterItem,
  type ModelMetricItem,
  type EnquiriesResponse,
  type KDDStatusResponse,
} from "@/lib/api";
import { getAdminToken, setAdminToken, clearAdminToken } from "@/lib/session";

const COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
  "var(--muted-foreground)",
  "#f59e0b",
  "#10b981",
];

export const Route = createFileRoute("/admin")({
  head: () => ({
    meta: [
      { title: "KDD Analytics — LDCE Smart Enquiry" },
      {
        name: "description",
        content: "Explore enquiry patterns, clusters, association rules and model performance.",
      },
      { property: "og:title", content: "LDCE Enquiry Analytics" },
      { property: "og:description", content: "KDD insights across LDCE student enquiries." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: AdminPage,
});

function AdminPage() {
  const [token, setTokenState] = useState<string | null>(() => getAdminToken());

  const handleLogin = (newToken: string) => {
    setAdminToken(newToken);
    setTokenState(newToken);
  };

  const handleLogout = () => {
    clearAdminToken();
    setTokenState(null);
  };

  if (!token) {
    return <AdminLogin onLogin={handleLogin} />;
  }

  return <AdminDashboard onLogout={handleLogout} />;
}

function AdminLogin({ onLogin }: { onLogin: (token: string) => void }) {
  const [inputToken, setInputToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const clean = inputToken.trim();
    if (!clean) return;

    setLoading(true);
    setError(null);
    try {
      const res = await api.verifyAdminToken(clean);
      if (res.valid) {
        onLogin(clean);
      } else {
        setError("Invalid admin token. Please try again.");
      }
    } catch {
      setError("Invalid admin token. Access denied.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-[75vh] items-center justify-center px-4 py-12">
      <div className="w-full max-w-md rounded-2xl border border-border bg-card p-8 shadow-xl">
        <div className="flex size-12 items-center justify-center rounded-2xl bg-accent text-primary">
          <Lock className="size-6" />
        </div>
        <h1 className="mt-4 font-display text-2xl font-bold">Admin Authentication</h1>
        <p className="mt-1 text-xs text-muted-foreground">
          Enter your LDCE Administrator security token to access the KDD discovery dashboard.
        </p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase text-muted-foreground">
              Admin Security Token
            </label>
            <div className="mt-1 flex items-center gap-2 rounded-xl border border-border bg-background px-3 py-2.5 focus-within:ring-2 focus-within:ring-primary/40">
              <KeyRound className="size-4 text-muted-foreground" />
              <input
                type="password"
                value={inputToken}
                onChange={(e) => setInputToken(e.target.value)}
                placeholder="Enter admin token…"
                autoFocus
                className="w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
              />
            </div>
          </div>

          {error && (
            <div className="flex items-center gap-2 rounded-lg bg-destructive/10 p-2.5 text-xs text-destructive">
              <AlertCircle className="size-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <Button type="submit" disabled={loading || !inputToken.trim()} className="w-full">
            {loading ? (
              <>
                <Loader2 className="mr-2 size-4 animate-spin" /> Verifying…
              </>
            ) : (
              "Access Admin Dashboard"
            )}
          </Button>
        </form>
      </div>
    </div>
  );
}

function KPI({
  label,
  value,
  trend,
  up = true,
}: {
  label: string;
  value: string | number;
  trend: string;
  up?: boolean;
}) {
  return (
    <div className="rounded-2xl border border-border bg-card p-5 shadow-soft">
      <div className="flex justify-between">
        <span className="text-sm text-muted-foreground">{label}</span>
        <Activity className="size-4 text-primary" />
      </div>
      <div className="mt-3 flex items-end justify-between">
        <strong className="font-display text-3xl">{value}</strong>
        <span className={`flex items-center text-xs font-bold ${up ? "text-online" : "text-warm"}`}>
          {up ? <ArrowUpRight className="size-3" /> : <ArrowDownRight className="size-3" />}
          {trend}
        </span>
      </div>
    </div>
  );
}

function ChartCard({
  title,
  children,
  headerRight,
}: {
  title: string;
  children: React.ReactNode;
  headerRight?: React.ReactNode;
}) {
  return (
    <article className="rounded-2xl border border-border bg-card p-5 shadow-soft">
      <div className="flex items-center justify-between">
        <h2 className="font-display text-lg font-bold">{title}</h2>
        {headerRight}
      </div>
      <div className="mt-5 h-64">{children}</div>
    </article>
  );
}

const KDD_STEPS = [
  "Selection",
  "Preprocessing",
  "Transformation",
  "Mining",
  "Evaluation",
  "Presentation",
];

function AdminDashboard({ onLogout }: { onLogout: () => void }) {
  const queryClient = useQueryClient();
  const [includeSynthetic, setIncludeSynthetic] = useState(true);
  const [trendGranularity, setTrendGranularity] = useState<"month" | "day">("month");
  const [selectedAlgo, setSelectedAlgo] = useState<"naive_bayes" | "decision_tree" | "knn">(
    "naive_bayes",
  );
  const [retrainAlgo, setRetrainAlgo] = useState<"naive_bayes" | "decision_tree" | "knn">(
    "naive_bayes",
  );
  const [ruleSortKey, setRuleSortKey] = useState<"lift" | "confidence" | "support">("lift");

  // Log filter state
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [deptFilter, setDeptFilter] = useState("");
  const [logPage, setLogPage] = useState(1);

  // KDD Polling & Execution State
  const [isKDDRunning, setIsKDDRunning] = useState(false);
  const [lastAnalysedTime, setLastAnalysedTime] = useState<string | null>(null);

  // --- Queries ---
  const { data: summaryData, isLoading: loadingSummary } = useQuery<AnalyticsOverviewResponse>({
    queryKey: ["analytics-summary", includeSynthetic],
    queryFn: () => api.getAnalyticsSummary(includeSynthetic),
  });

  const { data: categoriesData } = useQuery<CategoryDistributionItem[]>({
    queryKey: ["analytics-categories", includeSynthetic],
    queryFn: () => api.getAnalyticsCategories(includeSynthetic),
  });

  const { data: departmentsData } = useQuery<DepartmentBreakdownItem[]>({
    queryKey: ["analytics-departments", includeSynthetic],
    queryFn: () => api.getAnalyticsDepartments(includeSynthetic),
  });

  const { data: trendData } = useQuery<TrendItem[]>({
    queryKey: ["analytics-trend", trendGranularity, includeSynthetic],
    queryFn: () => api.getAnalyticsTrend(trendGranularity, includeSynthetic),
  });

  const { data: timeOfDayData } = useQuery<TimeOfDayItem[]>({
    queryKey: ["analytics-time-of-day", includeSynthetic],
    queryFn: () => api.getAnalyticsTimeOfDay(includeSynthetic),
  });

  const { data: rulesData } = useQuery<MinedRuleItem[]>({
    queryKey: ["analytics-rules"],
    queryFn: () => api.getAnalyticsRules(),
  });

  const { data: clustersData } = useQuery<ClusterItem[]>({
    queryKey: ["analytics-clusters"],
    queryFn: () => api.getAnalyticsClusters(),
  });

  const { data: modelMetricsData, refetch: refetchMetrics } = useQuery<ModelMetricItem[]>({
    queryKey: ["analytics-model-metrics"],
    queryFn: () => api.getAnalyticsModelMetrics(),
  });

  const { data: enquiriesData, isLoading: loadingEnquiries } = useQuery<EnquiriesResponse>({
    queryKey: ["enquiries", searchQuery, categoryFilter, deptFilter, logPage, includeSynthetic],
    queryFn: () =>
      api.getEnquiries({
        search: searchQuery || undefined,
        category: categoryFilter || undefined,
        department: deptFilter || undefined,
        page: logPage,
        page_size: 10,
        include_synthetic: includeSynthetic,
      }),
  });

  // Poll KDD Status
  const { data: kddStatus, refetch: refetchKDDStatus } = useQuery<KDDStatusResponse>({
    queryKey: ["kdd-status"],
    queryFn: () => api.getKDDStatus(),
    refetchInterval: isKDDRunning ? 1500 : false,
  });

  useEffect(() => {
    if (kddStatus?.status === "running" || kddStatus?.status === "pending") {
      setIsKDDRunning(true);
    } else if (kddStatus?.status === "done") {
      if (isKDDRunning) {
        setIsKDDRunning(false);
        setLastAnalysedTime(
          new Intl.DateTimeFormat("en-IN", {
            hour: "numeric",
            minute: "2-digit",
            second: "2-digit",
          }).format(new Date()),
        );
        // Refetch all analytics data
        queryClient.invalidateQueries({ queryKey: ["analytics-summary"] });
        queryClient.invalidateQueries({ queryKey: ["analytics-categories"] });
        queryClient.invalidateQueries({ queryKey: ["analytics-departments"] });
        queryClient.invalidateQueries({ queryKey: ["analytics-trend"] });
        queryClient.invalidateQueries({ queryKey: ["analytics-time-of-day"] });
        queryClient.invalidateQueries({ queryKey: ["analytics-rules"] });
        queryClient.invalidateQueries({ queryKey: ["analytics-clusters"] });
        queryClient.invalidateQueries({ queryKey: ["analytics-model-metrics"] });
        queryClient.invalidateQueries({ queryKey: ["enquiries"] });
      }
    } else if (kddStatus?.status === "error") {
      setIsKDDRunning(false);
    }
  }, [kddStatus, isKDDRunning, queryClient]);

  // Trigger KDD Mutation
  const triggerKDDMutation = useMutation({
    mutationFn: () => api.triggerKDD(includeSynthetic),
    onSuccess: () => {
      setIsKDDRunning(true);
      refetchKDDStatus();
    },
  });

  // Retrain Mutation
  const retrainMutation = useMutation({
    mutationFn: (algo: string) => api.retrainClassifier(algo),
    onSuccess: () => {
      refetchMetrics();
    },
  });

  // Active Model Metric Item
  const activeMetric = useMemo(() => {
    if (!modelMetricsData || modelMetricsData.length === 0) return null;
    return (
      modelMetricsData.find((m) => m.model_name.toLowerCase() === selectedAlgo.toLowerCase()) ||
      modelMetricsData[0]
    );
  }, [modelMetricsData, selectedAlgo]);

  // Sorted Rules
  const sortedRules = useMemo(() => {
    if (!rulesData) return [];
    return [...rulesData].sort((a, b) => b[ruleSortKey] - a[ruleSortKey]);
  }, [rulesData, ruleSortKey]);

  const currentStep = kddStatus?.current_step || 0;

  return (
    <div className="mx-auto max-w-[1500px] px-4 py-10 lg:px-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="section-label text-warm">Knowledge Discovery in Databases</p>
          <h1 className="mt-2 font-display text-4xl font-bold">
            Enquiry <span className="text-primary">Intelligence</span>
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Live analytics derived through data cleaning, feature transformation, K-Means
            clustering, Apriori mining, and model benchmarking.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Include Synthetic Toggle */}
          <label className="flex items-center gap-2 rounded-xl border border-border bg-card px-3 py-2 text-xs font-semibold cursor-pointer select-none">
            <input
              type="checkbox"
              checked={includeSynthetic}
              onChange={(e) => setIncludeSynthetic(e.target.checked)}
              className="accent-primary"
            />
            <span>Include demo data</span>
          </label>

          {includeSynthetic ? (
            <span className="rounded-full bg-warm-soft px-3 py-1.5 text-xs font-bold text-warm-foreground">
              Demo data included
            </span>
          ) : (
            <span className="rounded-full bg-online-soft px-3 py-1.5 text-xs font-bold text-online">
              Live inquiries only
            </span>
          )}

          {lastAnalysedTime && (
            <span className="rounded-full bg-muted px-3 py-1.5 text-xs font-medium text-muted-foreground">
              Analysed at {lastAnalysedTime}
            </span>
          )}

          <Button variant="outline" size="sm" onClick={onLogout} className="gap-1.5 text-xs">
            <LogOut className="size-3.5" /> Logout
          </Button>
        </div>
      </div>

      {/* 6-Stage KDD Progress Stepper */}
      <div className="overflow-x-auto rounded-2xl border border-border bg-card p-5 shadow-soft">
        <div className="mb-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <span className="font-display text-sm font-bold text-foreground">
              6-Stage KDD Execution Pipeline
            </span>
            <p className="text-xs text-muted-foreground">
              {isKDDRunning
                ? `Running Step ${currentStep} of 6…`
                : kddStatus?.status === "done"
                  ? "Latest analysis completed successfully"
                  : "Click button to run end-to-end KDD pipeline"}
            </p>
          </div>

          <Button
            size="sm"
            onClick={() => triggerKDDMutation.mutate()}
            disabled={isKDDRunning || triggerKDDMutation.isPending}
            className="gap-2"
          >
            {isKDDRunning || triggerKDDMutation.isPending ? (
              <>
                <Loader2 className="size-4 animate-spin" /> Processing…
              </>
            ) : (
              <>
                <Play className="size-4" /> Run KDD Analysis
              </>
            )}
          </Button>
        </div>

        <div className="flex min-w-[760px] items-center justify-between pt-2">
          {KDD_STEPS.map((stepName, i) => {
            const stepNum = i + 1;
            const isCompleted =
              currentStep > stepNum || (kddStatus?.status === "done" && !isKDDRunning);
            const isCurrent = currentStep === stepNum && isKDDRunning;

            return (
              <div key={stepName} className="flex flex-1 items-center">
                <div className="flex items-center gap-2">
                  <span
                    className={`flex size-8 items-center justify-center rounded-full text-xs font-bold transition-all ${
                      isCurrent
                        ? "bg-warm text-warm-foreground ring-4 ring-warm/20 animate-pulse"
                        : isCompleted
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted text-muted-foreground"
                    }`}
                  >
                    {isCompleted ? <Check className="size-4" /> : stepNum}
                  </span>
                  <div>
                    <span className="block text-xs font-semibold">{stepName}</span>
                    {isCurrent && <span className="text-[10px] text-warm font-bold">Active</span>}
                  </div>
                </div>
                {i < KDD_STEPS.length - 1 && (
                  <div
                    className={`mx-3 h-0.5 flex-1 transition-colors ${
                      isCompleted ? "bg-primary" : "bg-border"
                    }`}
                  />
                )}
              </div>
            );
          })}
        </div>

        {kddStatus?.error && (
          <div className="mt-4 flex items-center gap-2 rounded-xl bg-destructive/10 p-3 text-xs text-destructive">
            <AlertCircle className="size-4 shrink-0" />
            <span>KDD execution error: {kddStatus.error}</span>
          </div>
        )}
      </div>

      {/* KPI Cards */}
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {loadingSummary ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="h-28 rounded-2xl border border-border bg-card p-5 animate-pulse"
            />
          ))
        ) : summaryData?.stats ? (
          summaryData.stats.map((card) => (
            <KPI
              key={card.title}
              label={card.title}
              value={card.value}
              trend={card.change}
              up={card.trend === "up"}
            />
          ))
        ) : (
          <>
            <KPI label="Total Enquiries" value="0" trend="No data" />
            <KPI label="Resolution Rate" value="0%" trend="No data" />
            <KPI label="Top Topic Area" value="N/A" trend="No data" />
            <KPI label="Enquiries Today" value="0" trend="No data" />
          </>
        )}
      </section>

      {/* Analytics Charts Grid */}
      <section className="grid gap-5 xl:grid-cols-2">
        {/* Category Donut */}
        <ChartCard title="Enquiries by category">
          {categoriesData && categoriesData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={categoriesData}
                  innerRadius={65}
                  outerRadius={95}
                  paddingAngle={3}
                  dataKey="count"
                  nameKey="category"
                >
                  {categoriesData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(val: unknown, name: unknown) => {
                    const item = categoriesData.find((c) => c.category === name);
                    return [`${val} (${item?.percentage || 0}%)`, String(name)];
                  }}
                />
                <text
                  x="50%"
                  y="48%"
                  textAnchor="middle"
                  className="fill-foreground text-xl font-bold"
                >
                  {summaryData?.stats?.[0]?.value || "0"}
                </text>
                <text x="50%" y="57%" textAnchor="middle" className="fill-muted-foreground text-xs">
                  enquiries
                </text>
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
              No category data yet. Run KDD analysis.
            </div>
          )}
        </ChartCard>

        {/* Departments Bar Chart */}
        <ChartCard title="Most enquired departments">
          {departmentsData && departmentsData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={departmentsData.slice(0, 7)}
                layout="vertical"
                margin={{ left: 25, right: 20 }}
              >
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" hide />
                <YAxis type="category" dataKey="department" width={110} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(val: unknown) => [`${val} enquiries`, "Count"]} />
                <Bar dataKey="count" fill="var(--chart-1)" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
              No department data yet.
            </div>
          )}
        </ChartCard>

        {/* Enquiry Trend Chart */}
        <ChartCard
          title="Enquiry traffic trend"
          headerRight={
            <div className="flex gap-1 rounded-lg border border-border bg-background p-1 text-xs">
              <button
                onClick={() => setTrendGranularity("day")}
                className={`rounded px-2 py-1 font-semibold ${
                  trendGranularity === "day"
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground"
                }`}
              >
                Day
              </button>
              <button
                onClick={() => setTrendGranularity("month")}
                className={`rounded px-2 py-1 font-semibold ${
                  trendGranularity === "month"
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground"
                }`}
              >
                Month
              </button>
            </div>
          }
        >
          {trendData && trendData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trendData}>
                <defs>
                  <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--chart-1)" stopOpacity={0.45} />
                    <stop offset="100%" stopColor="var(--chart-1)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="time" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(val: unknown) => [`${val} enquiries`, "Count"]} />
                <Area
                  dataKey="count"
                  stroke="var(--chart-1)"
                  fill="url(#areaGrad)"
                  strokeWidth={2.5}
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
              No trend data available.
            </div>
          )}
        </ChartCard>

        {/* Time of Day Distribution */}
        <ChartCard title="Enquiries by time of day">
          {timeOfDayData && timeOfDayData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={timeOfDayData} margin={{ bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis
                  dataKey="name"
                  tick={{ fontSize: 9 }}
                  interval={0}
                  angle={-15}
                  textAnchor="end"
                />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(val: unknown) => [`${val} enquiries`, "Volume"]} />
                <Bar dataKey="value" fill="var(--chart-4)" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
              No time-of-day data available.
            </div>
          )}
        </ChartCard>
      </section>

      {/* Frequently Associated Enquiries (Apriori) */}
      <section className="rounded-2xl border border-border bg-card p-5 shadow-soft">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center gap-2">
            <GitBranch className="size-5 text-warm" />
            <h2 className="font-display text-xl font-bold">
              Frequently Associated Enquiries (Apriori)
            </h2>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span className="text-muted-foreground">Sort by:</span>
            {(["lift", "confidence", "support"] as const).map((key) => (
              <button
                key={key}
                onClick={() => setRuleSortKey(key)}
                className={`rounded-lg px-2.5 py-1 capitalize font-medium ${
                  ruleSortKey === key
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground"
                }`}
              >
                {key}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-5 overflow-x-auto">
          {sortedRules.length > 0 ? (
            <table className="w-full min-w-[650px] text-left text-sm">
              <thead className="border-b border-border text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="px-3 py-3">Rule (Antecedent → Consequent)</th>
                  <th className="px-3 py-3">Support</th>
                  <th className="px-3 py-3">Confidence</th>
                  <th className="px-3 py-3">Lift</th>
                  <th className="px-3 py-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {sortedRules.map((r) => (
                  <tr
                    key={r.id}
                    className="border-b border-border/70 last:border-0 hover:bg-muted/30"
                  >
                    <td className="px-3 py-3 font-semibold">
                      {r.antecedent} <span className="text-primary font-bold">→</span>{" "}
                      {r.consequent}
                    </td>
                    <td className="px-3 py-3 font-mono text-xs">{(r.support * 100).toFixed(1)}%</td>
                    <td className="px-3 py-3 font-mono text-xs">
                      {(r.confidence * 100).toFixed(1)}%
                    </td>
                    <td className="px-3 py-3">
                      <span className="rounded-full bg-accent px-2.5 py-1 font-bold text-primary font-mono text-xs">
                        {r.lift.toFixed(2)}×
                      </span>
                    </td>
                    <td className="px-3 py-3">
                      <span
                        className={`rounded-full px-2.5 py-1 text-xs font-bold ${
                          r.status === "Useful"
                            ? "bg-online-soft text-online"
                            : "bg-muted text-muted-foreground"
                        }`}
                      >
                        {r.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="py-12 text-center text-xs text-muted-foreground">
              No association rules mined yet. Run KDD analysis to discover enquiry co-occurrences.
            </div>
          )}
        </div>
      </section>

      {/* Discovered Enquiry Clusters (K-Means) */}
      <section>
        <div className="mb-4 flex items-center gap-2">
          <Layers3 className="size-5 text-warm" />
          <h2 className="font-display text-xl font-bold">Discovered Enquiry Clusters (K-Means)</h2>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {clustersData && clustersData.length > 0 ? (
            clustersData.map((cluster) => (
              <article
                key={cluster.cluster_id}
                className="rounded-2xl border border-border bg-card p-5 shadow-soft flex flex-col justify-between"
              >
                <div>
                  <div className="flex justify-between items-center">
                    <span className="font-display text-xs text-warm font-bold">
                      Cluster {cluster.cluster_id + 1}
                    </span>
                    <b className="text-2xl text-primary font-display">{cluster.size_pct}%</b>
                  </div>
                  <h3 className="mt-2 font-display text-lg font-bold">{cluster.label}</h3>
                  <div className="mt-4 flex flex-wrap gap-1.5">
                    {cluster.top_terms.map((term) => (
                      <span
                        key={term}
                        className="rounded-full bg-accent px-2.5 py-1 text-xs text-primary font-medium"
                      >
                        {term}
                      </span>
                    ))}
                  </div>
                </div>
              </article>
            ))
          ) : (
            <div className="col-span-full rounded-2xl border border-border bg-card p-8 text-center text-xs text-muted-foreground">
              No clusters discovered yet. Run KDD analysis to cluster enquiries by TF-IDF
              similarity.
            </div>
          )}
        </div>
      </section>

      {/* Classifier Model Performance & Retraining */}
      <section className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
        <article className="rounded-2xl border border-border bg-card p-5 shadow-soft">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <BrainCircuit className="size-5 text-warm" />
              <h2 className="font-display text-xl font-bold">Classification Models</h2>
            </div>
            {activeMetric?.is_active && (
              <span className="rounded-full bg-online-soft px-2.5 py-1 text-[10px] font-bold uppercase text-online">
                Active in Chat
              </span>
            )}
          </div>

          <div className="mt-4 flex gap-1 rounded-lg bg-muted p-1">
            {(["naive_bayes", "decision_tree", "knn"] as const).map((algo) => {
              const label =
                algo === "naive_bayes"
                  ? "Naive Bayes"
                  : algo === "decision_tree"
                    ? "Decision Tree"
                    : "KNN";
              return (
                <button
                  key={algo}
                  onClick={() => setSelectedAlgo(algo)}
                  className={`flex-1 rounded-md px-2 py-2 text-xs font-bold transition-all ${
                    selectedAlgo === algo
                      ? "bg-card text-primary shadow-sm"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {label}
                </button>
              );
            })}
          </div>

          {activeMetric ? (
            <div className="mt-6 space-y-5">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
                <div className="rounded-xl border border-border bg-surface p-3">
                  <span className="text-[11px] text-muted-foreground uppercase font-bold">
                    Accuracy
                  </span>
                  <div className="font-display text-2xl font-bold text-primary">
                    {(activeMetric.accuracy * 100).toFixed(1)}%
                  </div>
                </div>
                <div className="rounded-xl border border-border bg-surface p-3">
                  <span className="text-[11px] text-muted-foreground uppercase font-bold">
                    F1-Score
                  </span>
                  <div className="font-display text-2xl font-bold text-primary">
                    {(activeMetric.f1_score * 100).toFixed(1)}%
                  </div>
                </div>
                <div className="rounded-xl border border-border bg-surface p-3">
                  <span className="text-[11px] text-muted-foreground uppercase font-bold">
                    Precision
                  </span>
                  <div className="font-display text-2xl font-bold text-primary">
                    {(activeMetric.precision * 100).toFixed(1)}%
                  </div>
                </div>
                <div className="rounded-xl border border-border bg-surface p-3">
                  <span className="text-[11px] text-muted-foreground uppercase font-bold">
                    Recall
                  </span>
                  <div className="font-display text-2xl font-bold text-primary">
                    {(activeMetric.recall * 100).toFixed(1)}%
                  </div>
                </div>
              </div>

              {/* Holdout Accuracy & Note */}
              <div className="rounded-xl border border-border/80 bg-accent/40 p-4">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                  <div>
                    <span className="text-xs font-bold text-primary uppercase">
                      Hand-written Holdout Accuracy
                    </span>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Evaluated on 50 realistic, out-of-distribution questions from prospective
                      students.
                    </p>
                  </div>
                  <div className="font-display text-2xl font-bold text-primary">
                    {activeMetric.holdout_accuracy != null
                      ? `${(activeMetric.holdout_accuracy * 100).toFixed(1)}%`
                      : "N/A"}
                  </div>
                </div>
                <p className="mt-2 text-[11px] text-muted-foreground border-t border-border/50 pt-2">
                  ℹ️ <i>Why accuracy differs:</i> Test-set accuracy is measured on stratified 20%
                  validation split from training templates; holdout accuracy tests real human
                  variations, slang, typos, and phrasing.
                </p>
              </div>

              {/* Confusion Matrix */}
              {activeMetric.confusion_matrix && activeMetric.confusion_matrix.length > 0 && (
                <div>
                  <span className="text-xs font-bold text-muted-foreground uppercase">
                    Confusion Matrix Heatmap ({activeMetric.confusion_matrix.length} ×{" "}
                    {activeMetric.confusion_matrix.length} categories)
                  </span>
                  <div
                    className="mt-2 grid gap-1 max-h-48 overflow-auto rounded-lg border border-border p-2 bg-surface"
                    style={{
                      gridTemplateColumns: `repeat(${activeMetric.confusion_matrix.length}, minmax(28px, 1fr))`,
                    }}
                  >
                    {activeMetric.confusion_matrix.flatMap((row, rIdx) =>
                      row.map((val, cIdx) => (
                        <div
                          key={`${rIdx}-${cIdx}`}
                          title={`Row ${rIdx + 1} (Actual) × Col ${cIdx + 1} (Pred): ${val}`}
                          className={`flex aspect-square items-center justify-center rounded text-[10px] font-bold ${
                            rIdx === cIdx
                              ? "bg-primary text-primary-foreground"
                              : val > 0
                                ? "bg-warm-soft text-warm-foreground"
                                : "bg-muted/40 text-muted-foreground"
                          }`}
                        >
                          {val}
                        </div>
                      )),
                    )}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="py-12 text-center text-xs text-muted-foreground">
              No model metrics saved yet. Run KDD analysis to evaluate all classifiers.
            </div>
          )}
        </article>

        {/* Retrain Classifier Control */}
        <article className="rounded-2xl border border-border bg-card p-5 shadow-soft flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2">
              <RefreshCw className="size-5 text-warm" />
              <h2 className="font-display text-xl font-bold">Retrain Model</h2>
            </div>
            <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
              Retrain intent classification model on Knowledge Base examples + template patterns +
              external university intents. Retraining persists the updated pipeline to disk and sets
              it active immediately.
            </p>

            <div className="mt-5 space-y-3">
              <label className="block text-xs font-semibold uppercase text-muted-foreground">
                Target Algorithm
              </label>
              <div className="grid grid-cols-3 gap-2">
                {(["naive_bayes", "decision_tree", "knn"] as const).map((algo) => (
                  <button
                    key={algo}
                    onClick={() => setRetrainAlgo(algo)}
                    className={`rounded-xl border p-3 text-xs font-bold text-center transition-all ${
                      retrainAlgo === algo
                        ? "border-primary bg-accent text-primary"
                        : "border-border bg-background text-muted-foreground hover:border-primary/40"
                    }`}
                  >
                    {algo === "naive_bayes"
                      ? "Naive Bayes"
                      : algo === "decision_tree"
                        ? "Decision Tree"
                        : "KNN"}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-border">
            <Button
              className="w-full gap-2"
              onClick={() => retrainMutation.mutate(retrainAlgo)}
              disabled={retrainMutation.isPending}
            >
              {retrainMutation.isPending ? (
                <>
                  <Loader2 className="size-4 animate-spin" /> Training Model…
                </>
              ) : (
                <>
                  <Sparkles className="size-4" /> Retrain & Activate Model
                </>
              )}
            </Button>
            {retrainMutation.isSuccess && (
              <p className="mt-2 text-center text-xs font-semibold text-online">
                ✅ Successfully trained and activated {retrainAlgo}!
              </p>
            )}
          </div>
        </article>
      </section>

      {/* Recent Enquiry Log Table (Server-side Search & Pagination) */}
      <section className="rounded-2xl border border-border bg-card p-5 shadow-soft">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center gap-2">
            <Database className="size-5 text-warm" />
            <h2 className="font-display text-xl font-bold">Enquiry Log Repository</h2>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Search */}
            <label className="flex items-center gap-2 rounded-xl border border-border bg-background px-3 py-1.5 text-xs">
              <Search className="size-3.5 text-muted-foreground shrink-0" />
              <input
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setLogPage(1);
                }}
                placeholder="Search queries or sessions…"
                className="w-40 sm:w-56 bg-transparent outline-none placeholder:text-muted-foreground"
              />
            </label>

            {/* Category Filter */}
            <select
              value={categoryFilter}
              onChange={(e) => {
                setCategoryFilter(e.target.value);
                setLogPage(1);
              }}
              className="rounded-xl border border-border bg-background px-2.5 py-1.5 text-xs outline-none"
            >
              <option value="">All Categories</option>
              {categoriesData?.map((c) => (
                <option key={c.category} value={c.category}>
                  {c.category}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="mt-4 overflow-x-auto">
          {loadingEnquiries ? (
            <div className="py-12 text-center text-xs text-muted-foreground">
              <Loader2 className="size-5 animate-spin mx-auto mb-2 text-primary" />
              Loading enquiry logs…
            </div>
          ) : enquiriesData && enquiriesData.items.length > 0 ? (
            <table className="w-full min-w-[760px] text-left text-xs">
              <thead className="border-b border-border text-muted-foreground uppercase text-[10px]">
                <tr>
                  <th className="px-3 py-2.5">ID</th>
                  <th className="px-3 py-2.5">Question</th>
                  <th className="px-3 py-2.5">Category</th>
                  <th className="px-3 py-2.5">Department</th>
                  <th className="px-3 py-2.5">Confidence</th>
                  <th className="px-3 py-2.5">Rating</th>
                  <th className="px-3 py-2.5">Source</th>
                  <th className="px-3 py-2.5">Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {enquiriesData.items.map((enq) => (
                  <tr
                    key={enq.id}
                    className="border-b border-border/70 last:border-0 hover:bg-muted/30"
                  >
                    <td className="px-3 py-2.5 font-mono text-muted-foreground">#{enq.id}</td>
                    <td className="px-3 py-2.5 font-medium max-w-xs truncate">
                      {enq.raw_question}
                    </td>
                    <td className="px-3 py-2.5">
                      <span className="rounded bg-accent px-2 py-0.5 font-semibold text-primary">
                        {enq.predicted_category || "N/A"}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-muted-foreground">
                      {enq.predicted_department || "General"}
                    </td>
                    <td className="px-3 py-2.5 font-mono">{(enq.confidence * 100).toFixed(0)}%</td>
                    <td className="px-3 py-2.5">
                      {enq.user_rating === "up" ? (
                        <span className="inline-flex items-center gap-1 text-online font-bold">
                          <ThumbsUp className="size-3" /> Helpful
                        </span>
                      ) : enq.user_rating === "down" ? (
                        <span className="inline-flex items-center gap-1 text-destructive font-bold">
                          <ThumbsDown className="size-3" /> Unhelpful
                        </span>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </td>
                    <td className="px-3 py-2.5">
                      {enq.is_synthetic ? (
                        <span className="rounded bg-muted px-2 py-0.5 text-[10px] text-muted-foreground font-semibold">
                          Synthetic
                        </span>
                      ) : (
                        <span className="rounded bg-online-soft px-2 py-0.5 text-[10px] text-online font-semibold">
                          Live
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2.5 text-muted-foreground whitespace-nowrap">
                      {enq.created_at
                        ? new Date(enq.created_at).toLocaleString("en-IN", {
                            dateStyle: "short",
                            timeStyle: "short",
                          })
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="py-12 text-center text-xs text-muted-foreground">
              No enquiry records found matching current criteria.
            </div>
          )}
        </div>

        {/* Pagination Controls */}
        {enquiriesData && enquiriesData.total > 0 && (
          <div className="mt-4 flex items-center justify-between border-t border-border pt-3 text-xs text-muted-foreground">
            <span>
              Showing {(enquiriesData.page - 1) * enquiriesData.page_size + 1} to{" "}
              {Math.min(enquiriesData.page * enquiriesData.page_size, enquiriesData.total)} of{" "}
              {enquiriesData.total} enquiries
            </span>
            <div className="flex items-center gap-1">
              <Button
                variant="icon"
                size="icon"
                disabled={enquiriesData.page <= 1}
                onClick={() => setLogPage((p) => Math.max(1, p - 1))}
              >
                <ChevronLeft className="size-4" />
              </Button>
              <span className="px-2 font-semibold">Page {enquiriesData.page}</span>
              <Button
                variant="icon"
                size="icon"
                disabled={enquiriesData.page * enquiriesData.page_size >= enquiriesData.total}
                onClick={() => setLogPage((p) => p + 1)}
              >
                <ChevronRight className="size-4" />
              </Button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
