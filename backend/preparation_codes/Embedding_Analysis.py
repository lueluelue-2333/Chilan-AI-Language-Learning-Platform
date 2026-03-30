# -*- coding: utf-8 -*-
import os
import sys
import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.metrics.pairwise import cosine_similarity
from embedding_provider_cache import EmbeddingProviderCache, MODELS, ensure_utf8_stdout


current_file_path = Path(__file__).resolve()

try:
    from test_cases import test_suites
except ImportError:
    print("❌ 错误：请确保同目录下存在 test_cases.py 文件")
    sys.exit(1)

ensure_utf8_stdout()

print("🛠️ 模型矩阵加载完成:")
for tag, model_id in MODELS.items():
    print(f"   - {tag}: {model_id}")

embedding_service = EmbeddingProviderCache()


def get_embedding(text, model_tag):
    return embedding_service.get_embedding(text, model_tag)


def find_best_threshold(y_true, scores):
    best = {
        "threshold": 0.5,
        "accuracy": -1.0,
        "f1": -1.0,
        "precision": 0.0,
        "recall": 0.0,
    }

    for threshold in np.arange(0.05, 0.951, 0.005):
        preds = (scores >= threshold).astype(int)
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

    return best


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


def build_mode_dataframe(mode):
    suite = test_suites[mode]
    rows = []
    total_questions = len(suite)
    print(f"\n🔍 开始分析 [{mode}]，共 {total_questions} 道题...")

    for question_index, (title, data) in enumerate(suite.items(), start=1):
        print(f"   🧩 第 {question_index}/{total_questions} 题: {title}")
        standard_text = data["standard"]
        standard_vectors = {tag: get_embedding(standard_text, tag) for tag in MODELS}

        total_cases = len(data["cases"])
        for case_index, (answer_text, label) in enumerate(data["cases"], start=1):
            print(f"      ✏️ Case {case_index}/{total_cases} | label={label} | answer={answer_text[:60]}")
            row = {
                "维度": mode,
                "题目": title,
                "标准": standard_text,
                "学生答案": answer_text,
                "人工评分": int(label),
            }

            for tag in MODELS:
                answer_vector = get_embedding(answer_text, tag)
                standard_vector = standard_vectors[tag]
                if standard_vector is not None and answer_vector is not None:
                    sim = cosine_similarity([standard_vector], [answer_vector])[0][0]
                    row[tag] = round(float(sim), 6)
                else:
                    row[tag] = np.nan
            rows.append(row)

    df_mode = pd.DataFrame(rows)
    return df_mode.dropna(subset=list(MODELS.keys())).reset_index(drop=True)


def summarize_model_performance(df_mode, mode):
    summary_rows = []
    plot_payload = []

    print(f"\n📊 [{mode}] 单模型最佳分界线结果:")
    for tag in MODELS:
        model_df = df_mode[["维度", "题目", "标准", "学生答案", "人工评分", tag]].copy()
        model_df = model_df.rename(columns={tag: "相似度"})
        threshold_stats = find_best_threshold(model_df["人工评分"].values, model_df["相似度"].values)
        visual_threshold = find_visual_threshold(model_df["人工评分"].values, model_df["相似度"].values)
        model_df["pred_label"] = (model_df["相似度"] >= threshold_stats["threshold"]).astype(int)
        model_df["result_flag"] = np.where(model_df["pred_label"] == model_df["人工评分"], "✅", "❌")
        model_df["模型"] = tag
        model_df["最佳阈值"] = threshold_stats["threshold"]
        model_df["视觉阈值"] = visual_threshold
        model_df["准确率"] = threshold_stats["accuracy"]
        model_df["Precision"] = threshold_stats["precision"]
        model_df["Recall"] = threshold_stats["recall"]
        model_df["F1"] = threshold_stats["f1"]

        print(f"   - {tag}")
        print(f"     最佳阈值: {threshold_stats['threshold']:.3f}")
        print(f"     视觉阈值: {visual_threshold:.3f}")
        print(f"     Accuracy: {threshold_stats['accuracy']:.4f}")
        print(f"     Precision: {threshold_stats['precision']:.4f}")
        print(f"     Recall: {threshold_stats['recall']:.4f}")
        print(f"     F1: {threshold_stats['f1']:.4f}")

        summary_rows.append(
            {
                "维度": mode,
                "模型": tag,
                "模型ID": MODELS[tag],
                "最佳阈值": threshold_stats["threshold"],
                "视觉阈值": visual_threshold,
                "准确率": threshold_stats["accuracy"],
                "Precision": threshold_stats["precision"],
                "Recall": threshold_stats["recall"],
                "F1": threshold_stats["f1"],
            }
        )
        plot_payload.append((tag, model_df.copy(), threshold_stats, visual_threshold))

    plot_mode_binary_distribution(mode, plot_payload)
    return pd.DataFrame(summary_rows)


def plot_mode_binary_distribution(mode, plot_payload):
    plt.rcParams["font.sans-serif"] = ["SimHei", "Arial Unicode MS"]
    plt.rcParams["axes.unicode_minus"] = False

    palette = {"0": "#d95f5f", "1": "#4daf7c"}
    fig, axes = plt.subplots(1, len(plot_payload), figsize=(7 * len(plot_payload), 6), sharey=True)
    if len(plot_payload) == 1:
        axes = [axes]

    for ax, (model_tag, model_df, threshold_stats, visual_threshold) in zip(axes, plot_payload):
        plot_df = model_df.copy()
        plot_df["人工评分"] = plot_df["人工评分"].astype(str)
        sns.boxplot(
            data=plot_df,
            x="人工评分",
            y="相似度",
            palette=palette,
            order=["0", "1"],
            ax=ax,
        )
        sns.stripplot(
            data=plot_df,
            x="人工评分",
            y="相似度",
            order=["0", "1"],
            color="#1f1f1f",
            alpha=0.75,
            jitter=0.18,
            size=4.5,
            ax=ax,
        )
        ax.axhline(
            threshold_stats["threshold"],
            color="#333333",
            linestyle="--",
            alpha=0.85,
            label=f"最佳阈值 = {threshold_stats['threshold']:.3f}",
        )
        ax.axhline(
            visual_threshold,
            color="#1f77b4",
            linestyle=":",
            alpha=0.9,
            label=f"视觉阈值 = {visual_threshold:.3f}",
        )
        ax.set_title(f"{model_tag}\n{MODELS[model_tag]}")
        ax.set_xlabel("真实标签")
        ax.set_xticklabels(["错 (0)", "对 (1)"])
        ax.legend(loc="upper left", fontsize=9)

        info_text = "\n".join(
            [
                f"Acc = {threshold_stats['accuracy']:.3f}",
                f"P = {threshold_stats['precision']:.3f}",
                f"R = {threshold_stats['recall']:.3f}",
                f"F1 = {threshold_stats['f1']:.3f}",
            ]
        )
        ax.text(
            0.98,
            0.02,
            info_text,
            transform=ax.transAxes,
            va="bottom",
            ha="right",
            fontsize=9,
            bbox={"boxstyle": "round", "facecolor": "#f7f7f7", "edgecolor": "#cccccc"},
        )

    axes[0].set_ylabel("相似度")
    fig.suptitle(f"{mode} 单模型相似度分布对比", fontsize=18, y=1.02)
    plt.tight_layout()
    plt.show()


def run_analysis():
    mode_dfs = []
    summary_dfs = []
    timestamp = datetime.datetime.now().strftime("%m%d_%H%M")
    excel_path = f"SingleEmbedding_Binary_Report_{timestamp}.xlsx"

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        for mode in ["English_Evaluation", "Chinese_Evaluation"]:
            df_mode = build_mode_dataframe(mode)
            if df_mode.empty:
                print(f"⚠️ [{mode}] 没有可用样本，跳过。")
                continue

            print(f"📦 [{mode}] 特征表构建完成，共 {len(df_mode)} 条样本。")
            summary_df = summarize_model_performance(df_mode, mode)

            mode_dfs.append(df_mode)
            summary_dfs.append(summary_df)

            df_mode.to_excel(writer, sheet_name=f"{mode[:3]}_features", index=False)
            summary_df.to_excel(writer, sheet_name=f"{mode[:3]}_summary", index=False)

        if mode_dfs:
            pd.concat(mode_dfs, ignore_index=True).to_excel(writer, sheet_name="all_features", index=False)
        if summary_dfs:
            pd.concat(summary_dfs, ignore_index=True).to_excel(writer, sheet_name="all_summary", index=False)

    embedding_service.flush(force=True)
    embedding_service.print_stats(prefix="📦 [SingleEmbedding]")
    print(f"\n✅ 单模型二分类评测完成！报告已生成: {os.path.abspath(excel_path)}")


if __name__ == "__main__":
    run_analysis()
