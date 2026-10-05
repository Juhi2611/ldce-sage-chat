"""SQLAlchemy ORM models for the LDCE enquiry system.

Tables
------
enquiries       – every non-small-talk message processed
sessions        – browser session tracking (anonymous)
feedback        – thumbs up / down per enquiry
mined_rules     – Apriori association rules from a KDD run
mined_clusters  – K-Means cluster descriptors from a KDD run
model_metrics   – Classifier evaluation results from a KDD run
kdd_run_log     – Execution log / status for each KDD pipeline run
"""
import json
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, Integer, String, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


class Session(Base):
    """Anonymous browser session."""
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    enquiries: Mapped[list["Enquiry"]] = relationship("Enquiry", back_populates="session")


class Enquiry(Base):
    """One processed chat turn (excluding small-talk)."""
    __tablename__ = "enquiries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("sessions.id"), index=True)
    raw_question: Mapped[str] = mapped_column(Text)
    normalized_question: Mapped[str] = mapped_column(Text)
    predicted_category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    predicted_department: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    predicted_topic: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    user_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    session: Mapped["Session"] = relationship("Session", back_populates="enquiries")
    feedbacks: Mapped[list["Feedback"]] = relationship("Feedback", back_populates="enquiry")


class Feedback(Base):
    """Thumbs-up / thumbs-down per enquiry."""
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    enquiry_id: Mapped[int] = mapped_column(Integer, ForeignKey("enquiries.id"), index=True)
    rating: Mapped[str] = mapped_column(String(4))  # "up" | "down"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    enquiry: Mapped["Enquiry"] = relationship("Enquiry", back_populates="feedbacks")


class MinedRule(Base):
    """One Apriori association rule discovered during a KDD run."""
    __tablename__ = "mined_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    antecedent: Mapped[str] = mapped_column(String(200))
    consequent: Mapped[str] = mapped_column(String(200))
    support: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    lift: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(10))  # "Useful" | "Weak"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MinedCluster(Base):
    """One K-Means cluster descriptor from a KDD run."""
    __tablename__ = "mined_clusters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    cluster_id: Mapped[int] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(String(100))
    size_pct: Mapped[float] = mapped_column(Float)
    top_terms_json: Mapped[str] = mapped_column(Text)  # JSON list of strings
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    @property
    def top_terms(self) -> list[str]:
        return json.loads(self.top_terms_json)


class ModelMetric(Base):
    """Classifier evaluation results for one algorithm in one KDD run."""
    __tablename__ = "model_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    model_name: Mapped[str] = mapped_column(String(50))
    accuracy: Mapped[float] = mapped_column(Float)
    precision: Mapped[float] = mapped_column(Float)
    recall: Mapped[float] = mapped_column(Float)
    f1_score: Mapped[float] = mapped_column(Float)
    confusion_matrix_json: Mapped[str] = mapped_column(Text)  # JSON 2-D list
    holdout_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    @property
    def confusion_matrix(self) -> list[list[int]]:
        return json.loads(self.confusion_matrix_json)


class KDDRunLog(Base):
    """Execution log and current step for a KDD pipeline run."""
    __tablename__ = "kdd_run_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | running | done | error
    current_step: Mapped[int] = mapped_column(Integer, default=0)
    summary_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    include_synthetic: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
