import os
import json
import time
from abc import ABC, abstractmethod
from json_repair import repair_json  # 必须安装: pip install json-repair

class BaseLLMProvider(ABC):
    """定义所有模型必须实现的标准接口"""
    
    @abstractmethod
    def generate_structured_json(self, prompt: str, file_path: str = None, file_obj=None) -> dict:
        """支持直接传入路径或已上传的文件对象"""
        pass

    def upload_pdf(self, file_path: str):
        """预上传 PDF 文件的标准接口（主要为 Gemini 设计）"""
        return None

    def _safe_parse_json(self, raw_text: str) -> dict:
        """通用的 JSON 提取与自动修复逻辑"""
        if not raw_text:
            raise ValueError("❌ 收到空的原始文本，无法进行 JSON 解析。")
            
        # 1. 清理 Markdown 标记
        clean_text = raw_text.strip()
        if "```json" in clean_text:
            clean_text = clean_text.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_text:
            clean_text = clean_text.split("```")[1].split("```")[0].strip()

        # 2. 尝试标准解析
        try:
            return json.loads(clean_text)
        except json.JSONDecodeError:
            # 3. 如果标准解析失败，启动 json-repair 自动缝补
            try:
                print("⚠️ 检测到 JSON 语法错误，正在启动自动缝补...")
                repaired_json_str = repair_json(clean_text)
                return json.loads(repaired_json_str)
            except Exception as e:
                # 4. 如果缝补也失败，抛出详细错误
                raise Exception(f"❌ JSON 深度修复失败: {e}\n原始片段: {raw_text[-150:]}")

class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model_id: str):
        from google import genai
        self.client = genai.Client(api_key=api_key)
        self.model_id = model_id

    def upload_pdf(self, file_path: str):
        """Gemini 专属：上传文件并等待处理完成"""
        print(f"📤 正在上传教材到 Gemini 云端: {os.path.basename(file_path)}")
        with open(file_path, "rb") as f:
            sample_file = self.client.files.upload(
                file=f,
                config={'mime_type': 'application/pdf'}
            )
        
        while sample_file.state == "PROCESSING":
            time.sleep(2)
            sample_file = self.client.files.get(name=sample_file.name)

        if sample_file.state == "FAILED":
            raise Exception(f"❌ Gemini 处理文件失败: {file_path}")
        
        print("✅ 文件处理就绪。")
        return sample_file

    def generate_structured_json(self, prompt: str, file_path: str = None, file_obj=None) -> dict:
        from google.genai import types 
        contents = [prompt]
        
        if file_obj:
            contents.append(file_obj)
        elif file_path:
            file_obj = self.upload_pdf(file_path)
            contents.append(file_obj)

        # 🚀 修正后的安全设置：必须使用 HARM_CATEGORY_ 前缀的全称
        safety_settings = [
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
            types.SafetySetting(category="HARM_CATEGORY_CIVIC_INTEGRITY", threshold="BLOCK_NONE"),
        ]

        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=contents,
                config={
                    'response_mime_type': 'application/json',
                    'temperature': 0.0,
                    'max_output_tokens': 8192,
                    'safety_settings': safety_settings
                }
            )
        except Exception as e:
            # 如果还是报错，尝试把 CIVIC_INTEGRITY 这一行删掉（部分模型版本不支持此分类）
            raise Exception(f"❌ Gemini API 调用失败: {e}")
        
        if not response.text:
            candidate = response.candidates[0] if response.candidates else None
            finish_reason = getattr(candidate, 'finish_reason', 'UNKNOWN')
            raise Exception(f"❌ Gemini 返回空。原因: {finish_reason}")
            
        return self._safe_parse_json(response.text)

class ClaudeProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model_id: str):
        from anthropic import Anthropic
        self.client = Anthropic(api_key=api_key)
        self.model_id = model_id

    def generate_structured_json(self, prompt: str, file_path: str = None, file_obj=None) -> dict:
        import base64
        content_array = []
        if file_path:
            with open(file_path, "rb") as f:
                pdf_data = base64.b64encode(f.read()).decode("utf-8")
            content_array.append({
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": pdf_data
                }
            })
            
        content_array.append({
            "type": "text",
            "text": f"{prompt}\n\n请严格且仅输出 JSON 格式。"
        })

        response = self.client.messages.create(
            model=self.model_id,
            max_tokens=8192,
            temperature=0.0,
            messages=[{"role": "user", "content": content_array}]
        )
        return self._safe_parse_json(response.content[0].text)

class DoubaoProvider(BaseLLMProvider):
    def __init__(self, api_key: str, endpoint_id: str):
        from volcenginesdkarkruntime import Ark
        self.client = Ark(api_key=api_key)
        self.endpoint_id = endpoint_id

    def generate_structured_json(self, prompt: str, file_path: str = None, file_obj=None) -> dict:
        content_list = []
        if file_path:
            import fitz  
            import base64
            try:
                pdf_document = fitz.open(file_path)
                for page_num in range(len(pdf_document)):
                    page = pdf_document.load_page(page_num)
                    pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
                    img_data = pix.tobytes("png")
                    base64_str = base64.b64encode(img_data).decode("utf-8")
                    content_list.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{base64_str}"}
                    })
            except Exception as e:
                raise Exception(f"本地渲染 PDF 图片失败: {e}")

        content_list.append({"type": "text", "text": prompt})

        response = self.client.chat.completions.create(
            model=self.endpoint_id,
            messages=[{"role": "user", "content": content_list}],
            temperature=0.0,
            max_tokens=8192  
        )
        return self._safe_parse_json(response.choices[0].message.content)

class LLMFactory:
    """根据配置文件分发具体的模型 Provider"""
    @staticmethod
    def create_provider() -> BaseLLMProvider:
        provider_type = os.getenv("CB_ACTIVE_LLM", "gemini").lower()
        
        if provider_type == "gemini":
            api_key = os.getenv("CB_GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
            model_id = os.getenv("CB_GEMINI_MODEL_ID", "gemini-2.0-flash")
            if not api_key: raise ValueError("❌ 未找到 Gemini API Key")
            return GeminiProvider(api_key, model_id)
            
        elif provider_type == "claude":
            api_key = os.getenv("CB_CLAUDE_API_KEY")
            model_id = os.getenv("CB_CLAUDE_MODEL_ID", "claude-3-5-sonnet-latest")
            if not api_key: raise ValueError("❌ 未找到 Claude API Key")
            return ClaudeProvider(api_key, model_id)
            
        elif provider_type == "doubao":
            api_key = os.getenv("CB_DOUBAO_API_KEY")
            endpoint_id = os.getenv("CB_DOUBAO_ENDPOINT_ID")
            if not api_key or not endpoint_id: raise ValueError("❌ 未找到 Doubao 配置")
            return DoubaoProvider(api_key, endpoint_id)
            
        else:
            raise ValueError(f"❌ 不支持的模型类型: {provider_type}")