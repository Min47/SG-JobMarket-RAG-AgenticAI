# Plan 4J: ML Training

> **Project:** SG Job Market Intelligence Platform
> **Focus:** Feature engineering, salary prediction, job clustering, role classification, model registry, and batch predictions
> **Status:** Deferred — Skeleton Only

---

## [Overview]

Single sentence: Machine learning pipeline for salary prediction, job clustering, and role classification with feature engineering, model registry, and batch inference.

Multiple paragraphs:
The ML training pipeline is currently a skeleton with class structures but no trained models. All three trainers (`ml/train.py`) return `status: "NOT_IMPLEMENTED"`. This plan documents the full design for when ML development resumes.

Three models are planned:
1. **Salary Predictor** (Regression) — Predicts salary range from job features using LightGBM
2. **Job Clusterer** (Unsupervised) — Groups similar jobs into clusters using KMeans
3. **Role Classifier** (Multi-class) — Predicts job classification from description and features

Feature engineering extracts numerical features (salary transforms, text lengths, days since posted), categorical features (one-hot encoding for location, work type, source), and embedding features (384-dim SBERT embeddings, with PCA reduction planned).

The model registry uses a versioned directory structure with joblib serialization, JSON configs, and GCS backup. Batch predictions run daily via Cloud Scheduler, writing results to a BigQuery `ml_predictions` table.

> **Note**: This plan is deferred until the GenAI stack (Plans 4A-4I) is productionized.

---

## [Architecture]

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ML TRAINING PIPELINE                                                        │
│ ─────────────────────────────────────────────────────────────────────────── │
│                                                                             │
│  Feature Engineering (ml/features.py)                                       │
│  ├── Numerical: salary transforms (log1p), text lengths, days_since_posted │
│  ├── Categorical: one-hot encoding (location, work_type, source)           │
│  └── Embedding: 384-dim SBERT, PCA 2D/10D                                  │
│                                                                             │
│  Models                                                                     │
│  ├── Salary Predictor (ml/salary_predictor.py) → LightGBM regression       │
│  ├── Job Clusterer (ml/clustering.py) → KMeans + elbow method              │
│  └── Role Classifier (ml/role_classifier.py) → LightGBM multi-class        │
│                                                                             │
│  Model Registry (ml/registry.py)                                            │
│  ├── Versioned directory structure                                          │
│  ├── joblib + JSON config persistence                                       │
│  └── GCS upload: gs://sg-job-market-data/models/                           │
│                                                                             │
│  Batch Predictions (ml/predict.py)                                          │
│  ├── Daily via Cloud Scheduler                                              │
│  └── Output: BigQuery ml_predictions table                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## [Files]

Single sentence: 5 ML module files, 1 registry file, 1 prediction file.

| File | Purpose |
|------|---------|
| `ml/features.py` | Feature engineering: numerical, categorical, embedding |
| `ml/salary_predictor.py` | LightGBM salary regression model |
| `ml/clustering.py` | KMeans job clustering with elbow method |
| `ml/role_classifier.py` | LightGBM multi-class role classification |
| `ml/train.py` | Training orchestrator (skeleton) |
| `ml/registry.py` | Model versioning, save/load, GCS upload |
| `ml/predict.py` | Batch prediction pipeline |

---

## [Feature Engineering]

File: `ml/features.py`

### Numerical Features

| Feature | Source | Transformation |
|---------|--------|----------------|
| `salary_min_monthly` | cleaned_jobs | Log transform, impute median |
| `salary_max_monthly` | cleaned_jobs | Log transform, impute median |
| `salary_mid_monthly` | Derived | `(min + max) / 2` |
| `salary_range` | Derived | `max - min` |
| `days_since_posted` | cleaned_jobs | `NOW() - job_posted_timestamp` |
| `description_length` | cleaned_jobs | `LEN(job_description)` |
| `title_length` | cleaned_jobs | `LEN(job_title)` |

### Categorical Features

| Feature | Source | Encoding |
|---------|--------|----------|
| `source` | cleaned_jobs | One-hot (2 categories) |
| `job_location` | cleaned_jobs | One-hot or target encoding |
| `job_classification` | cleaned_jobs | Label encoding (for target) |
| `job_work_type` | cleaned_jobs | One-hot |
| `company_industry` | cleaned_jobs | One-hot or target encoding |
| `company_size` | cleaned_jobs | Ordinal encoding |

### Embedding Features

| Feature | Source | Shape |
|---------|--------|-------|
| `embedding` | job_embeddings | 384 floats |
| `embedding_pca_2d` | Derived | 2 floats (for visualization) |
| `embedding_pca_10d` | Derived | 10 floats (for ML) |

### Implemented

- `FeatureConfig` dataclass with numerical/categorical feature lists
- `FeatureEngineer.extract_numerical_features()` — salary transforms (log1p), text lengths, days_since_posted
- `FeatureEngineer.extract_categorical_features()` — one-hot encoding via `pd.get_dummies`
- `FeatureEngineer.prepare_training_data()` — combines numerical + categorical + embeddings
- `create_train_test_split()` — time-based split (no data leakage)

### Not Implemented

- PCA reduction for embeddings
- `get_feature_names()` returns empty list
- No BigQuery integration (`vw_ml_features` view not created)
- No sklearn Pipeline or transformer persistence

### Feature Storage

```sql
CREATE VIEW vw_ml_features AS
SELECT 
  c.job_id,
  c.source,
  c.job_title,
  c.job_classification,
  c.job_location,
  c.job_work_type,
  c.job_salary_min_sgd_monthly,
  c.job_salary_max_sgd_monthly,
  (c.job_salary_min_sgd_monthly + c.job_salary_max_sgd_monthly) / 2 AS salary_mid,
  TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), c.job_posted_timestamp, DAY) AS days_since_posted,
  LENGTH(c.job_description) AS description_length,
  e.embedding
FROM cleaned_jobs c
JOIN job_embeddings e ON c.job_id = e.job_id AND c.source = e.source
WHERE c.job_salary_min_sgd_monthly IS NOT NULL
```

### Data Splitting Strategy

- Time-based split (not random):
  - Train: Jobs posted before cutoff date
  - Validation: Jobs posted after cutoff
  - Test: Most recent 10% of jobs
- Stratify by job_classification and salary_range

---

## [Model Training]

### Salary Prediction (Regression)

File: `ml/salary_predictor.py`

| Model | Pros | Cons | Priority |
|-------|------|------|----------|
| **LightGBM** ✅ | Fast, handles categorical, good default | Requires tuning | P0 |
| **XGBoost** | Robust, well-documented | Slower than LightGBM | P1 |
| **Random Forest** | Interpretable, no tuning needed | Memory heavy | P2 |
| **Linear Regression** | Baseline, interpretable | Poor with non-linear | Baseline |

#### Implemented Skeleton

- `SalaryPredictor` class supporting LightGBM, XGBoost, Ridge
- `DEFAULT_PARAMS` for LightGBM: 31 leaves, lr=0.05, 500 estimators
- `_calculate_metrics()` — RMSE, MAE, R², MAPE
- `get_feature_importance()` — top-N feature ranking
- `save()` / `load()` — joblib + JSON config persistence

#### Not Implemented

- No training data loaded from BigQuery
- No model trained or saved to `models/`

#### Hyperparameter Tuning

- Use Optuna or RandomizedSearchCV
- Key hyperparameters for LightGBM:
  - `num_leaves`: [31, 50, 100]
  - `learning_rate`: [0.01, 0.05, 0.1]
  - `n_estimators`: [100, 500, 1000]
  - `min_child_samples`: [20, 50, 100]
- Log all experiments to `ml/experiments/`

#### Evaluation

```python
def evaluate_regression(y_true, y_pred) -> Dict[str, float]:
    return {
        "rmse": np.sqrt(mean_squared_error(y_true, y_pred)),
        "mae": mean_absolute_error(y_true, y_pred),
        "r2": r2_score(y_true, y_pred),
        "mape": mean_absolute_percentage_error(y_true, y_pred),
    }
```

- Create residual plots
- Analyze errors by salary range and job type

**Target metrics:**
- RMSE < $1,500 SGD
- MAE < $1,000 SGD
- R² > 0.7

---

### Job Clustering (Unsupervised)

File: `ml/clustering.py`

#### Implemented Skeleton

- `JobClusterer` with KMeans (elbow method support)
- `_generate_cluster_labels()` — keyword extraction from job titles
- `analyze_clusters()` — per-cluster salary stats, top locations
- `find_optimal_clusters()` — inertia sweep across k range
- `reduce_dimensions()` — PCA and UMAP support
- `save()` / `load()` persistence

#### Dimensionality Reduction

- Implement PCA for feature reduction
- Implement UMAP for visualization
- Create 2D/3D scatter plots with cluster colors

#### Cluster Analysis

- Generate cluster summaries:
  - Cluster size distribution
  - Average salary per cluster
  - Top job titles per cluster
  - Top companies per cluster
- Name clusters (e.g., "Tech/Software", "Finance/Banking", "Healthcare")

**Target metrics:**
- Silhouette Score > 0.3
- Balanced cluster sizes (no cluster < 5% of data)

---

### Job Role Classification (Multi-class)

#### Classification Pipeline

```python
class RoleClassifier:
    def __init__(self, model_type: str = "lightgbm")
    def train(self, X: pd.DataFrame, y: pd.Series) -> None
    def predict(self, X: pd.DataFrame) -> np.ndarray
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray
    def evaluate(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]
```

- Handle class imbalance (SMOTE or class weights)
- Implement top-k accuracy for multi-class

#### Evaluation Metrics

```python
def evaluate_classification(y_true, y_pred) -> Dict[str, float]:
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "f1_macro": f1_score(y_true, y_pred, average='macro'),
        "f1_weighted": f1_score(y_true, y_pred, average='weighted'),
    }
```

- Create confusion matrix visualization
- Per-class precision/recall analysis

**Target Metrics:**
- F1 Macro: > 0.6
- Top-3 Accuracy: > 0.85

---

## [Model Registry]

### Directory Structure

```
/models/
  salary_predictor/
    v1/
      model.joblib
      config.json
      metrics.json
      feature_names.json
  role_classifier/
    v1/
      model.joblib
      config.json
      metrics.json
      label_encoder.joblib
  clustering/
    v1/
      model.joblib
      config.json
      metrics.json
      cluster_labels.json
```

### Registry API

```python
# ml/registry.py
def save_model(model, name: str, version: str, metrics: Dict) -> Path
def load_model(name: str, version: str = "latest") -> Any
def list_models() -> List[Dict]
def get_model_metrics(name: str, version: str) -> Dict
```

### GCS Upload

- Upload models to: `gs://sg-job-market-data/models/`
- Implement model download for inference
- Version management (keep last 5 versions)

---

## [Batch Predictions]

### Prediction Pipeline

```python
# ml/predict.py
def predict_salary_batch(job_ids: List[str]) -> Dict[str, float]
def predict_cluster_batch(job_ids: List[str]) -> Dict[str, int]
def predict_all_new_jobs() -> Dict[str, Any]
```

- Write predictions to BigQuery `ml_predictions` table
- Schedule daily predictions (Cloud Scheduler → Cloud Function)

### Predictions Table Schema

```python
@dataclass
class MLPrediction:
    job_id: str
    source: str
    predicted_salary: float
    salary_confidence: float
    predicted_cluster: int
    cluster_name: str
    predicted_at: datetime
```

---

## [Acceptance Criteria]

| Criterion | Target | How to Measure |
|-----------|--------|----------------|
| Salary RMSE | < $1,500 SGD | Evaluation on test set |
| Salary MAE | < $1,000 SGD | Evaluation on test set |
| Salary R² | > 0.7 | Evaluation on test set |
| Cluster Silhouette | > 0.3 | Cluster analysis |
| Classification F1 | > 0.6 (macro) | Evaluation on test set |
| Classification Top-3 | > 0.85 | Evaluation on test set |
| No data leakage | Time-based split enforced | Code review |
| Model registry | Versioned saves to GCS | Registry tests |
| Batch predictions | Daily scheduled predictions | Cloud Scheduler check |

---

## [Resumption Checklist]

When resuming ML development:
- [ ] Create BigQuery `vw_ml_features` view
- [ ] Implement PCA for embeddings
- [ ] Load training data from BigQuery
- [ ] Train salary predictor with LightGBM
- [ ] Tune hyperparameters with Optuna
- [ ] Train job clusterer with KMeans
- [ ] Implement role classifier
- [ ] Build model registry with GCS upload
- [ ] Create batch prediction pipeline
- [ ] Schedule daily predictions

---

*Document version: 1.0*
