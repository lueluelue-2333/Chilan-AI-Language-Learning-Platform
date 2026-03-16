import os
import json
import psycopg2
from psycopg2.extras import Json
from google import genai
from pathlib import Path
from dotenv import load_dotenv

# 🌟 引入你刚刚写的标准数据库连接池
from connection import get_connection

# ==========================================
# 1. 环境与配置初始化
# ==========================================
# 自动定位项目根目录下的 .env 文件
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("❌ 未在 .env 中找到 GEMINI_API_KEY")

# 初始化大模型客户端 (推荐使用最新的多语言 embedding 模型)
client = genai.Client(api_key=GEMINI_API_KEY)
EMBEDDING_MODEL = "gemini-embedding-001" 

def get_embedding(text: str) -> list[float]:
    """调用 Gemini 接口生成 3072 维向量"""
    print(f"🧠 正在请求大模型生成向量: '{text[:15]}...'")
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
    )
    return response.embeddings[0].values

# ==========================================
# 2. 核心入库逻辑
# ==========================================
def sync_lesson_data(json_file_path: str):
    # 读取 Agent 生成的完美 JSON 文件
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    lesson_metadata = data.get("lesson_metadata", {})
    course_content = data.get("course_content", {})
    database_items = data.get("database_items", [])

    if not lesson_metadata or not database_items:
        print("❌ JSON 数据不完整，缺少 metadata 或 database_items！")
        return

    # 提取 metadata 变量
    course_id = lesson_metadata.get("course_id")
    lesson_id = lesson_metadata.get("lesson_id")
    title = lesson_metadata.get("title")

    conn = None
    cur = None
    
    try:
        # 🌟 直接使用你封装的数据库连接函数！
        conn = get_connection()
        cur = conn.cursor()
        print("✅ 成功通过 connection.py 连接到 PostgreSQL 数据库！\n")

        # ---------------------------------------------------------
        # 任务一：同步 `lessons` 表 (写入 JSONB 课件数据)
        # ---------------------------------------------------------
        print(f"📦 正在同步 Lesson {lesson_id} 基础课件数据...")
        
        # 检查是否已存在该课
        cur.execute("SELECT 1 FROM lessons WHERE course_id = %s AND lesson_id = %s", (course_id, lesson_id))
        if cur.fetchone():
            # 已存在，执行更新 (利用 psycopg2.extras.Json 自动处理 dict 到 JSONB 的转换)
            cur.execute("""
                UPDATE lessons 
                SET title = %s, structured_content = %s
                WHERE course_id = %s AND lesson_id = %s
            """, (title, Json(course_content), course_id, lesson_id))
            print(f"   -> 🔄 更新了已存在的 Lesson {lesson_id} 数据。")
        else:
            # 不存在，执行插入
            cur.execute("""
                INSERT INTO lessons (course_id, lesson_id, title, structured_content)
                VALUES (%s, %s, %s, %s)
            """, (course_id, lesson_id, title, Json(course_content)))
            print(f"   -> 🆕 插入了全新的 Lesson {lesson_id} 数据。")


        # ---------------------------------------------------------
        # 任务二：同步 `language_items` 表 (生成向量并写入题库)
        # ---------------------------------------------------------
        print("\n🎯 开始同步题库并生成 Embedding 向量...")
        success_count = 0

        for item in database_items:
            q_id = item['question_id']
            q_type = item['question_type']
            q_text = item['original_text']
            s_answers = item['standard_answers'] # 这是一个数组
            
            # 生成向量 (取第一个标准答案作为基准)
            primary_embedding = get_embedding(s_answers[0])
            embedding_str = str(primary_embedding) # 转换为 PostgreSQL 接受的向量字符串格式

            # 检查题目是否已存在
            cur.execute("""
                SELECT 1 FROM language_items 
                WHERE course_id = %s AND lesson_id = %s AND question_id = %s
            """, (course_id, lesson_id, q_id))
            
            if cur.fetchone():
                cur.execute("""
                    UPDATE language_items 
                    SET question_type = %s, original_text = %s, standard_answers = %s, primary_embedding = %s
                    WHERE course_id = %s AND lesson_id = %s AND question_id = %s
                """, (q_type, q_text, s_answers, embedding_str, course_id, lesson_id, q_id))
                print(f"   -> 🔄 更新题目 {q_id}: {q_text}")
            else:
                cur.execute("""
                    INSERT INTO language_items 
                    (course_id, lesson_id, question_id, question_type, original_text, standard_answers, primary_embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (course_id, lesson_id, q_id, q_type, q_text, s_answers, embedding_str))
                print(f"   -> 🆕 插入题目 {q_id}: {q_text}")
            
            success_count += 1

        # 完美运行，提交所有事务！
        conn.commit()
        print(f"\n🎉 大功告成！课件本体和 {success_count} 道向量题库全部落盘！")

    except Exception as e:
        print(f"\n❌ 数据库操作失败，已回滚: {e}")
        if conn: conn.rollback()
    finally:
        if cur: cur.close()
        if conn: conn.close()

if __name__ == "__main__":
    # 使用 pathlib 优雅地定位跨文件夹的 JSON 路径
    current_dir = Path(__file__).resolve().parent
    target_json = current_dir.parent / "content_builder" / "output_json" / "lesson1_data.json"
    
    if target_json.exists():
        print(f"🔍 成功找到数据文件: {target_json}")
        sync_lesson_data(str(target_json))
    else:
        print(f"❌ 找不到文件，请检查路径: {target_json}")