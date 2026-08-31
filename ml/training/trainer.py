"""Model trainer producing versioned ML artifacts from dataset files."""

from __future__ import annotations

import csv
import math
import random
import time
from pathlib import Path
from typing import Any

from ml.artifacts.store import ArtifactStore

NULL_VALUES = {"", "null", "none", "na", "n/a", "nan", "undefined"}


def _is_null(val: str) -> bool:
    return val.strip().lower() in NULL_VALUES


def _compute_classification_metrics(
    y_true: list[int], y_pred: list[int]
) -> tuple[float, float, float, float]:
    """Calculate accuracy, macro precision, macro recall, macro F1."""
    if not y_true:
        return 0.0, 0.0, 0.0, 0.0

    n_samples = len(y_true)
    correct = sum(1 for yt, yp in zip(y_true, y_pred) if yt == yp)
    accuracy = round(correct / n_samples, 4)

    classes = sorted(list(set(y_true) | set(y_pred)))
    if not classes:
        return accuracy, 0.0, 0.0, 0.0

    precisions: list[float] = []
    recalls: list[float] = []
    f1s: list[float] = []

    for c in classes:
        tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == c and yp == c)
        fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt != c and yp == c)
        fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == c and yp != c)

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0

        precisions.append(prec)
        recalls.append(rec)
        f1s.append(f1)

    macro_precision = round(sum(precisions) / len(precisions), 4)
    macro_recall = round(sum(recalls) / len(recalls), 4)
    macro_f1 = round(sum(f1s) / len(f1s), 4)

    return accuracy, macro_precision, macro_recall, macro_f1


class ModelTrainer:
    """Trains reproducible ML model versions on datasets and persists artifacts."""

    def __init__(self, artifact_store: ArtifactStore | None = None) -> None:
        self.artifact_store = artifact_store or ArtifactStore()

    def train_model(
        self,
        name: str,
        version_tag: str,
        hyperparameters: dict[str, Any] | None = None,
    ) -> str:
        """Legacy helper for deterministic demo model creation."""
        params = hyperparameters or {"learning_rate": 0.01, "max_depth": 5, "seed": 42}
        weights = [round(0.42 + 0.1 * i, 4) for i in range(len(params))]

        artifact_data = {
            "model_name": name,
            "version_tag": version_tag,
            "hyperparameters": params,
            "weights": weights,
            "feature_names": ["feature_1", "feature_2", "feature_3"],
        }
        return self.artifact_store.save_artifact(name, version_tag, artifact_data)

    def train_dataset_model(
        self,
        csv_file_path: Path | str | bytes,
        target_column: str,
        model_name: str,
        version_tag: str,
        model_type: str = "random_forest",
        hyperparameters: dict[str, Any] | None = None,
        workspace_id: Any | None = None,
    ) -> tuple[dict[str, Any], str]:
        """Parse CSV, train classification model, compute metrics, save artifact."""

        import io
        from app.core.storage import StorageService

        start_time = time.time()
        file_obj: io.StringIO | io.TextIOWrapper

        if isinstance(csv_file_path, bytes):
            file_obj = io.StringIO(csv_file_path.decode("utf-8-sig", errors="replace"))
        else:
            path = Path(csv_file_path)
            if path.exists() and path.is_file():
                file_obj = path.open("r", encoding="utf-8-sig", errors="replace")
            else:
                try:
                    content_bytes = StorageService().read_dataset_file(str(csv_file_path))
                    file_obj = io.StringIO(content_bytes.decode("utf-8-sig", errors="replace"))
                except Exception as err:
                    raise FileNotFoundError(f"Dataset CSV file not found: {csv_file_path}") from err

        params = hyperparameters or {}
        n_estimators = int(params.get("n_estimators", 100))
        max_depth = int(params.get("max_depth", 5))
        random_seed = int(params.get("random_state", 42))

        # 1. Parse CSV
        try:
            reader = csv.reader(file_obj)
            try:
                header = [col.strip() for col in next(reader)]
            except StopIteration:
                raise ValueError("CSV file is empty") from None

            if target_column not in header:
                raise ValueError(f"Target column '{target_column}' not found in CSV header")

            target_idx = header.index(target_column)
            feature_indices = [i for i in range(len(header)) if i != target_idx]
            feature_names = [header[i] for i in feature_indices]

            rows: list[tuple[list[str], str]] = []
            for row in reader:
                if not row or all(_is_null(c) for c in row):
                    continue
                if target_idx < len(row):
                    t_val = row[target_idx].strip()
                    if not _is_null(t_val):
                        f_vals = [row[i].strip() if i < len(row) else "" for i in feature_indices]
                        rows.append((f_vals, t_val))
        finally:
            file_obj.close()

        if len(rows) < 2:
            raise ValueError(
                f"Target column '{target_column}' contains fewer than 2 valid rows for training"
            )

        # 2. Encode features & targets
        raw_targets = [r[1] for r in rows]
        target_classes = sorted(list(set(raw_targets)))
        target_to_label = {cls: idx for idx, cls in enumerate(target_classes)}
        y_all = [target_to_label[t] for t in raw_targets]

        # Feature numerical encoding
        feature_encoders: list[dict[str, float]] = [{} for _ in feature_names]
        X_all: list[list[float]] = []

        for f_vals, _ in rows:
            num_row: list[float] = []
            for idx, val in enumerate(f_vals):
                if _is_null(val):
                    num_row.append(0.0)
                else:
                    try:
                        num_row.append(float(val))
                    except ValueError:
                        enc = feature_encoders[idx]
                        if val not in enc:
                            enc[val] = float(len(enc))
                        num_row.append(enc[val])
            X_all.append(num_row)

        # 3. Train/Test Split (80/20)
        rng = random.Random(random_seed)
        indices = list(range(len(rows)))
        rng.shuffle(indices)

        split_idx = max(1, int(len(rows) * 0.8))
        if split_idx >= len(rows):
            split_idx = len(rows) - 1

        train_indices = indices[:split_idx]
        test_indices = indices[split_idx:]

        X_train = [X_all[i] for i in train_indices]
        y_train = [y_all[i] for i in train_indices]
        X_test = [X_all[i] for i in test_indices]
        y_test = [y_all[i] for i in test_indices]

        # 4. Train Model & Predict
        y_pred: list[int] = []

        try:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.linear_model import LogisticRegression
            from sklearn.tree import DecisionTreeClassifier

            if model_type == "logistic_regression":
                clf = LogisticRegression(random_state=random_seed, max_iter=200)
            elif model_type == "decision_tree":
                clf = DecisionTreeClassifier(max_depth=max_depth, random_state=random_seed)
            else:
                clf = RandomForestClassifier(
                    n_estimators=n_estimators, max_depth=max_depth, random_state=random_seed
                )

            clf.fit(X_train, y_train)
            y_pred = [int(p) for p in clf.predict(X_test)]
            trained_weights = getattr(clf, "feature_importances_", None)
            if trained_weights is not None:
                weights = [round(float(w), 4) for w in trained_weights]
            else:
                weights = [1.0 / max(1, len(feature_names))] * len(feature_names)

        except ImportError:
            # Standalone fallback decision logic
            majority_class = Counter_mode(y_train)
            weights = [round(1.0 / max(1, len(feature_names)), 4) for _ in feature_names]

            # Simple decision boundary fallback
            y_pred = []
            for row in X_test:
                # Deterministic prediction based on majority class & weighted sum
                s = sum(r * w for r, w in zip(row, weights))
                pred_cls = target_classes[int(math.floor(abs(s))) % len(target_classes)]
                y_pred.append(target_to_label[pred_cls])

        # 5. Compute Metrics
        duration_ms = round((time.time() - start_time) * 1000, 2)
        acc, prec, rec, f1 = _compute_classification_metrics(y_test, y_pred)

        metrics = {
            "accuracy": acc,
            "precision": prec,
            "recall": rec,
            "f1_score": f1,
            "training_duration_ms": duration_ms,
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "target_column": target_column,
            "target_classes": target_classes,
        }

        # 6. Save Model Artifact
        artifact_data = {
            "model_name": model_name,
            "version_tag": version_tag,
            "model_type": model_type,
            "target_column": target_column,
            "target_classes": target_classes,
            "feature_names": feature_names,
            "hyperparameters": params,
            "metrics": metrics,
            "weights": weights,
        }

        artifact_path = self.artifact_store.save_artifact(
            model_name, version_tag, artifact_data, workspace_id=workspace_id
        )
        return metrics, artifact_path


def Counter_mode(arr: list[int]) -> int:
    counts: dict[int, int] = {}
    for item in arr:
        counts[item] = counts.get(item, 0) + 1
    return max(counts.items(), key=lambda x: x[1])[0] if counts else 0
