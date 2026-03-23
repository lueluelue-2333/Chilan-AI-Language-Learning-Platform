# backend/preparation_codes/listmodel.py
import os
from pathlib import Path
from google import genai
from dotenv import load_dotenv

# 1. 精确加载 .env
base_dir = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=base_dir / ".env")

api_key = os.getenv("GEMINI_API_KEY")
print(f"--- 调试信息 ---")
print(f"API Key 加载成功: {api_key is not None}")

if not api_key:
    print("❌ 错误：请检查 .env 是否在 backend 目录下，且包含 GEMINI_API_KEY")
else:
    # 2. 使用新版客户端
    client = genai.Client(api_key=api_key)
    print("--- 正在获取可用模型列表 ---")
    try:
        # 列出所有可用模型
        for m in client.models.list():
            print(f"✅ 可用模型: {m.name}")
    except Exception as e:
        print(f"❌ 获取失败: {e}")