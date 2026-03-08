import sys
from pathlib import Path
from datetime import datetime

# 将根目录注入路径，确保 import database 有效
root = str(Path(__file__).resolve().parent.parent)
if root not in sys.path: sys.path.append(root)

from database.connection import get_connection

def init_user_progress(u_id: int, q_id: int):
    conn = get_connection()
    try:
        cur = conn.cursor()
        
        # 1. 确保测试用户存在 (解决外键报错)
        cur.execute("""
            INSERT INTO users (user_id, username, email, password_hash) 
            VALUES (%s, %s, %s, 'dummy_hash') ON CONFLICT DO NOTHING;
        """, (u_id, f"test_user_{u_id}", f"user{u_id}@test.com"))
        
        # 2. 插入初始化进度
        cur.execute("""
            INSERT INTO user_progress (user_id, question_id, stability, difficulty, next_review)
            VALUES (%s, %s, 0.5, 5.0, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id, question_id) DO NOTHING;
        """, (u_id, q_id))
        
        conn.commit()
        print(f"✅ 已成功为用户 {u_id} 激活题目 {q_id} 的练习状态。")
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    # 测试运行：初始化用户 1 对题目 1 的进度
    init_user_progress(u_id=1, q_id=1)