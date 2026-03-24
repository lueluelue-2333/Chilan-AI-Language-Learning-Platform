import os
import json
import time
import re
import shutil
from pathlib import Path
from abc import ABC, abstractmethod
from dotenv import load_dotenv

# --- 基础路径配置 ---
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

# ==========================================
# 第一部分：抽象基类 (接口定义)
# ==========================================
class BaseLLMProvider(ABC):
    """定义所有模型必须实现的标准接口"""
    @abstractmethod
    def generate_structured_json(self, prompt: str, file_path: str) -> dict:
        pass

# ==========================================
# 第二部分：具体模型实现类
# ==========================================

class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model_id: str):
        from google import genai
        self.client = genai.Client(api_key=api_key)
        self.model_id = model_id

    def generate_structured_json(self, prompt: str, file_path: str) -> dict:
        with open(file_path, "rb") as f:
            sample_file = self.client.files.upload(
                file=f,
                config={'mime_type': 'application/pdf'}
            )
        
        while sample_file.state == "PROCESSING":
            time.sleep(2)
            sample_file = self.client.files.get(name=sample_file.name)

        if sample_file.state == "FAILED":
            raise Exception(f"Gemini 处理文件失败: {file_path}")

        response = self.client.models.generate_content(
            model=self.model_id,
            contents=[prompt, sample_file],
            config={
                'response_mime_type': 'application/json',
                'temperature': 0.1,
                'top_p': 0.8
            }
        )
        return json.loads(response.text)


class ClaudeProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model_id: str):
        from anthropic import Anthropic
        self.client = Anthropic(api_key=api_key)
        self.model_id = model_id

    def generate_structured_json(self, prompt: str, file_path: str) -> dict:
        import base64
        
        # Claude 原生支持 PDF 多模态，直接将文件转为 Base64
        with open(file_path, "rb") as f:
            pdf_data = base64.b64encode(f.read()).decode("utf-8")

        response = self.client.messages.create(
            model=self.model_id,
            max_tokens=8192,
            temperature=0.1,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_data
                            }
                        },
                        {
                            "type": "text",
                            "text": f"{prompt}\n\n请严格且仅输出 JSON 格式，不要包含任何 Markdown 标记（如 ```json）。"
                        }
                    ]
                }
            ]
        )

        raw_text = response.content[0].text
        # 清洗可能存在的 Markdown 标记
        clean_text = raw_text.strip().removeprefix("```json").removesuffix("```").strip()
        return json.loads(clean_text)


class DoubaoProvider(BaseLLMProvider):
    def __init__(self, api_key: str, endpoint_id: str):
        from volcenginesdkarkruntime import Ark
        self.client = Ark(api_key=api_key)
        self.endpoint_id = endpoint_id

    def generate_structured_json(self, prompt: str, file_path: str) -> dict:
        import fitz  # 导入刚刚安装的 PyMuPDF
        import base64
        import json

        # 1. 像豆包网站后台一样：把 PDF 的每一页变成高清图片
        base64_images = []
        try:
            pdf_document = fitz.open(file_path)
            # 遍历每一页进行“截图”
            for page_num in range(len(pdf_document)):
                page = pdf_document.load_page(page_num)
                # 矩阵放大两倍 (Matrix(2.0, 2.0))，保证汉字和拼音足够清晰
                pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
                img_data = pix.tobytes("png")
                base64_str = base64.b64encode(img_data).decode("utf-8")
                base64_images.append(base64_str)
        except Exception as e:
            raise Exception(f"本地渲染 PDF 图片失败，请确保安装了 PyMuPDF: {e}")

        # 2. 组装多模态 Prompt (文本 + N张图片)
        content_list = [{"type": "text", "text": prompt}]
        for img_b64 in base64_images:
            content_list.append({
                "type": "image_url",
                "image_url": {
                    # 按照火山引擎多模态 API 的要求拼接 base64 协议头
                    "url": f"data:image/png;base64,{img_b64}"
                }
            })

        # 3. 直接请求 Doubao-Seed-2.0-pro
        response = self.client.chat.completions.create(
            model=self.endpoint_id,
            messages=[
                {"role": "user", "content": content_list}
            ],
            temperature=0.1,
            max_tokens=8192  # 🌟 新增这一行：强制放宽最大输出长度限制
        )
        
        # 4. 清理可能的 Markdown 标记并解析
        raw_text = response.choices[0].message.content
        clean_text = raw_text.strip().removeprefix("```json").removesuffix("```").strip()
        
        try:
            return json.loads(clean_text)
        except json.JSONDecodeError as e:
            raise Exception(f"豆包返回的 JSON 格式有误: {e}\n原始返回: {raw_text[:200]}...")

# ==========================================
# 第三部分：模型工厂 (LLM Factory)
# ==========================================
class LLMFactory:
    """根据配置文件分发具体的模型 Provider"""
    @staticmethod
    def create_provider() -> BaseLLMProvider:
        provider_type = os.getenv("CB_ACTIVE_LLM", "gemini").lower()
        
        if provider_type == "gemini":
            api_key = os.getenv("CB_GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
            model_id = os.getenv("CB_GEMINI_MODEL_ID", "gemini-2.5-pro")
            if not api_key:
                raise ValueError("❌ 未找到 Gemini API Key")
            return GeminiProvider(api_key, model_id)
            
        elif provider_type == "claude":
            api_key = os.getenv("CB_CLAUDE_API_KEY")
            model_id = os.getenv("CB_CLAUDE_MODEL_ID", "claude-3-5-sonnet-latest")
            if not api_key:
                raise ValueError("❌ 未找到 Claude API Key")
            return ClaudeProvider(api_key, model_id)
            
        elif provider_type == "doubao":
            api_key = os.getenv("CB_DOUBAO_API_KEY")
            endpoint_id = os.getenv("CB_DOUBAO_ENDPOINT_ID")
            if not api_key or not endpoint_id:
                raise ValueError("❌ 未找到 Doubao API Key 或 Endpoint ID")
            return DoubaoProvider(api_key, endpoint_id)
            
        else:
            raise ValueError(f"❌ 不支持的模型类型: {provider_type}")

# ==========================================
# 第四部分：核心业务逻辑 (Agent)
# ==========================================
class ContentCreatorAgent:
    def __init__(self, provider: BaseLLMProvider):
        self.llm = provider

    def _build_prompt(self, lesson_id: int, course_id: int) -> str:
        return f"""
        你是一名资深的对外汉语专家和数据工程师。请解析提供的教材 PDF，并严格按照要求提取内容，最终只输出一个合法的 JSON，不要包含任何额外的 Markdown 标记（如 ```json）。

        【核心解析规则】
        1. lesson_metadata:
            - course_id: {course_id}（英文学中文固定为1）
            - lesson_id: {lesson_id}
            - title: 这一课程的标题，例如 "Lesson {lesson_id}: 问好" (请根据课文内容生成，标题应该为中文)

        2. course_content (前端展示数据):
            - dialogues: 按照原文顺序提取课文内容，包括对话者，对话内容，这些都需要以中文提取，并标注拼音。
            - vocabulary: 提取单词、拼音、词性、英文定义。同时提取一个例句，必须将例句严格拆分为纯中文 (cn)、纯拼音 (py) 和英文翻译 (en)。

        3. database_items (题库数据，严格对齐 PostgreSQL 表结构):
            - 生成用于复习翻译的题目，必须覆盖基础核心词汇和课文重点句子。
            - 按照以下顺序：先是中译英单词，再是英译中单词，再是中译英句子，最后是英译中句子。
            - 剔除用户无法回答的无意义单字（如"呢"）或强相关的人名题目。
            - question_id: 从 1 开始递增。
            - question_type: 严格只能是 "CN_TO_EN" 或 "EN_TO_CN"。
            - standard_answers: 必须是数组（List/Array）。

        4. aigc_visual_prompt: 为本课生成一段 Midjourney 英文提示词，用于生成课程封面。

        【强制输出结构】
        请严格照抄以下 JSON 格式进行输出，绝不允许修改字段名或破坏层级结构：
        {{
            "lesson_metadata": {{
                "course_id": {course_id},
                "lesson_id": {lesson_id},
                "title": "Lesson {lesson_id}: 自动生成的标题"
            }},
            "course_content": {{
                "dialogues": [
                    {{
                        "lines": [
                            {{   
                                "role": "王小明",
                                "english": "Hello, my name is Wang Xiaoming.",
                                "words": [
                                    {{"cn": "你", "py": "nǐ"}},
                                    {{"cn": "好", "py": "hǎo"}}
                                ]
                            }}
                        ]
                    }}
                ],
                "vocabulary": [
                    {{
                        "word": "单词",
                        "pinyin": "dān cí",
                        "part_of_speech": "n",
                        "definition": "word",
                        "example_sentence": {{
                            "cn": "这是一个例句。",
                            "py": "Zhè shì yí gè lìjù.",
                            "en": "This is an example sentence."
                        }}
                    }}
                ]
            }},
            "database_items": [
                {{
                    "lesson_id": {lesson_id},
                    "question_id": 1,
                    "course_id": {course_id},
                    "question_type": "CN_TO_EN",
                    "original_text": "你好",
                    "standard_answers": ["Hello", "Hi"]
                }}
            ],
            "aigc_visual_prompt": "..."
        }}
        """

    def parse_textbook(self, file_path: str, lesson_id: int, course_id: int = 1):
        print(f"🚀 [ContentBuild] 任务启动: {Path(file_path).name} (ID: {lesson_id})")
        prompt = self._build_prompt(lesson_id, course_id)
        
        try:
            return self.llm.generate_structured_json(prompt, file_path)
        except Exception as e:
            print(f"❌ 解析过程发生错误: {e}")
            return None

# ==========================================
# 第五部分：主程序流
# ==========================================
def main():
    try:
        provider = LLMFactory.create_provider()
        agent = ContentCreatorAgent(provider)
        print(f"🔧 当前激活模型提供商: {type(provider).__name__}")
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return

    current_dir = Path(__file__).resolve().parent
    raw_dir = current_dir / "raw_materials"
    output_dir = current_dir / "output_json"
    archive_dir = current_dir / "archive_pdfs"
    
    for d in [raw_dir, output_dir, archive_dir]:
        d.mkdir(parents=True, exist_ok=True)
    
    pdf_files = list(raw_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"📭 raw_materials 为空，没有需要处理的 PDF。")
        return

    print(f"📦 发现 {len(pdf_files)} 个新教材准备处理！\n" + "="*40)

    for pdf_path in pdf_files:
        file_name = pdf_path.stem
        numbers = re.findall(r'\d+', file_name)
        if not numbers:
            print(f"⚠️ 警告：无法从文件名 {file_name} 提取编号，跳过该文件！")
            continue
            
        lesson_id = int(numbers[0])
        result = agent.parse_textbook(str(pdf_path), lesson_id=lesson_id)
        
        if result:
            output_file = output_dir / f"lesson{lesson_id}_data.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"✅ 成功生成数据: {output_file.name}")
            
            try:
                archive_path = archive_dir / pdf_path.name
                if archive_path.exists():
                    archive_path = archive_dir / f"{pdf_path.stem}_{int(time.time())}.pdf"
                shutil.move(str(pdf_path), str(archive_path))
                print(f"📁 教材已归档至: archive_pdfs 文件夹")
            except Exception as e:
                print(f"⚠️ 归档文件时发生错误: {e}")
        else:
            print(f"❌ {file_name}.pdf 处理失败，保留在 raw_materials 中等待下次重试。")
        print("-" * 40)

if __name__ == "__main__":
    main()