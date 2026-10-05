# LDCE Smart Enquiry Assistant — Backend API & KDD Analytics Engine

FastAPI full-stack backend with scikit-learn intent classification and a 6-stage Knowledge Discovery in Databases (KDD) analytics pipeline for **L. D. College of Engineering, Ahmedabad**.

---

## 🚀 Prerequisites & Installation

1. **Python Version**: Python 3.10 or higher
2. **Install Dependencies**:
   ```bash
   python -m pip install -r backend/requirements.txt
   ```
3. **Environment Setup**:
   Copy `.env.example` to `.env`:
   ```bash
   cp backend/.env.example backend/.env
   ```

---

## 🛠️ CLI Scripts & Data Pipeline

### 1. Seed Synthetic Enquiry Data

Generates ~3,000–5,000 synthetic enquiry rows across 1,200 sessions tagged with `is_synthetic=True` (demonstrating evening query bias, admission season spikes, and co-occurrence patterns):

```bash
python backend/scripts/seed_synthetic.py
```

### 2. Train and Benchmark Classifiers

Trains TF-IDF vectorizers and benchmarks Multinomial Naive Bayes, Decision Tree, and K-Nearest Neighbors on the knowledge base, template corpus, and hand-written holdout questions:

```bash
python backend/scripts/train_classifier.py
```

_Outputs accuracy, 5-fold CV statistics, holdout accuracy on `backend/data/holdout_questions.csv`, and a confidence-distribution percentile table for threshold tuning._

### 3. Run KDD Pipeline CLI

Executes all 6 stages of the KDD analytics pipeline (Data Selection, Preprocessing, Transformation, Mining, Evaluation, Presentation) and saves discovered rules, clusters, and model metrics into SQLite:

```bash
python backend/scripts/run_kdd.py [--exclude-synthetic]
```

### 4. Check Verification Status

Lists all knowledge base entries whose facts still require manual verification against official `ldce.ac.in` web pages:

```bash
python backend/scripts/list_unverified.py
```

---

## 🏃 Running the Server

Start the FastAPI server using Uvicorn:

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

- **Interactive API Documentation (Swagger / OpenAPI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Alternative ReDoc Docs**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🧪 Running Tests

Run the full pytest suite (including entity extraction, classifier, Apriori mining, and FastAPI TestClient endpoints):

```bash
python -m pytest backend/tests
```

---

## 📊 KDD Pipeline Stages

1. **Selection**: Queries database; filters out noise and optionally excludes synthetic demo rows (`include_synthetic=False`).
2. **Preprocessing**: Cleans missing values, normalises text, deduplicates session queries within 60 seconds.
3. **Transformation**: Extracts temporal features (`time_period`, `is_weekend`), builds session $\times$ category basket matrix, and TF-IDF document matrix.
4. **Mining**: Benchmark classifiers (NB/DT/KNN), K-Means clustering with silhouette $k$-selection, and Apriori association rule mining.
5. **Evaluation**: Filters rules by minimum support (0.05), confidence (0.50), and lift (> 1.2), deduplicates reciprocal rules, and tags as `Useful` or `Weak`.
6. **Presentation**: Persists metrics, clusters, and rules to the SQLite database for the Admin Dashboard and recommend engine.
