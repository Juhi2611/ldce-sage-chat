"""KDD Pipeline Orchestrator.

run_kdd(run_id, db, include_synthetic) executes all 6 KDD steps in order and
persists results to the database. Each step updates the KDDRunLog.current_step
so the frontend progress stepper stays in sync.

Steps
-----
1. Selection      – select_data()
2. Preprocessing  – preprocess()
3. Transformation – transform()
4. Mining         – run_classification(), run_clustering(), run_apriori()
5. Evaluation     – evaluate_rules()
6. Presentation   – persist all results to DB (done here)
"""
import json
import uuid
from datetime import datetime

import pandas as pd
from sqlalchemy.orm import Session

from ..models import KDDRunLog, MinedRule, MinedCluster, ModelMetric
from .selection import select_data
from .preprocessing import preprocess
from .transformation import transform
from .mining import run_classification, run_clustering, run_apriori
from .evaluation import evaluate_rules

import joblib
from ..config import settings, DATA_DIR, MODELS_DIR


def _update_step(db: Session, run_id: str, step: int, status: str = "running") -> None:
    log = db.query(KDDRunLog).filter(KDDRunLog.run_id == run_id).first()
    if log:
        log.current_step = step
        log.status = status
        log.updated_at = datetime.utcnow()
        db.commit()


def run_kdd(run_id: str, db: Session, include_synthetic: bool = True) -> dict:
    """Execute the full KDD pipeline.

    Parameters
    ----------
    run_id : str              – unique identifier for this run
    db : sqlalchemy Session   – open DB session
    include_synthetic : bool  – if False, exclude is_synthetic rows from analysis

    Returns
    -------
    Summary dict with key metrics from each step.
    """
    # Initialise run log
    log = KDDRunLog(
        run_id=run_id,
        status="running",
        current_step=0,
        include_synthetic=include_synthetic,
    )
    db.add(log)
    db.commit()

    try:
        # --- Step 1: Selection ---
        _update_step(db, run_id, 1)
        df = select_data(db, include_synthetic=include_synthetic)
        if df.empty:
            _finish(db, run_id, "error", error="No valid data to analyse. Seed some enquiries first.")
            return {"error": "No data"}

        # --- Step 2: Preprocessing ---
        _update_step(db, run_id, 2)
        df_clean, preprocess_report = preprocess(df)
        if df_clean.empty:
            _finish(db, run_id, "error", error="All rows removed during preprocessing.")
            return {"error": "No data after preprocessing"}

        # --- Step 3: Transformation ---
        _update_step(db, run_id, 3)
        transformed = transform(df_clean)
        basket = transformed["basket"]
        tfidf_matrix = transformed["tfidf_matrix"]
        vectorizer = transformed["vectorizer"]

        # --- Step 4: Mining ---
        _update_step(db, run_id, 4)

        # Load training corpus for classifier benchmarking
        from ..chatbot.classifier import get_training_data
        texts, labels = get_training_data()

        # Load holdout CSV if present
        holdout_df = _load_holdout()

        clf_results = run_classification(texts, labels, holdout_df)
        clusters = run_clustering(tfidf_matrix, vectorizer)
        raw_rules = run_apriori(basket)

        # --- Step 5: Evaluation ---
        _update_step(db, run_id, 5)
        evaluated_rules = evaluate_rules(raw_rules)

        # --- Step 6: Presentation (persist to DB) ---
        _update_step(db, run_id, 6)

        # Clear previous results for this run
        db.query(MinedRule).filter(MinedRule.run_id == run_id).delete()
        db.query(MinedCluster).filter(MinedCluster.run_id == run_id).delete()
        db.query(ModelMetric).filter(ModelMetric.run_id == run_id).delete()

        # Find best model by f1_score
        best_model_name = max(clf_results, key=lambda r: r["f1_score"])["model_name"]

        # Persist classifier metrics
        for r in clf_results:
            is_active = r["model_name"] == settings.classifier_algorithm
            metric = ModelMetric(
                run_id=run_id,
                model_name=r["model_name"],
                accuracy=r["accuracy"],
                precision=r["precision"],
                recall=r["recall"],
                f1_score=r["f1_score"],
                confusion_matrix_json=json.dumps(r["confusion_matrix"]),
                holdout_accuracy=r.get("holdout_accuracy"),
                is_active=is_active,
            )
            db.add(metric)
            # Save the trained model pipeline
            pipe = r["pipeline"]
            MODELS_DIR.mkdir(exist_ok=True)
            joblib.dump(
                {"pipeline": pipe, "algorithm": r["model_name"], "run_id": run_id},
                MODELS_DIR / f"classifier_{r['model_name']}.joblib",
            )

        # Persist clusters
        for c in clusters:
            cluster = MinedCluster(
                run_id=run_id,
                cluster_id=c["cluster_id"],
                label=c["label"],
                size_pct=c["size_pct"],
                top_terms_json=json.dumps(c["top_terms"]),
            )
            db.add(cluster)

        # Persist rules
        for rule in evaluated_rules:
            mined = MinedRule(
                run_id=run_id,
                antecedent=rule["antecedent"],
                consequent=rule["consequent"],
                support=rule["support"],
                confidence=rule["confidence"],
                lift=rule["lift"],
                status=rule["status"],
            )
            db.add(mined)

        db.commit()

        summary = {
            "run_id": run_id,
            "include_synthetic": include_synthetic,
            "preprocessing": preprocess_report,
            "classification": [
                {k: v for k, v in r.items() if k != "pipeline"}
                for r in clf_results
            ],
            "best_model": best_model_name,
            "n_clusters": len(clusters),
            "n_rules_total": len(raw_rules),
            "n_rules_useful": sum(1 for r in evaluated_rules if r["status"] == "Useful"),
        }

        _finish(db, run_id, "done", summary=summary)
        return summary

    except Exception as e:
        _finish(db, run_id, "error", error=str(e))
        raise


def _finish(
    db: Session,
    run_id: str,
    status: str,
    summary: dict | None = None,
    error: str | None = None,
) -> None:
    log = db.query(KDDRunLog).filter(KDDRunLog.run_id == run_id).first()
    if log:
        log.status = status
        log.summary_json = json.dumps(summary) if summary else None
        log.error = error
        log.updated_at = datetime.utcnow()
        db.commit()


def _load_holdout() -> pd.DataFrame | None:
    path = DATA_DIR / "holdout_questions.csv"
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path)
        df = df[["text", "expected_category"]].dropna()
        df.columns = ["text", "expected_category"]
        return df
    except Exception:
        return None
