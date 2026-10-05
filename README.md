# LDCE Smart Enquiry Assistant & KDD Discovery System

An end-to-end intelligent enquiry assistant and analytics platform for **L. D. College of Engineering (LDCE), Ahmedabad, Gujarat**.

The system combines:
1. **Frontend**: A modern, responsive React 19 interface (TanStack Start + Tailwind CSS + Recharts + Framer Motion) providing instant conversational enquiry handling and an administrative KDD analytics dashboard.
2. **Backend**: A FastAPI Python backend featuring Scikit-Learn intent classification (Naive Bayes, Decision Tree, KNN), entity extraction, and a 6-stage Knowledge Discovery in Databases (KDD) pipeline with Apriori association rule mining and K-Means clustering.

---

## 🏛️ Architecture Overview

```
├── frontend (src/)              # React 19 + TanStack Router + Tailwind CSS + Recharts
│   ├── components/              # ChatExperience, SiteShell, PageFooter, UI kit
│   ├── hooks/useChat.ts         # Live chat orchestration hook
│   ├── lib/api.ts               # Typed API client connecting to FastAPI
│   ├── lib/session.ts           # Anonymous session UUID & admin session management
│   └── routes/                  # Chat (index), Departments catalogue, Admin Dashboard
│
└── backend/                     # FastAPI Application
    ├── app/                     # API routers, configuration, and schemas
    │   ├── chatbot/             # Normalizer, Intent Classifiers, Entity Extraction, Answer Retrieval
    │   ├── kdd/                 # 6-Stage Pipeline (Selection → Preprocessing → Transformation → Mining → Evaluation → Presentation)
    │   ├── config.py            # Path resolution & settings
    │   └── models.py            # SQLAlchemy SQLite schema
    ├── data/                    # Knowledge base, holdout questions & seeds
    ├── models_saved/            # Persisted Joblib classifier pipelines
    └── scripts/                 # CLI utilities (reset_db, run_kdd, train_classifier)
```

---

## 🚀 Quickstart Guide

### 1. Backend Setup

**Python Version Requirement**: Python 3.11+ (tested on Python 3.11 through 3.13.5 with Scikit-Learn 1.6+ and FastAPI).

```sh
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Reset DB & Seed Demo Data (generates ~4,800 enquiries across 1,200 sessions)
python scripts/reset_db.py

# Train intent classification models & benchmark on holdout set
python scripts/train_classifier.py

# Execute the 6-stage KDD analytics pipeline
python scripts/run_kdd.py

# Start FastAPI development server (runs on http://127.0.0.1:8000)
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup

Prerequisites: Node.js 18+ and npm

```sh
# From root directory:
npm install

# Start development server (runs on http://localhost:5173 with proxy to backend)
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## 📊 KDD Analytics & Data Mining

The backend implements the 6-stage Knowledge Discovery in Databases process:
1. **Selection**: Queries database records while filtering out noise and intake errors.
2. **Preprocessing**: Cleans text, removes duplicates within 60s windows, and handles missing values.
3. **Transformation**: Generates temporal features (time-of-day, weekday/weekend) and builds session-level cross-tabulated basket matrices and TF-IDF document vectors.
4. **Data Mining**:
   - **Association Rule Mining (Apriori)**: Extracts co-occurrence rules (e.g. *Hostel → Campus Facilities*, *Admissions → Fees*, *Placements → Departments*).
   - **Clustering (K-Means)**: Automatically identifies clusters of enquiry topics using silhouette-optimal cluster count.
   - **Classification Benchmarking**: Trains and benchmarks Multinomial Naive Bayes, Decision Tree, and K-Nearest Neighbors.
5. **Evaluation**: Labels rules as *Useful* or *Weak* based on support, confidence, and lift thresholds.
6. **Presentation**: Persists insights to SQLite and serves real-time charts, heatmaps, and metrics to the Admin Dashboard.

> **Note on Simulated Demo Data**:
> Synthetic enquiries seeded via `scripts/seed_synthetic.py` are explicitly flagged with `is_synthetic=True`. They simulate multi-turn admissions season traffic, evening enquiry spikes, and realistic co-occurrences for analytics and viva demonstrations. Toggle **"Include demo data"** in the Admin Dashboard to switch between simulated and live student enquiry datasets.

---

## 🔒 Admin Dashboard Access

- **Admin Route**: `/admin`
- **Default Admin Token**: `change_me` (configure via `ADMIN_TOKEN` in `backend/.env`)
- Provides live KPI cards, category distribution donut, department enquiry volume, traffic trends with day/month granularity, time-of-day distributions, association rules tables, cluster breakdowns, model confusion matrices, holdout accuracy evaluations, live enquiry log searches, and interactive triggers for retraining models and running KDD pipelines.

---

## 🧪 Testing

```sh
# Backend test suite (Pytest - 45 unit & integration tests)
cd backend
pytest

# Frontend build & type checking
npm run build
npm run lint
```
