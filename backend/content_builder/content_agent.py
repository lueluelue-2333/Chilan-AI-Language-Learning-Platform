import os
import json
import time
from pathlib import Path
from google import genai
from dotenv import load_dotenv

# 1. 自动化路径处理：精准定位到 backend/.env
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
        
        # 锁定模型
        self.model_id = "gemini-3.1-pro-preview" 

    # 🌟 修改点 1：去掉了 async，改为纯同步函数
    def parse_textbook(self, file_path: str):
        """
        核心逻辑：解析教材 PDF 并生成结构化 JSON 数据
        """
        print(f"🚀 正在上传并解析教材: {file_path}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"❌ 错误：找不到文件 {file_path}")

        # 1. 上传 PDF 文件
        with open(file_path, "rb") as f:
            sample_file = self.client.files.upload(
                file=f,
                config={'mime_type': 'application/pdf'}
            )
        
        # 2. 等待云端处理 PDF
        print("⏳ 系统正在理解教材版式...", end="", flush=True)
        # 🌟 此处的 time.sleep(2) 在同步函数里是非常正确的
        while sample_file.state == "PROCESSING":
            print(".", end="", flush=True)
            time.sleep(2)
            sample_file = self.client.files.get(name=sample_file.name)

        if sample_file.state == "FAILED":
            raise Exception("❌ 教材上传处理失败，请检查 API 状态。")

        # 3. Prompt (保持你优秀的防弹 Prompt 不变)
        prompt = """
        你是一名资深的对外汉语专家和数据工程师。请解析提供的教材 PDF，并严格按照要求提取内容，最终只输出一个合法的 JSON，不要包含任何额外的 Markdown 标记（如 ```json）。

        【核心解析规则】
        1. **lesson_metadata**:
            - course_id: 1（英文学中文固定为1）
            - lesson_id: 1
            - title: 这一课程的标题，例如 "Lesson 1: Greetings"

        2. **course_content** (前端展示数据):
            - dialogues: 按照原文顺序提取课文内容，保留加粗生词使用 <b>生词</b> 标签，并标注拼音。
            - vocabulary: 提取单词、拼音、词性、英文定义和一例句。

        3. **database_items** (题库数据，严格对齐 PostgreSQL 表结构):
            - 生成用于复习翻译的题目，必须覆盖基础核心词汇和课文重点句子。
            - 既要包括刚刚生成的vocabulary对应的的中译英、英译中的题目，也要包括很重要的句子的翻译。
            - 同时你还要对题目进行一定的处理，要保证给用户的题目都是高质量，有普适价值的，比如一些人名相关的题目就可以剔除。
            - course_id & lesson_id: 必须与 metadata 中保持一致。
            - question_id: 从 1 开始递增的整数。
            - question_type: 严格只能是 "CN_TO_EN" (中译英) 或 "EN_TO_CN" (英译中)。
            - original_text: 题干文本。
            - standard_answers: **必须是数组（List/Array）**，即使只有一个答案也必须包裹在数组中。

        4. **aigc_visual_prompt**: 为本课生成一段 Midjourney 英文提示词，用于生成课程封面。

        【强制输出结构】
        请严格照抄以下 JSON 格式进行输出，绝不允许修改字段名或破坏层级结构：
        {
        "lesson_metadata": {
            "course_id": 1 (固定为1),
            "lesson_id": 1 (从1开始递增),
            "title": "Lesson 1: Greetings"
        },
        "course_content": {
            "dialogues": [
            {
                "lines": [
                {   
                    "role": "角色名",
                    "chinese": "<b>包含</b>高亮的中文",
                    "pinyin": "bāo hán",
                    "english": "English translation"
                }
                ]
            }
            ],
            "vocabulary": [
            {
                "word": "单词",
                "pinyin": "dān cí",
                "part_of_speech": "n",
                "definition": "word",
                "example_sentence": "这是一个例句。(This is an example sentence.)"
            }
            ]
        },
        "database_items": [
            {
            "lesson_id": 1,
            "question_id": 1,
            "course_id": 1,
            "question_type": "CN_TO_EN",
            "original_text": "你好",
            "standard_answers": ["Hello", "Hi"]
            }
        ],
        "aigc_visual_prompt": "..."
        }
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

# 🌟 修改点 2：去掉 async main
def main():
    agent = ContentCreatorAgent()
    
    current_dir = Path(__file__).resolve().parent
    pdf_path = current_dir / "raw_materials" / "lesson1.pdf"
    
    if pdf_path.exists():
        # 🌟 修改点 3：直接调用，不需要 await
        result = agent.parse_textbook(str(pdf_path))
        if result:
            output_file = current_dir / "output_json" / "lesson1_data.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n✅ 解析成功！数据已保存至: {output_file}")
    else:
        print(f"\n❌ 错误：在路径 {current_dir} 下未找到 lesson1.pdf")

if __name__ == "__main__":
    # 🌟 修改点 4：直接执行 main
    main()