"""Pydantic schemas for API requests and responses."""
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict


# ─── Chat Schemas ────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User question text")
    session_id: str = Field(..., min_length=1, description="Browser session UUID")
    algorithm: Optional[str] = Field(None, description="naive_bayes | decision_tree | knn")


class SuggestionItem(BaseModel):
    label: str
    question: str
    source: str  # "mined" | "default"


class ChatResponse(BaseModel):
    answer_markdown: str
    intent: str
    department: Optional[str] = None
    topic: Optional[str] = None
    confidence: float
    resolved: bool
    suggestions: list[SuggestionItem] = []
    enquiry_id: Optional[int] = None
    source_url: Optional[str] = None
    is_smalltalk: bool = False


class FeedbackRequest(BaseModel):
    enquiry_id: int
    rating: str = Field(..., pattern="^(up|down)$")


# ─── Analytics Schemas ────────────────────────────────────────────────────────

class StatCard(BaseModel):
    title: str
    value: str
    change: str
    trend: str  # "up" | "down" | "neutral"


class CategoryDistributionItem(BaseModel):
    category: str
    count: int
    percentage: float


class TrafficTrendItem(BaseModel):
    time: str
    count: int


class TemporalPatternItem(BaseModel):
    period: str
    count: int
    topCategory: str


class AnalyticsOverviewResponse(BaseModel):
    stats: list[StatCard]
    categoryDistribution: list[CategoryDistributionItem]
    trafficTrend: list[TrafficTrendItem]
    temporalPattern: list[TemporalPatternItem]
    recentLogCount: int


class MinedRuleItem(BaseModel):
    id: int
    antecedent: str
    consequent: str
    support: float
    confidence: float
    lift: float
    status: str  # "Useful" | "Weak"


class ClusterItem(BaseModel):
    cluster_id: int
    label: str
    size_pct: float
    top_terms: list[str]


class ModelMetricItem(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_name: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    confusion_matrix: list[list[int]]
    holdout_accuracy: Optional[float] = None
    is_active: bool


class EnquiryLogItem(BaseModel):
    id: int
    session_id: str
    raw_question: str
    predicted_category: Optional[str] = None
    predicted_department: Optional[str] = None
    confidence: float
    resolved: bool
    created_at: str
    is_synthetic: bool
    user_rating: Optional[str] = None


class KDDStatusResponse(BaseModel):
    run_id: Optional[str] = None
    status: str  # "idle" | "pending" | "running" | "done" | "error"
    current_step: int = 0
    summary: Optional[dict] = None
    error: Optional[str] = None
    include_synthetic: bool = True
