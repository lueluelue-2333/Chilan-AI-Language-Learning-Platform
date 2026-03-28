# -*- coding: utf-8 -*-
import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI
import google.generativeai as genai
from zai import ZhipuAiClient
import voyageai
import datetime

# 导入测试用例
try:
    from test_cases import test_suites
except ImportError:
    print("❌ 错误：请确保同目录下存在 test_cases.py 文件")
    sys.exit(1)

# 强制 UTF-8 环境
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ================= 配置区 =================
OPENAI_API_KEY = "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"
GEMINI_API_KEY = "AIzaSyC52mIfJoYD8eoMS2DdY43BanE2jc2bp3w"
ZHIPUAI_API_KEY = "8b6f34f2c0984d50b169c2e71dd4c51f.AIXzag6846gJqwfB"
VOYAGE_API_KEY = "pa-Cn7qC8lQgj61S5kRBgXRY4Pd4WFJ0rS6B7xUA-PzKTK"
DEEPSEEK_API_KEY = "sk-02cff5ac1c364489bccf386fd504b052"

# 定义评测模型矩阵
MODELS = {
    "OA-Large": "text-embedding-3-large",
    "Gemini": "gemini-embedding-001",
    "ZP-3": "embedding-3",
    "Voyage-4": "voyage-4-large",
    "DeepSeek": "deepseek-embedding"  # 新增 DeepSeek 模型
}

# 初始化所有客户端
client_oa = OpenAI(api_key=OPENAI_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)
client_zp = ZhipuAiClient(api_key=ZHIPUAI_API_KEY)
client_vo = voyageai.Client(api_key=VOYAGE_API_KEY)
# DeepSeek 专用客户端 (兼容 OpenAI 格式)
client_ds = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

def get_embedding(text, model_tag):
    try:
        name = MODELS[model_tag]
        if "OA" in model_tag:
            return client_oa.embeddings.create(input=[text], model=name).data[0].embedding
        elif "Gemini" in model_tag:
            m_path = f"models/{name}" if not name.startswith("models/") else name
            return genai.embed_content(model=m_path, content=text, task_type="similarity")['embedding']
        elif "ZP" in model_tag:
            return client_zp.embeddings.create(model=name, input=[text]).data[0].embedding
        elif "Voyage" in model_tag:
            # Voyage 4 指定 2048 维度
            resp = client_vo.embed([text], model=name, output_dimension=2048)
            return resp.embeddings[0]
        elif "DeepSeek" in model_tag:
            # 调用 DeepSeek 嵌入接口
            return client_ds.embeddings.create(input=[text], model=name).data[0].embedding
    except Exception as e:
        # print(f"获取 {model_tag} 失败: {e}") 
        print(f"⚠️ 获取 {model_tag} 失败! 错误信息: {e}")
        return None

def run_analysis():
    # 循环跑：中译英(English_Evaluation) 和 英译中(Chinese_Evaluation)
    all_dfs = []
    modes = ["English_Evaluation", "Chinese_Evaluation"]
    
    for mode in modes:
        print(f"\n🔍 正在开始 [{mode}] 维度的五路模型深度对比...")
        suite = test_suites[mode]
        results = []
        
        for title, data in suite.items():
            std_txt = data["standard"]
            # 预抓取各家标准答案向量
            std_vecs = {tag: get_embedding(std_txt, tag) for tag in MODELS}
            
            for test_txt, score in data["cases"]:
                row = {"维度": mode, "题目": title, "标准": std_txt, "学生答案": test_txt, "人工评分": score}
                for tag in MODELS:
                    t_vec = get_embedding(test_txt, tag)
                    if std_vecs[tag] and t_vec:
                        sim = cosine_similarity([std_vecs[tag]], [t_vec])[0][0]
                        row[tag] = round(float(sim), 4)
                results.append(row)
        
        df_mode = pd.DataFrame(results)
        all_dfs.append(df_mode)
        
        # 实时生成五路对比图
        plot_model_ranges(df_mode, mode)

    # 汇总导出 Excel
    full_df = pd.concat(all_dfs)
    timestamp = datetime.datetime.now().strftime("%m%d_%H%M")
    filename = f"Full_5Models_Report_{timestamp}.xlsx"
    full_df.to_excel(filename, index=False)
    print(f"\n✅ 全量评测圆满完成！报告已生成: {os.path.abspath(filename)}")

def plot_model_ranges(df, mode):
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 修改为 1行5列，适应 DeepSeek
    fig, axes = plt.subplots(1, 5, figsize=(30, 8), sharey=True)

    for i, tag in enumerate(MODELS.keys()):
        ax = axes[i]
        # 1. 绘制散点
        sns.stripplot(ax=ax, data=df, x='人工评分', y=tag, hue='人工评分', 
                      palette="viridis", size=7, jitter=0.2, alpha=0.5, legend=False)
        
        # 2. 计算区间统计
        stats = df.groupby('人工评分')[tag].agg(['min', 'max', 'mean']).reset_index()
        
        for _, row in stats.iterrows():
            grade = row['人工评分']
            g_min, g_max, g_mean = row['min'], row['max'], row['mean']
            
            # 绘制垂直区间线
            ax.vlines(x=grade-1, ymin=g_min, ymax=g_max, color='black', linewidth=2.5, alpha=0.7)
            ax.hlines(y=[g_min, g_max], xmin=grade-1.1, xmax=grade-0.9, color='black', linewidth=2.5)
            
            # 标注 Max/Min 值
            ax.text(grade-1.15, g_max, f'Max:{g_max:.3f}', ha='right', va='center', fontsize=9, color='#d62728', fontweight='bold')
            ax.text(grade-1.15, g_min, f'Min:{g_min:.3f}', ha='right', va='center', fontsize=9, color='#1f77b4', fontweight='bold')
            # 标注平均分
            ax.plot(grade-1, g_mean, marker='D', color='white', markeredgecolor='black', markersize=7)

        ax.set_title(f"模型: {tag}", fontsize=15, fontweight='bold')
        ax.set_xticks([0, 1, 2, 3])
        ax.set_xticklabels(['1分(错)', '2分', '3分', '4分'])
        ax.grid(axis='y', linestyle='--', alpha=0.3)

    plt.suptitle(f"五路语义边界压力测试 (OpenAI/Gemini/智谱/Voyage/DeepSeek) - {mode}\n(Gap 越大代表模型区分度越好，推荐关注 1 分 Max 与 4 分 Min 的间距)", fontsize=22, y=1.05)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    run_analysis()