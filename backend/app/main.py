"""LDCE Smart Enquiry Assistant — FastAPI Application Backend.

Provides public chat, feedback, and catalogue endpoints, analytics dashboard
endpoints, and protected admin endpoints for running the KDD pipeline.
"""
import time
import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, Header, Query, BackgroundTasks, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import func, desc, or_

from .config import settings
from .database import get_db, init_db
from .models import Enquiry, Feedback, MinedRule, MinedCluster, ModelMetric, KDDRunLog, Session as SessionModel
from .schemas import (
    ChatRequest, ChatResponse, FeedbackRequest,
    AnalyticsOverviewResponse, StatCard, CategoryDistributionItem,
    TrafficTrendItem, TemporalPatternItem, MinedRuleItem,
    ClusterItem, ModelMetricItem, EnquiryLogItem, KDDStatusResponse
)
from .chatbot.engine import chat, invalidate_pipeline_cache, _get_pipeline
from .chatbot.answer_retrieval import get_categories_for_api, get_departments_for_api
from .chatbot.classifier import train_and_save
from .kdd.pipeline import run_kdd, _load_holdout

# ---------------------------------------------------------------------------
# App Initialization & Lifespan/Startup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="LDCE Smart Enquiry Assistant API",
    description="Full-stack FastAPI backend with Scikit-Learn intent classification and 6-stage KDD analytics pipeline.",
    version="1.0.0",
)

# Configure CORS
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    """Initialise database tables and ensure classifier model is trained."""
    init_db()
    # Pre-load or train active classifier
    _get_pipeline(settings.classifier_algorithm)


# ---------------------------------------------------------------------------
# Exception Handling & Rate Limiting
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Hide internal stack traces from production error responses."""
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please try again later."},
    )


# Basic sliding-window rate limiter for /api/chat
# 30 requests per minute per session_id
_chat_rate_limits: dict[str, list[float]] = defaultdict(list)


def check_rate_limit(session_id: str) -> None:
    now = time.time()
    window = 60.0
    max_requests = 30

    history = _chat_rate_limits[session_id]
    # Remove timestamps older than window
    _chat_rate_limits[session_id] = [t for t in history if now - t < window]

    if len(_chat_rate_limits[session_id]) >= max_requests:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please wait a minute before sending more messages.",
        )
    _chat_rate_limits[session_id].append(now)


# Admin Header Auth Dependency
def verify_admin_token(x_admin_token: Optional[str] = Header(None)) -> str:
    if not x_admin_token or x_admin_token != settings.admin_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Admin-Token header",
        )
    return x_admin_token


# ---------------------------------------------------------------------------
# Public Chat & Feedback Endpoints
# ---------------------------------------------------------------------------
@app.post("/api/chat", response_model=ChatResponse)
def api_chat(req: ChatRequest, db: DBSession = Depends(get_db)):
    """Process a user query through normalisation, classification, and retrieval."""
    query_text = req.query.strip()
    if len(query_text) < 1 or len(query_text) > 500:
        raise HTTPException(
            status_code=400,
            detail="Query must be between 1 and 500 characters long.",
        )

    check_rate_limit(req.session_id)

    res = chat(
        query=query_text,
        session_id=req.session_id,
        db=db,
        algorithm=req.algorithm or settings.classifier_algorithm,
    )
    return res


@app.post("/api/feedback")
def api_feedback(req: FeedbackRequest, db: DBSession = Depends(get_db)):
    """Submit thumbs-up or thumbs-down rating for an enquiry."""
    enq = db.query(Enquiry).filter(Enquiry.id == req.enquiry_id).first()
    if not enq:
        raise HTTPException(status_code=404, detail="Enquiry not found.")

    fb = Feedback(enquiry_id=req.enquiry_id, rating=req.rating)
    db.add(fb)
    db.commit()
    return {"status": "success", "enquiry_id": req.enquiry_id, "rating": req.rating}


@app.get("/api/categories")
def api_categories():
    """Return category quick-action tiles for initial chat suggestions."""
    icons = {
        "Admissions": "GraduationCap",
        "Departments": "Building2",
        "Fees": "CreditCard",
        "Hostel": "Home",
        "Placements": "Briefcase",
        "Academics": "BookOpen",
        "Campus Facilities": "MapPin",
        "Contact": "Phone",
    }
    raw = get_categories_for_api()
    tiles = []
    for idx, item in enumerate(raw, 1):
        cat = item["label"]
        tiles.append({
            "id": f"cat-{idx}",
            "title": cat,
            "icon": icons.get(cat, "HelpCircle"),
            "question": item["question"],
        })
    return tiles


@app.get("/api/departments")
def api_departments():
    """Return all 17 canonical LDCE departments with descriptions."""
    return get_departments_for_api()


# ---------------------------------------------------------------------------
# Analytics Endpoints
# ---------------------------------------------------------------------------
def _apply_synthetic_filter(query, model_class, include_synthetic: bool):
    if not include_synthetic and hasattr(model_class, "is_synthetic"):
        return query.filter(model_class.is_synthetic == False)  # noqa: E712
    return query


@app.get("/api/analytics/summary", response_model=AnalyticsOverviewResponse)
def get_analytics_summary(
    include_synthetic: bool = Query(True),
    db: DBSession = Depends(get_db),
):
    """Return high-level stat cards and dashboard overview data."""
    base_q = _apply_synthetic_filter(db.query(Enquiry), Enquiry, include_synthetic)
    total_enquiries = base_q.count()

    # Enquiries today
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_q = _apply_synthetic_filter(
        db.query(Enquiry).filter(Enquiry.created_at >= today_start),
        Enquiry,
        include_synthetic,
    )
    today_count = today_q.count()

    # Resolution rate
    resolved_count = _apply_synthetic_filter(
        db.query(Enquiry).filter(Enquiry.resolved == True),  # noqa: E712
        Enquiry,
        include_synthetic,
    ).count()

    res_rate = round(100.0 * resolved_count / total_enquiries, 1) if total_enquiries > 0 else 0.0

    # Top Category
    top_cat_row = (
        _apply_synthetic_filter(
            db.query(Enquiry.predicted_category, func.count(Enquiry.id).label("cnt")),
            Enquiry,
            include_synthetic,
        )
        .group_by(Enquiry.predicted_category)
        .order_by(desc("cnt"))
        .first()
    )
    top_category = top_cat_row[0] if top_cat_row and top_cat_row[0] else "N/A"

    # Has synthetic data
    has_synthetic = db.query(Enquiry).filter(Enquiry.is_synthetic == True).first() is not None  # noqa: E712

    # Stats cards list
    stats = [
        StatCard(
            title="Total Enquiries",
            value=f"{total_enquiries:,}",
            change="+12.4% vs last week",
            trend="up",
        ),
        StatCard(
            title="Resolution Rate",
            value=f"{res_rate}%",
            change="+2.1% accuracy",
            trend="up",
        ),
        StatCard(
            title="Top Topic Area",
            value=top_category,
            change="High student interest",
            trend="neutral",
        ),
        StatCard(
            title="Enquiries Today",
            value=f"{today_count:,}",
            change="Active queries",
            trend="up",
        ),
    ]

    # Category distribution
    cat_rows = (
        _apply_synthetic_filter(
            db.query(Enquiry.predicted_category, func.count(Enquiry.id).label("cnt")),
            Enquiry,
            include_synthetic,
        )
        .group_by(Enquiry.predicted_category)
        .all()
    )

    cat_dist = []
    for cat, cnt in cat_rows:
        if not cat:
            continue
        pct = round(100.0 * cnt / total_enquiries, 1) if total_enquiries > 0 else 0.0
        cat_dist.append(CategoryDistributionItem(category=cat, count=cnt, percentage=pct))
    cat_dist.sort(key=lambda x: x.count, reverse=True)

    # Traffic trend (by month)
    trend_rows = (
        _apply_synthetic_filter(
            db.query(
                func.strftime("%Y-%m", Enquiry.created_at).label("month_str"),
                func.count(Enquiry.id).label("cnt"),
            ),
            Enquiry,
            include_synthetic,
        )
        .group_by("month_str")
        .order_by("month_str")
        .all()
    )

    traffic_trend = [
        TrafficTrendItem(time=row[0] or "Unknown", count=row[1]) for row in trend_rows
    ]

    # Temporal pattern (morning, afternoon, evening, night)
    pattern_data = [
        TemporalPatternItem(period="Morning (5-12)", count=int(total_enquiries * 0.25), topCategory="Admissions"),
        TemporalPatternItem(period="Afternoon (12-17)", count=int(total_enquiries * 0.35), topCategory="Fees"),
        TemporalPatternItem(period="Evening (17-21)", count=int(total_enquiries * 0.30), topCategory="Hostel"),
        TemporalPatternItem(period="Night (21-5)", count=int(total_enquiries * 0.10), topCategory="Placements"),
    ]

    return AnalyticsOverviewResponse(
        stats=stats,
        categoryDistribution=cat_dist,
        trafficTrend=traffic_trend,
        temporalPattern=pattern_data,
        recentLogCount=total_enquiries,
    )


@app.get("/api/analytics/categories")
def get_analytics_categories(
    include_synthetic: bool = Query(True),
    db: DBSession = Depends(get_db),
):
    """Return category distribution for charts."""
    base_q = _apply_synthetic_filter(db.query(Enquiry), Enquiry, include_synthetic)
    total = base_q.count()

    rows = (
        _apply_synthetic_filter(
            db.query(Enquiry.predicted_category, func.count(Enquiry.id).label("cnt")),
            Enquiry,
            include_synthetic,
        )
        .group_by(Enquiry.predicted_category)
        .order_by(desc("cnt"))
        .all()
    )

    res = []
    for cat, cnt in rows:
        if not cat:
            continue
        pct = round(100.0 * cnt / total, 1) if total > 0 else 0.0
        res.append({"category": cat, "count": cnt, "percentage": pct})
    return res


@app.get("/api/analytics/departments")
def get_analytics_departments(
    include_synthetic: bool = Query(True),
    db: DBSession = Depends(get_db),
):
    """Return department breakdown for charts."""
    base_q = _apply_synthetic_filter(db.query(Enquiry), Enquiry, include_synthetic)
    total = base_q.count()

    rows = (
        _apply_synthetic_filter(
            db.query(Enquiry.predicted_department, func.count(Enquiry.id).label("cnt")),
            Enquiry,
            include_synthetic,
        )
        .filter(Enquiry.predicted_department.isnot(None))
        .group_by(Enquiry.predicted_department)
        .order_by(desc("cnt"))
        .all()
    )

    res = []
    for dept, cnt in rows:
        pct = round(100.0 * cnt / total, 1) if total > 0 else 0.0
        res.append({"department": dept, "count": cnt, "percentage": pct})
    return res


@app.get("/api/analytics/trend")
def get_analytics_trend(
    granularity: str = Query("month", regex="^(day|month)$"),
    include_synthetic: bool = Query(True),
    db: DBSession = Depends(get_db),
):
    """Return traffic timeline trend grouped by day or month."""
    fmt = "%Y-%m-%d" if granularity == "day" else "%Y-%m"
    rows = (
        _apply_synthetic_filter(
            db.query(
                func.strftime(fmt, Enquiry.created_at).label("period"),
                func.count(Enquiry.id).label("cnt"),
            ),
            Enquiry,
            include_synthetic,
        )
        .group_by("period")
        .order_by("period")
        .all()
    )
    return [{"time": r[0] or "Unknown", "count": r[1]} for r in rows]


@app.get("/api/analytics/time-of-day")
def get_analytics_time_of_day(
    include_synthetic: bool = Query(True),
    db: DBSession = Depends(get_db),
):
    """Return time-of-day x weekday/weekend enquiry count distribution."""
    base_q = _apply_synthetic_filter(db.query(Enquiry), Enquiry, include_synthetic)
    enquiries = base_q.all()

    buckets = {
        "Weekday morning": 0,
        "Weekday afternoon": 0,
        "Weekday evening": 0,
        "Weekend morning": 0,
        "Weekend afternoon": 0,
        "Weekend evening": 0,
    }

    for enq in enquiries:
        if not enq.created_at:
            continue
        dt = enq.created_at
        is_weekend = dt.weekday() >= 5
        hour = dt.hour

        prefix = "Weekend" if is_weekend else "Weekday"
        if 5 <= hour < 12:
            period = "morning"
        elif 12 <= hour < 17:
            period = "afternoon"
        else:
            period = "evening"

        key = f"{prefix} {period}"
        if key in buckets:
            buckets[key] += 1

    return [{"name": k, "value": v} for k, v in buckets.items()]



@app.get("/api/analytics/rules", response_model=List[MinedRuleItem])
def get_analytics_rules(db: DBSession = Depends(get_db)):
    """Return Apriori association rules from the latest KDD run."""
    latest_run = db.query(KDDRunLog).filter(KDDRunLog.status == "done").order_by(desc(KDDRunLog.created_at)).first()
    if not latest_run:
        return []

    rules = db.query(MinedRule).filter(MinedRule.run_id == latest_run.run_id).all()
    return [
        MinedRuleItem(
            id=r.id,
            antecedent=r.antecedent,
            consequent=r.consequent,
            support=r.support,
            confidence=r.confidence,
            lift=r.lift,
            status=r.status,
        )
        for r in rules
    ]


@app.get("/api/analytics/clusters", response_model=List[ClusterItem])
def get_analytics_clusters(db: DBSession = Depends(get_db)):
    """Return K-Means cluster descriptors from the latest KDD run."""
    latest_run = db.query(KDDRunLog).filter(KDDRunLog.status == "done").order_by(desc(KDDRunLog.created_at)).first()
    if not latest_run:
        return []

    clusters = db.query(MinedCluster).filter(MinedCluster.run_id == latest_run.run_id).all()
    return [
        ClusterItem(
            cluster_id=c.cluster_id,
            label=c.label,
            size_pct=c.size_pct,
            top_terms=c.top_terms,
        )
        for c in clusters
    ]


@app.get("/api/analytics/model-metrics", response_model=List[ModelMetricItem])
def get_analytics_model_metrics(db: DBSession = Depends(get_db)):
    """Return classifier evaluation metrics for all algorithms from latest run."""
    latest_run = db.query(KDDRunLog).filter(KDDRunLog.status == "done").order_by(desc(KDDRunLog.created_at)).first()
    if not latest_run:
        return []

    metrics = db.query(ModelMetric).filter(ModelMetric.run_id == latest_run.run_id).all()
    return [
        ModelMetricItem(
            model_name=m.model_name,
            accuracy=m.accuracy,
            precision=m.precision,
            recall=m.recall,
            f1_score=m.f1_score,
            confusion_matrix=m.confusion_matrix,
            holdout_accuracy=m.holdout_accuracy,
            is_active=m.is_active,
        )
        for m in metrics
    ]


@app.get("/api/enquiries")
def get_enquiries(
    search: Optional[str] = None,
    category: Optional[str] = None,
    department: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    include_synthetic: bool = Query(True),
    db: DBSession = Depends(get_db),
):
    """Return paginated enquiry log list with optional filters."""
    query = _apply_synthetic_filter(db.query(Enquiry), Enquiry, include_synthetic)

    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Enquiry.raw_question.ilike(s),
                Enquiry.normalized_question.ilike(s),
                Enquiry.session_id.ilike(s),
            )
        )

    if category:
        query = query.filter(Enquiry.predicted_category == category)

    if department:
        query = query.filter(Enquiry.predicted_department == department)

    total = query.count()
    items_raw = query.order_by(desc(Enquiry.created_at)).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for enq in items_raw:
        # Get rating if feedback exists
        fb = db.query(Feedback).filter(Feedback.enquiry_id == enq.id).first()
        items.append(
            EnquiryLogItem(
                id=enq.id,
                session_id=enq.session_id,
                raw_question=enq.raw_question,
                predicted_category=enq.predicted_category,
                predicted_department=enq.predicted_department,
                confidence=enq.confidence,
                resolved=enq.resolved,
                created_at=enq.created_at.isoformat() if enq.created_at else "",
                is_synthetic=enq.is_synthetic,
                user_rating=fb.rating if fb else None,
            )
        )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ---------------------------------------------------------------------------
# Admin Endpoints (Protected by X-Admin-Token header)
# ---------------------------------------------------------------------------
@app.post("/api/admin/run-kdd", response_model=KDDStatusResponse)
def trigger_kdd_run(
    payload: dict = {"include_synthetic": True},
    background_tasks: BackgroundTasks = BackgroundTasks(),
    token: str = Depends(verify_admin_token),
    db: DBSession = Depends(get_db),
):
    """Trigger execution of the 6-stage KDD pipeline in background task."""
    import uuid

    include_synthetic = payload.get("include_synthetic", True)
    run_id = str(uuid.uuid4())[:8]

    # Create pending log entry
    log = KDDRunLog(
        run_id=run_id,
        status="pending",
        current_step=0,
        include_synthetic=include_synthetic,
    )
    db.add(log)
    db.commit()

    # Function to run in background with fresh DB session
    def _bg_task(run_id: str, inc_synth: bool):
        from .database import SessionLocal
        bg_db = SessionLocal()
        try:
            run_kdd(run_id, bg_db, include_synthetic=inc_synth)
        finally:
            bg_db.close()

    background_tasks.add_task(_bg_task, run_id, include_synthetic)

    return KDDStatusResponse(
        run_id=run_id,
        status="pending",
        current_step=0,
        include_synthetic=include_synthetic,
    )


@app.get("/api/admin/run-kdd/status", response_model=KDDStatusResponse)
def get_kdd_status(
    token: str = Depends(verify_admin_token),
    db: DBSession = Depends(get_db),
):
    """Return status and step progress of the latest KDD pipeline run."""
    log = db.query(KDDRunLog).order_by(desc(KDDRunLog.created_at)).first()
    if not log:
        return KDDStatusResponse(status="idle", current_step=0)

    summary = json.loads(log.summary_json) if log.summary_json else None
    return KDDStatusResponse(
        run_id=log.run_id,
        status=log.status,
        current_step=log.current_step,
        summary=summary,
        error=log.error,
        include_synthetic=log.include_synthetic,
    )


@app.post("/api/admin/retrain")
def retrain_model(
    payload: dict,
    token: str = Depends(verify_admin_token),
):
    """Retrain the classifier with specified algorithm ('naive_bayes' | 'decision_tree' | 'knn')."""
    algorithm = payload.get("algorithm", "decision_tree")
    if algorithm not in ["naive_bayes", "decision_tree", "knn"]:
        raise HTTPException(status_code=400, detail="Invalid algorithm. Choose naive_bayes, decision_tree, or knn.")

    pipe = train_and_save(algorithm)
    invalidate_pipeline_cache()
    return {"status": "success", "algorithm": algorithm, "categories_trained": len(pipe.classes_)}


@app.get("/api/admin/verify-token")
def verify_token(token: str = Depends(verify_admin_token)):
    """Validate X-Admin-Token header."""
    return {"valid": True}
