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

# 导入您的海量版测试用例
from test_cases import test_suites

# ================= 模式选择 =================
EVAL_MODE = "English_Evaluation" 
# ==========================================

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# --- API 配置 (严格遵循您提供的最新 Key) ---
OPENAI_API_KEY = "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"
GEMINI_API_KEY = "AIzaSyC52mIfJoYD8eoMS2DdY43BanE2jc2bp3w"
ZHIPUAI_API_KEY = "8b6f34f2c0984d50b169c2e71dd4c51f.AIXzag6846gJqwfB"
VOYAGE_API_KEY = "pa-Cn7qC8lQgj61S5kRBgXRY4Pd4WFJ0rS6B7xUA-PzKTK"

# --- 逻辑门阈值设置 (建议根据后续 Excel 结果微调) ---
# 只有高于此分的模型才认为该维度“通过”
THRESHOLDS = {
    "OA-Large": 0.88,
    "Gemini": 0.85,
    "ZP-3": 0.86,
    "Voyage-4": 0.82
}

MODELS = {
    "OA-Large": "text-embedding-3-large",
    "Gemini": "gemini-embedding-001",
    "ZP-3": "embedding-3",
    "Voyage-4": "voyage-4-large"
}

# 初始化
client_oa = OpenAI(api_key=OPENAI_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)
client_zp = ZhipuAiClient(api_key=ZHIPUAI_API_KEY)
client_vo = voyageai.Client(api_key=VOYAGE_API_KEY)

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
            return client_vo.embed([text], model=name, output_dimension=2048).embeddings[0]
    except: return None

def apply_logic_gate(row):
    """
    逻辑门核心算法：
    1. 判断每个模型是否超过自身阈值
    2. 计算加权综合分
    """
    gate_results = {}
    passed_count = 0
    
    for tag in MODELS.keys():
        is_pass = row[tag] >= THRESHOLDS[tag]
        gate_results[f"{tag}_Pass"] = is_pass
        if is_pass: passed_count += 1
    
    # 判定：全票通过才算真正通过
    row['Logic_Gate_Pass'] = "✅ PASS" if passed_count == 4 else "❌ FAIL"
    row['Confidence_Level'] = f"{passed_count}/4"
    
    # 综合共识分 (Consensus Score)
    row['Consensus_Score'] = round(np.mean([row[t] for t in MODELS.keys()]), 4)
    
    return row

def run_logic_analysis():
    print(f"🚀 正在执行四模型逻辑门检验: [{EVAL_MODE}]")
    suite = test_suites[EVAL_MODE]
    data_list = []
    
    for title, content in suite.items():
        std_txt = content["standard"]
        std_vecs = {tag: get_embedding(std_txt, tag) for tag in MODELS}
        
        for test_txt, human_grade in content["cases"]:
            row = {"题目": title, "标准答案": std_txt, "学生答案": test_txt, "人工评分": human_grade}
            for tag in MODELS:
                t_vec = get_embedding(test_txt, tag)
                if std_vecs[tag] and t_vec:
                    row[tag] = round(float(cosine_similarity([std_vecs[tag]], [t_vec])[0][0]), 4)
            data_list.append(row)

    df = pd.DataFrame(data_list)
    # 应用逻辑门校验
    df = df.apply(apply_logic_gate, axis=1)

    # 导出 Excel
    filename = f"LogicGate_Report_{EVAL_MODE}_{datetime.datetime.now().strftime('%H%M')}.xlsx"
    df.to_excel(filename, index=False)
    print(f"✅ 逻辑门报告已生成: {filename}")

    # 打印逻辑门拦截统计
    print("\n--- 逻辑门拦截统计 (4/4 代表全模型通过) ---")
    print(df['Confidence_Level'].value_counts().sort_index(ascending=False))

    plot_gate_results(df)

def plot_gate_results(df):
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False
    
    plt.figure(figsize=(14, 7))
    
    # 绘制共识分与人工评分的对比散点图
    sns.scatterplot(data=df, x='人工评分', y='Consensus_Score', hue='Logic_Gate_Pass', 
                    style='Logic_Gate_Pass', s=100, palette={'✅ PASS': 'g', '❌ FAIL': 'r'})
    
    plt.axhline(y=0.85, color='gray', linestyle='--', alpha=0.5, label="共识及格线")
    plt.title(f"逻辑门检验分布图 ({EVAL_MODE})\n绿色代表四模型共识通过，红色代表至少有一家模型存疑", fontsize=15)
    plt.xticks([1, 2, 3, 4])
    plt.grid(True, alpha=0.3)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    run_logic_analysis()