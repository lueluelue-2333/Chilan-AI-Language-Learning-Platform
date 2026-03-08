import os
import time
import re
import numpy as np
import google.generativeai as genai
from dotenv import load_dotenv

# 初始化
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.0-flash')

# 测试数据
USER_INPUT = "I have a pen."
STD_ANSWER = "I have a pen."
QUESTION = "我有一支笔。"

def test_regex():
    start = time.perf_counter()
    # 模拟常见的正则清洗：去空格、去标点、转小写
    clean_text = re.sub(r'[^\w\s]', '', USER_INPUT).strip().lower()
    is_match = clean_text == re.sub(r'[^\w\s]', '', STD_ANSWER).strip().lower()
    end = time.perf_counter()
    return (end - start) * 1000  # 转换为毫秒

def test_vector():
    start = time.perf_counter()
    # 1. 生成向量 (API 调用)
    res = genai.embed_content(
        model="models/gemini-embedding-001",
        content=USER_INPUT,
        task_type="semantic_similarity"
    )
    vec = res['embedding']
    
    # 2. 模拟余弦相似度计算 (本地计算)
    # 实际项目中这步在数据库完成，耗时极短
    vec_a = np.array(vec)
    vec_b = np.array(vec) # 模拟对比
    similarity = np.dot(vec_a, vec_b) / (np.linalg.norm(vec_a) * np.linalg.norm(vec_b))
    
    end = time.perf_counter()
    return (end - start) * 1000

def test_llm():
    start = time.perf_counter()
    prompt = f"Evaluate translation. Question: {QUESTION}, Standard: {STD_ANSWER}, Student: {USER_INPUT}. Return JSON."
    response = model.generate_content(prompt)
    _ = response.text
    end = time.perf_counter()
    return (end - start) * 1000

def run_benchmark():
    print(f"--- 🚀 2026 判题流水线性能测试 (输入: '{USER_INPUT}') ---")
    
    # 正则测试 (跑 1000 次取平均)
    reg_times = [test_regex() for _ in range(1000)]
    avg_reg = sum(reg_times) / len(reg_times)
    print(f"1. [正则匹配] 平均耗时: {avg_reg:.4f} ms")

    # 向量测试 (由于涉及 API，跑 5 次取平均)
    print("正在测试向量生成 (API)...")
    vec_times = [test_vector() for _ in range(5)]
    avg_vec = sum(vec_times) / len(vec_times)
    print(f"2. [向量比对] 平均耗时: {avg_vec:.2f} ms")

    # LLM 测试 (由于涉及生成，跑 3 次取平均)
    print("正在测试 LLM 生成 (API)...")
    llm_times = [test_llm() for _ in range(3)]
    avg_llm = sum(llm_times) / len(llm_times)
    print(f"3. [LLM 判题] 平均耗时: {avg_llm:.2f} ms")

if __name__ == "__main__":
    run_benchmark()