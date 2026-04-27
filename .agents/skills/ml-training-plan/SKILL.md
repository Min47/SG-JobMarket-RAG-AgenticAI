---
name: ml-training-plan
description: Brief description of what this skill does
---

# Phase 1.2 - 1.4: ML Training Plan (Deferred)

## Status: Skeleton Only — Not Trained

All ML modules have class structures but no trained models. `ml/train.py` returns `status: "NOT_IMPLEMENTED"` for all three trainers.

---

## 1.2: Feature Engineering

File: `ml/features.py`

### [Concept] Numerical Features 
| Feature | Source | Transformation |
|---------|--------|----------------|
| `salary_min_monthly` | cleaned_jobs | Log transform, impute median |
| `salary_max_monthly` | cleaned_jobs | Log transform, impute median |
| `salary_mid_monthly` | Derived | `(min + max) / 2` |
| `salary_range` | Derived | `max - min` |
| `days_since_posted` | cleaned_jobs | `NOW() - job_posted_timestamp` |
| `description_length` | cleaned_jobs | `LEN(job_description)` |
| `title_length` | cleaned_jobs | `LEN(job_title)` |

### [Concept] Categorical Features
| Feature | Source | Encoding |
|---------|--------|----------|
| `source` | cleaned_jobs | One-hot (2 categories) |
| `job_location` | cleaned_jobs | One-hot or target encoding |
| `job_classification` | cleaned_jobs | Label encoding (for target) |
| `job_work_type` | cleaned_jobs | One-hot |
| `company_industry` | cleaned_jobs | One-hot or target encoding |
| `company_size` | cleaned_jobs | Ordinal encoding |

### [Concept] Embedding Features
| Feature | Source | Shape |
|---------|--------|-------|
| `embedding` | job_embeddings | 384 floats |
| `embedding_pca_2d` | Derived | 2 floats (for visualization) |
| `embedding_pca_10d` | Derived | 10 floats (for ML) |

### Implemented:
- `FeatureConfig` dataclass with numerical/categorical feature lists
- `FeatureEngineer.extract_numerical_features()` — salary transforms (log1p), text lengths, days_since_posted
- `FeatureEngineer.extract_categorical_features()` — one-hot encoding via `pd.get_dummies`
- `FeatureEngineer.prepare_training_data()` — combines numerical + categorical + embeddings
- `create_train_test_split()` — time-based split (no data leakage)

### Not implemented:
- PCA reduction for embeddings
- `get_feature_names()` returns empty list
- No BigQuery integration (`vw_ml_features` view not created)
- No sklearn Pipeline or transformer persistence

### [Concept] Feature Storage
- [ ] Create BigQuery view `vw_ml_features`:
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

### [Concept] Data Splitting Strategy
- [ ] Implement time-based split (not random):
  - Train: Jobs posted before cutoff date
  - Validation: Jobs posted after cutoff
  - Test: Most recent 10% of jobs
- [ ] Stratify by job_classification and salary_range
- [ ] Document split ratios and date ranges

### [Concept] Acceptance Criteria
- [ ] Feature matrix created with all features
- [ ] No data leakage between train/val/test
- [ ] Feature importance analysis completed
- [ ] Documentation of all feature transformations

---

## 1.3: Model Training

> ### 1.3.1: Salary Prediction (Regression)

File: `ml/salary_predictor.py`

| Model | Pros | Cons | Priority |
|-------|------|------|----------|
| **LightGBM** ✅ | Fast, handles categorical, good default | Requires tuning | P0 |
| **XGBoost** | Robust, well-documented | Slower than LightGBM | P1 |
| **Random Forest** | Interpretable, no tuning needed | Memory heavy | P2 |
| **Linear Regression** | Baseline, interpretable | Poor with non-linear | Baseline |

#### Implemented skeleton:
- `SalaryPredictor` class supporting LightGBM, XGBoost, Ridge
- `DEFAULT_PARAMS` for LightGBM: 31 leaves, lr=0.05, 500 estimators
- `_calculate_metrics()` — RMSE, MAE, R², MAPE
- `get_feature_importance()` — top-N feature ranking
- `save()` / `load()` — joblib + JSON config persistence

#### Not implemented:
- No training data loaded from BigQuery
- No model trained or saved to `models/`
- Hyperparameter Tuning
 [ ] Use Optuna or RandomizedSearchCV
 [ ] Key hyperparameters for LightGBM:
  - `num_leaves`: [31, 50, 100]
  - `learning_rate`: [0.01, 0.05, 0.1]
  - `n_estimators`: [100, 500, 1000]
  - `min_child_samples`: [20, 50, 100]
 [ ] Log all experiments to `ml/experiments/`

#### [Concept] Evaluation
- [ ] Implement evaluation suite:
  ```python
  def evaluate_regression(y_true, y_pred) -> Dict[str, float]:
      return {
          "rmse": np.sqrt(mean_squared_error(y_true, y_pred)),
          "mae": mean_absolute_error(y_true, y_pred),
          "r2": r2_score(y_true, y_pred),
          "mape": mean_absolute_percentage_error(y_true, y_pred),
      }
  ```
- [ ] Create residual plots
- [ ] Analyze errors by salary range and job type

Target metrics: 
- RMSE < $1,500 SGD
- MAE < $1,000 SGD
- R² > 0.7


> ### 1.3.2: Job Clustering (Unsupervised)

File: `ml/clustering.py`

#### Implemented skeleton:
- `JobClusterer` with KMeans (elbow method support)
- `_generate_cluster_labels()` — keyword extraction from job titles
- `analyze_clusters()` — per-cluster salary stats, top locations
- `find_optimal_clusters()` — inertia sweep across k range
- `reduce_dimensions()` — PCA and UMAP support
- `save()` / `load()` persistence

#### [Concept] Dimensionality Reduction
- [ ] Implement PCA for feature reduction
- [ ] Implement UMAP for visualization
- [ ] Create 2D/3D scatter plots with cluster colors

#### [Concept] Cluster Analysis
- [ ] Generate cluster summaries:
  - Cluster size distribution
  - Average salary per cluster
  - Top job titles per cluster
  - Top companies per cluster
- [ ] Name clusters (e.g., "Tech/Software", "Finance/Banking", "Healthcare")

#### [Concept] Evaluation
Target metrics: 
- Silhouette Score > 0.3
- balanced cluster sizes (no cluster < 5% of data)

> ### 1.3.3: Job Role Classification (Multi-class)

#### Implemented skeleton:
- ?

#### Not implemented:
- ?

### [Concept] Classification Pipeline
- [ ] Create `ml/role_classifier.py`:
  ```python
  class RoleClassifier:
      def __init__(self, model_type: str = "lightgbm")
      def train(self, X: pd.DataFrame, y: pd.Series) -> None
      def predict(self, X: pd.DataFrame) -> np.ndarray
      def predict_proba(self, X: pd.DataFrame) -> np.ndarray
      def evaluate(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, float]
  ```
- [ ] Handle class imbalance (SMOTE or class weights)
- [ ] Implement top-k accuracy for multi-class

### [Concept] Evaluation Metrics
- [ ] Implement classification metrics:
  ```python
  def evaluate_classification(y_true, y_pred) -> Dict[str, float]:
      return {
          "accuracy": accuracy_score(y_true, y_pred),
          "f1_macro": f1_score(y_true, y_pred, average='macro'),
          "f1_weighted": f1_score(y_true, y_pred, average='weighted'),
      }
  ```
- [ ] Create confusion matrix visualization
- [ ] Per-class precision/recall analysis

Target Metrics:
- F1 Macro: > 0.6
- Top-3 Accuracy: > 0.85

---

## 1.4: [Concept] Model Artifacts & Deployment

Goal: Save, version, and deploy trained models.

### 1.4.1: Model Serialization

#### Task 1.4.1: Model Registry Structure
- [ ] Create directory structure:
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
- [ ] Implement `ml/registry.py`:
  ```python
  def save_model(model, name: str, version: str, metrics: Dict) -> Path
  def load_model(name: str, version: str = "latest") -> Any
  def list_models() -> List[Dict]
  def get_model_metrics(name: str, version: str) -> Dict
  ```

#### Task 1.4.2: GCS Upload
- [ ] Upload models to GCS: `gs://sg-job-market-data/models/`
- [ ] Implement model download for inference
- [ ] Version management (keep last 5 versions)

### 1.4.2: Batch Predictions

#### Task 1.4.2.1: Prediction Pipeline
- [ ] Create `ml/predict.py`:
  ```python
  def predict_salary_batch(job_ids: List[str]) -> Dict[str, float]
  def predict_cluster_batch(job_ids: List[str]) -> Dict[str, int]
  def predict_all_new_jobs() -> Dict[str, Any]
  ```
- [ ] Write predictions to BigQuery `ml_predictions` table
- [ ] Schedule daily predictions (Cloud Scheduler → Cloud Function)

#### Task 1.4.2.2: BigQuery Predictions Table
- [ ] Create schema:
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

## Resumption Checklist
- Update here on latest progress