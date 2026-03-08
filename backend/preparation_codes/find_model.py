import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

print("--- 你可以使用的向量模型列表 ---")
for m in genai.list_models():
    if 'embedContent' in m.supported_generation_methods:
        print(f"模型名称: {m.name}")