import uuid
from datetime import datetime, timedelta
from database.connection import get_connection

# --- 配置区 ---
# 请填入你登录后的真实 UUID
USER_ID = "2eb6323c-a2a8-4656-8386-632bd06a3e6d" 
# 假设你数据库里已经有了 ID 为 1, 2, 3, 4, 5 的题目
TEST_QUESTIONS = [1, 2, 3, 4] 

def seed_data():
    conn = get_connection()
    cur = conn.cursor()
    try:
        print(f"开始为用户 {USER_ID} 注入测试数据...")

        # 1. 注入 3 条“待复习”数据 (next_review 设为过去的时间)
        for q_id in TEST_QUESTIONS[:3]:
            cur.execute("""
                INSERT INTO user_progress (user_id, question_id, stability, difficulty, state, next_review)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (user_id, question_id) DO NOTHING;
            """, (USER_ID, q_id, 2.0, 4.5, 2, datetime.now() - timedelta(days=1)))

        # 2. 注入 2 条“今日已复习”的流水账到 review_logs
        # 这会让教室页面的 "Total Reviewed" 显示为 2
        for q_id in TEST_QUESTIONS[3:5]:
            # 先确保进度表里有这两题（状态设为已复习）
            cur.execute("""
                INSERT INTO user_progress (user_id, question_id, stability, difficulty, state, last_review, next_review)
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + interval '3 days')
                ON CONFLICT (user_id, question_id) DO NOTHING;
            """, (USER_ID, q_id, 5.0, 3.0, 2))

            # 写入日志
            cur.execute("""
                INSERT INTO review_logs (user_id, question_id, rating, state, stability, difficulty, review_time)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP);
            """, (USER_ID, q_id, 3, 2, 5.0, 3.0))

        conn.commit()
        print("✅ 测试数据注入成功！现在去刷新教室页面看看吧。")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ 注入失败: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    seed_data()