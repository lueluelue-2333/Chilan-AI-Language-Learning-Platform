import os
import psycopg2
import google.generativeai as genai
from dotenv import load_dotenv

# 1. 加载 .env 文件
load_dotenv()

def check_postgres():
    print("--- 正在检查 PostgreSQL 连接 ---")
    try:
        conn_url = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(conn_url)
        cur = conn.cursor()
        cur.execute("SELECT version();")
        db_version = cur.fetchone()
        print(f"✅ 数据库连接成功！")
        print(f"   版本信息: {db_version[0]}")
        
        # 顺便检查 pgvector
        cur.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector';")
        vector_version = cur.fetchone()
        if vector_version:
            print(f"✅ pgvector 扩展已就绪 (版本: {vector_version[0]})")
        else:
            print("❌ pgvector 扩展未在当前数据库中激活。")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")

def check_gemini():
    print("\n--- 正在检查 Gemini API 连接 ---")
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ 未在 .env 中找到 GEMINI_API_KEY")
            return
            
        genai.configure(api_key=api_key)

        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # 尝试一个简单的生成请求
        response = model.generate_content("Hello, can you hear me? Just reply with 'OK'.")
        print(f"✅ Gemini API 响应成功！")
        print(f"   AI 回复: {response.text.strip()}")
    except Exception as e:
        print(f"❌ Gemini API 调用失败: {e}")

if __name__ == "__main__":
    check_postgres()
    check_gemini()