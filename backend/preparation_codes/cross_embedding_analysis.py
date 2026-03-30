# -*- coding: utf-8 -*-
import os
import sys
import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.model_selection import GroupShuffleSplit
from embedding_provider_cache import EmbeddingProviderCache, MODELS, ensure_utf8_stdout


current_file_path = Path(__file__).resolve()

try:
    from test_cases import test_suites
except ImportError:
    print("❌ 错误：请确保同目录下存在 test_cases.py 文件")
    sys.exit(1)

ensure_utf8_stdout()

TRAIN_TEST_RATIO = 0.3
RANDOM_STATE = 42

embedding_service = EmbeddingProviderCache()


def get_embedding(text, model_tag):
    return embedding_service.get_embedding(text, model_tag)


def build_feature_dataframe(eval_mode):
    suite = test_suites[eval_mode]
    rows = []
    total_questions = len(suite)

    print(f"📚 [{eval_mode}] 共 {total_questions} 道题，开始计算五模型相似度...")

    for index, (title, content) in enumerate(suite.items(), start=1):
        print(f"   🧩 [{eval_mode}] 正在处理第 {index}/{total_questions} 题: {title}")
        standard_text = content["standard"]
        print(f"      🔹 正在为标准答案生成五模型向量...")
        standard_vectors = {tag: get_embedding(standard_text, tag) for tag in MODELS}

        total_cases = len(content["cases"])
        for case_index, (test_text, label) in enumerate(content["cases"], start=1):
            print(f"      ✏️ Case {case_index}/{total_cases} | label={label} | answer={test_text[:60]}")
            row = {
                "eval_mode": eval_mode,
                "title": title,
                "standard": standard_text,
                "answer": test_text,
                "label": int(label),
            }
            for tag in MODELS:
                answer_vector = get_embedding(test_text, tag)
                standard_vector = standard_vectors[tag]
                if standard_vector is not None and answer_vector is not None:
                    sim = cosine_similarity([standard_vector], [answer_vector])[0][0]
                    row[tag] = round(float(sim), 6)
                else:
                    row[tag] = np.nan
            rows.append(row)

    df = pd.DataFrame(rows)
    return df.dropna(subset=list(MODELS.keys())).reset_index(drop=True)


def split_train_test(df):
    splitter = GroupShuffleSplit(n_splits=1, test_size=TRAIN_TEST_RATIO, random_state=RANDOM_STATE)
    train_idx, test_idx = next(splitter.split(df, y=df["label"], groups=df["title"]))
    train_df = df.iloc[train_idx].copy()
    test_df = df.iloc[test_idx].copy()
    print(f"✂️ 已完成分组切分: train={len(train_df)} | test={len(test_df)} | train_titles={train_df['title'].nunique()} | test_titles={test_df['title'].nunique()}")
    return train_df, test_df


def train_weighted_model(train_df):
    feature_names = list(MODELS.keys())
    X_train = train_df[feature_names].values
    y_train = train_df["label"].values

    print("🧠 正在训练融合模型 (LogisticRegression)...")
    model = LogisticRegression(random_state=RANDOM_STATE, max_iter=1000)
    model.fit(X_train, y_train)
    print("✅ 融合模型训练完成。")

    weights = dict(zip(feature_names, model.coef_[0]))
    intercept = float(model.intercept_[0])
    train_probs = model.predict_proba(X_train)[:, 1]
    best_threshold, threshold_stats = find_best_threshold(y_train, train_probs)
    visual_threshold = find_visual_threshold(y_train, train_probs)
    train_preds = (train_probs >= best_threshold).astype(int)

    return {
        "model": model,
        "weights": weights,
        "intercept": intercept,
        "best_threshold": best_threshold,
        "visual_threshold": visual_threshold,
        "threshold_train_stats": threshold_stats,
        "train_accuracy": accuracy_score(y_train, train_preds),
        "train_f1": f1_score(y_train, train_preds, zero_division=0),
        "train_auc": roc_auc_score(y_train, train_probs) if len(set(y_train)) > 1 else np.nan,
    }


def find_best_threshold(y_true, probs):
    best = {
        "threshold": 0.5,
        "accuracy": -1.0,
        "f1": -1.0,
        "precision": 0.0,
        "recall": 0.0,
    }

    for threshold in np.arange(0.05, 0.951, 0.005):
        preds = (probs >= threshold).astype(int)
        accuracy = accuracy_score(y_true, preds)
        f1 = f1_score(y_true, preds, zero_division=0)
        precision = precision_score(y_true, preds, zero_division=0)
        recall = recall_score(y_true, preds, zero_division=0)
        if (
            accuracy > best["accuracy"]
            or (accuracy == best["accuracy"] and f1 > best["f1"])
            or (
                accuracy == best["accuracy"]
                and f1 == best["f1"]
                and abs(threshold - 0.5) < abs(best["threshold"] - 0.5)
            )
        ):
            best = {
                "threshold": float(round(threshold, 3)),
                "accuracy": float(accuracy),
                "f1": float(f1),
                "precision": float(precision),
                "recall": float(recall),
            }

    return best["threshold"], best


def find_visual_threshold(y_true, scores):
    y_true = np.asarray(y_true)
    scores = np.asarray(scores)
    neg_scores = scores[y_true == 0]
    pos_scores = scores[y_true == 1]

    if len(neg_scores) == 0 or len(pos_scores) == 0:
        return 0.5

    neg_max = float(np.max(neg_scores))
    pos_min = float(np.min(pos_scores))
    return round((neg_max + pos_min) / 2, 3)


def evaluate_model(fitted_model, test_df, threshold):
    feature_names = list(MODELS.keys())
    X_test = test_df[feature_names].values
    y_test = test_df["label"].values

    print("🧪 正在测试集上评估融合模型...")
    test_probs = fitted_model.predict_proba(X_test)[:, 1]
    test_preds = (test_probs >= threshold).astype(int)

    result_df = test_df.copy()
    result_df["fusion_score"] = test_probs
    result_df["pred_label"] = test_preds
    result_df["result_flag"] = np.where(result_df["pred_label"] == result_df["label"], "✅", "❌")

    metrics = {
        "test_accuracy": accuracy_score(y_test, test_preds),
        "test_precision": precision_score(y_test, test_preds, zero_division=0),
        "test_recall": recall_score(y_test, test_preds, zero_division=0),
        "test_f1": f1_score(y_test, test_preds, zero_division=0),
        "test_auc": roc_auc_score(y_test, test_probs) if len(set(y_test)) > 1 else np.nan,
        "confusion_matrix": confusion_matrix(y_test, test_preds, labels=[0, 1]).tolist(),
        "threshold": threshold,
    }
    return result_df, metrics


def plot_language_results(result_df, eval_mode, weights, intercept, threshold, visual_threshold, test_accuracy):
    plt.rcParams["font.sans-serif"] = ["SimHei", "Arial Unicode MS"]
    plt.rcParams["axes.unicode_minus"] = False

    plot_df = result_df.copy()
    plot_df["label"] = plot_df["label"].astype(str)
    palette = {"0": "#d95f5f", "1": "#4daf7c"}

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    sns.boxplot(
        data=plot_df,
        x="label",
        y="fusion_score",
        ax=axes[0],
        palette=palette,
        order=["0", "1"],
    )
    sns.stripplot(
        data=plot_df,
        x="label",
        y="fusion_score",
        ax=axes[0],
        order=["0", "1"],
        color="#1f1f1f",
        alpha=0.75,
        jitter=0.18,
        size=5,
    )
    axes[0].axhline(threshold, color="#333333", linestyle="--", alpha=0.8, label=f"最佳分界线 = {threshold:.3f}")
    axes[0].axhline(
        visual_threshold,
        color="#1f77b4",
        linestyle=":",
        alpha=0.9,
        label=f"视觉分界线 = {visual_threshold:.3f}",
    )
    axes[0].set_title(f"{eval_mode} 融合分数分布")
    axes[0].set_xlabel("真实标签 (0=错, 1=对)")
    axes[0].set_ylabel("融合得分")
    axes[0].set_xticklabels(["错 (0)", "对 (1)"])
    axes[0].legend(loc="upper left")

    weight_df = pd.DataFrame(
        {"Model": list(weights.keys()), "Weight": list(weights.values())}
    ).sort_values("Weight", ascending=False)
    sns.barplot(data=weight_df, x="Weight", y="Model", ax=axes[1], palette="Blues_r")
    axes[1].set_title(f"{eval_mode} 学到的模型权重")
    axes[1].set_xlabel("系数")
    axes[1].set_ylabel("")
    weight_text = "\n".join(
        [
            f"w_OA = {weights['OA-Large']:.4f}",
            f"w_Gemini = {weights['Gemini']:.4f}",
            f"w_ZP = {weights['ZP-3']:.4f}",
            f"w_Voyage = {weights['Voyage-4']:.4f}",
            f"w_Ali = {weights['Ali']:.4f}",
            f"b = {intercept:.4f}",
            f"最佳阈值 = {threshold:.4f}",
            f"视觉阈值 = {visual_threshold:.4f}",
            f"测试准确率 = {test_accuracy:.4f}",
        ]
    )
    axes[1].text(
        1.02,
        0.02,
        weight_text,
        transform=axes[1].transAxes,
        va="bottom",
        ha="left",
        fontsize=10,
        bbox={"boxstyle": "round", "facecolor": "#f7f7f7", "edgecolor": "#cccccc"},
    )

    plt.tight_layout()
    plt.show()


def run_cross_embedding_analysis():
    print("🛠️ 模型矩阵加载完成 (5模型融合模式):")
    for tag, model_id in MODELS.items():
        print(f"   - {tag}: {model_id}")

    timestamp = datetime.datetime.now().strftime("%m%d_%H%M")
    excel_path = f"CrossEmbedding_Report_{timestamp}.xlsx"

    summary_rows = []

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        for eval_mode in ["English_Evaluation", "Chinese_Evaluation"]:
            print(f"\n🚀 开始分析: {eval_mode}")
            feature_df = build_feature_dataframe(eval_mode)
            if feature_df.empty:
                print(f"⚠️ {eval_mode} 没有可用数据，跳过。")
                continue

            print(f"📦 [{eval_mode}] 特征表构建完成，共 {len(feature_df)} 条样本。")
            train_df, test_df = split_train_test(feature_df)
            train_info = train_weighted_model(train_df)
            result_df, test_metrics = evaluate_model(
                train_info["model"],
                test_df,
                train_info["best_threshold"],
            )

            print(f"\n[{eval_mode}] 学到的权重:")
            print(f"  w_OA = {train_info['weights']['OA-Large']:.6f}")
            print(f"  w_Gemini = {train_info['weights']['Gemini']:.6f}")
            print(f"  w_ZP = {train_info['weights']['ZP-3']:.6f}")
            print(f"  w_Voyage = {train_info['weights']['Voyage-4']:.6f}")
            print(f"  w_Ali = {train_info['weights']['Ali']:.6f}")
            print(f"  b = {train_info['intercept']:.6f}")
            print(f"  best_threshold = {train_info['best_threshold']:.3f}")
            print(f"  visual_threshold = {train_info['visual_threshold']:.3f}")

            print(f"\n[{eval_mode}] 训练集表现:")
            print(f"  Accuracy: {train_info['train_accuracy']:.4f}")
            print(f"  F1: {train_info['train_f1']:.4f}")
            print(f"  AUC: {train_info['train_auc']:.4f}" if not np.isnan(train_info["train_auc"]) else "  AUC: N/A")
            print(f"  Threshold Accuracy: {train_info['threshold_train_stats']['accuracy']:.4f}")
            print(f"  Threshold Precision: {train_info['threshold_train_stats']['precision']:.4f}")
            print(f"  Threshold Recall: {train_info['threshold_train_stats']['recall']:.4f}")

            print(f"\n[{eval_mode}] 测试集表现:")
            print(f"  Best Threshold: {test_metrics['threshold']:.3f}")
            print(f"  Accuracy: {test_metrics['test_accuracy']:.4f}")
            print(f"  Precision: {test_metrics['test_precision']:.4f}")
            print(f"  Recall: {test_metrics['test_recall']:.4f}")
            print(f"  F1: {test_metrics['test_f1']:.4f}")
            print(f"  AUC: {test_metrics['test_auc']:.4f}" if not np.isnan(test_metrics["test_auc"]) else "  AUC: N/A")
            print(f"  Confusion Matrix [ [TN, FP], [FN, TP] ]: {test_metrics['confusion_matrix']}")

            weight_row = {
                "eval_mode": eval_mode,
                "intercept": train_info["intercept"],
                "train_accuracy": train_info["train_accuracy"],
                "train_f1": train_info["train_f1"],
                "train_auc": train_info["train_auc"],
                "best_threshold": train_info["best_threshold"],
                "visual_threshold": train_info["visual_threshold"],
                "test_accuracy": test_metrics["test_accuracy"],
                "test_precision": test_metrics["test_precision"],
                "test_recall": test_metrics["test_recall"],
                "test_f1": test_metrics["test_f1"],
                "test_auc": test_metrics["test_auc"],
            }
            weight_row.update(train_info["weights"])
            summary_rows.append(weight_row)

            feature_df.to_excel(writer, sheet_name=f"{eval_mode[:3]}_features", index=False)
            train_df.to_excel(writer, sheet_name=f"{eval_mode[:3]}_train", index=False)
            result_df.to_excel(writer, sheet_name=f"{eval_mode[:3]}_test", index=False)

            print(f"📈 [{eval_mode}] 正在绘制分析图...")
            plot_language_results(
                result_df,
                eval_mode,
                train_info["weights"],
                train_info["intercept"],
                train_info["best_threshold"],
                train_info["visual_threshold"],
                test_metrics["test_accuracy"],
            )
            print(f"✅ [{eval_mode}] 分析完成。")

        if summary_rows:
            pd.DataFrame(summary_rows).to_excel(writer, sheet_name="summary", index=False)

    embedding_service.flush(force=True)
    embedding_service.print_stats(prefix="📦 [CrossEmbedding]")
    print(f"\n✅ 融合分析报告已生成: {os.path.abspath(excel_path)}")


if __name__ == "__main__":
    run_cross_embedding_analysis()
