import os
import psycopg2
import google.generativeai as genai
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
DB_URL = os.getenv("DATABASE_URL")

def get_embedding(text: str):
    """调用 Gemini 模型生成 3072 维语义向量"""
    result = genai.embed_content(
        model="models/gemini-embedding-001",
        content=text,
        task_type="semantic_similarity"
    )
    return result['embedding']

def add_language_item(question_id: int, question_type: str, original_text: str, standard_answers: list):
    """
    核心功能：向题目表插入数据
    参数:
    1. question_id: 手动指定的题目 ID
    2. question_type: 题型 (如 'CN_TO_EN', 'EN_TO_CN')
    3. original_text: 题目内容 (原句)
    4. standard_answers: 标准答案列表 (数组格式)
    """
    try:
        # 自动化逻辑：提取数组中的第一个答案作为语义基准生成向量
        if not standard_answers:
            print("❌ 错误：标准答案列表不能为空")
            return
        
        print(f"--- 正在自动生成向量: {standard_answers[0]} ---")
        embedding_vector = get_embedding(standard_answers[0])

        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()

        # 执行插入
        sql = """
        INSERT INTO language_items (question_id, question_type, original_text, standard_answers, primary_embedding)
        VALUES (%s, %s, %s, %s, %s::vector)
        ON CONFLICT (question_id) DO UPDATE 
        SET question_type = EXCLUDED.question_type,
            original_text = EXCLUDED.original_text,
            standard_answers = EXCLUDED.standard_answers,
            primary_embedding = EXCLUDED.primary_embedding;
        """
        cur.execute(sql, (question_id, question_type, original_text, standard_answers, embedding_vector))

        conn.commit()
        print(f"✅ 题目 ID {question_id} 已成功入库/更新！")

        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ 插入失败: {e}")

# --- 测试运行 ---
if __name__ == "__main__":
    # 示例：中译英题型，包含多个可能的正确答案
    add_language_item(
        question_id=2,
        question_type="CN_TO_EN",
        original_text="一",
        standard_answers=["one"]
    )
    add_language_item(
        question_id=3,
        question_type="EN_TO_CN",
        original_text="one",
        standard_answers=["一", "壹"]
    )
    add_language_item(
        question_id=4,
        question_type="EN_TO_CN",
        original_text="What do you usually do on weekends?",
        standard_answers=["你通常在周末做什么？", "你平时周末都做些什么？"]
    )