import os
import json
import time
import asyncio
from pathlib import Path
from google import genai
from dotenv import load_dotenv

# 1. 自动化路径处理：确保能精准加载到 backend/.env
# 显式查找根目录下的 .env，避免 ValueError: Missing key inputs
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

class ContentCreatorAgent:
    def __init__(self):
        # 验证 API Key 加载状态
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("❌ 错误：在 .env 文件中未找到 GEMINI_API_KEY。")
        
        # 使用最新的 google-genai SDK
        self.client = genai.Client(api_key=api_key)
        
        # 根据你的 listmodel.py 结果，锁定最稳定的新版模型
        self.model_id = "gemini-2.5-pro" 

    async def parse_textbook(self, file_path: str):
        """
        核心逻辑：解析教材 PDF 并生成结构化 JSON 数据
        """
        print(f"🚀 正在上传并解析教材: {file_path}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"❌ 错误：找不到文件 {file_path}")

        # 1. 上传 PDF 文件并显式指定 MIME 类型
        # 显式指定 'application/pdf' 解决了 Unknown mime type 报错
        with open(file_path, "rb") as f:
            sample_file = self.client.files.upload(
                file=f,
                config={'mime_type': 'application/pdf'}
            )
        
        # 2. 等待云端处理 PDF
        print("⏳ 系统正在理解教材版式...", end="", flush=True)
        while sample_file.state == "PROCESSING":
            print(".", end="", flush=True)
            time.sleep(2)
            sample_file = self.client.files.get(name=sample_file.name)

        if sample_file.state == "FAILED":
            raise Exception("❌ 教材上传处理失败，请检查 API 状态。")

        # 3. 针对 Lesson 1 深度优化的解析提示词
        # 包含对话提取、生词表 和语法总结
        prompt = """
        你是一名资深的对外汉语专家和数据工程师。请解析教材（Lesson 1: Greetings），并输出严格的 JSON。
        输出必须包含以下三个核心模块，且字段名必须与描述一致：

        1. **lesson_metadata**:
           - course_id: 1（如果是用英文学习中文，则固定为1；如果是用中文学习英文，则固定为2。目前我给你的应该都是1）
           - lesson_id: 1
           - title: 这一课程的标题，例如 "Lesson 1: Greetings"

        2. **course_content** (用于前端展示):
           - [cite_start]dialogues: 提取 Dialogue 1 原文 [cite: 14-22, 27-37]。
           - [cite_start]vocabulary: 提取单词、拼音、词性和英文定义 [cite: 64]。

        3. **database_items** (直接对接 language_items 表):
           - 生成题目，每项包含：
             - question_type: 必须只能是 "CN_TO_EN" 或 "EN_TO_CN"。
             - original_text: 需要翻译的文本，如果是"CN_TO_EN"则为中文单个词或句子，如果是"EN_TO_CN"则为英文单个词或句子。
             - standard_answers: 单个正确答案或数组。
           - 题目应该包括词汇的 "CN_TO_EN" 或 "EN_TO_CN" 翻译，以及课文中对话的 "CN_TO_EN" 或 "EN_TO_CN" 翻译，确保覆盖教材核心内容。

        4. **aigc_visual_prompt**:
           - 为本课生成一段 Midjourney 英文提示词。
        """

        # 4. 调用模型生成内容
        response = self.client.models.generate_content(
            model=self.model_id,
            contents=[prompt, sample_file],
            config={
                'response_mime_type': 'application/json',
            }
        )

        try:
            # 5. 解析并返回数据
            structured_data = json.loads(response.text)
            return structured_data
        except Exception as e:
            print(f"\n❌ JSON 解析失败：{e}")
            return None

async def main():
    agent = ContentCreatorAgent()
    
    # 自动定位同目录下的 lesson1.pdf，解决 BadZipFile 和路径问题
    current_dir = Path(__file__).resolve().parent
    pdf_path = current_dir / "lesson1.pdf"
    
    if pdf_path.exists():
        result = await agent.parse_textbook(str(pdf_path))
        if result:
            output_file = current_dir / "lesson1_data.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n✅ 解析成功！数据已保存至: {output_file}")
    else:
        print(f"\n❌ 错误：在路径 {current_dir} 下未找到 lesson1.pdf")

if __name__ == "__main__":
    asyncio.run(main())