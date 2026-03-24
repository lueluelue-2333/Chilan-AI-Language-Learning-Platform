import os
import json
import time
from abc import ABC, abstractmethod

class BaseLLMProvider(ABC):
    """定义所有模型必须实现的标准接口"""
    @abstractmethod
    def generate_structured_json(self, prompt: str, file_path: str = None) -> dict:
        pass

class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model_id: str):
        from google import genai
        self.client = genai.Client(api_key=api_key)
        self.model_id = model_id

    def generate_structured_json(self, prompt: str, file_path: str = None) -> dict:
        contents = [prompt]
        
        # 只有在传入 file_path 时，才执行多模态文件上传
        if file_path:
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
            
            contents.append(sample_file)

        response = self.client.models.generate_content(
            model=self.model_id,
            contents=contents,
            config={
                'response_mime_type': 'application/json',
                'temperature': 0.1,
                'max_output_tokens': 8192
            }
        )
        return json.loads(response.text)

class ClaudeProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model_id: str):
        from anthropic import Anthropic
        self.client = Anthropic(api_key=api_key)
        self.model_id = model_id

    def generate_structured_json(self, prompt: str, file_path: str = None) -> dict:
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
            "text": f"{prompt}\n\n请严格且仅输出 JSON 格式，不要包含任何 Markdown 标记（如 ```json）。"
        })

        response = self.client.messages.create(
            model=self.model_id,
            max_tokens=8192,
            temperature=0.1,
            messages=[{"role": "user", "content": content_array}]
        )

        raw_text = response.content[0].text
        clean_text = raw_text.strip().removeprefix("```json").removesuffix("```").strip()
        return json.loads(clean_text)

class DoubaoProvider(BaseLLMProvider):
    def __init__(self, api_key: str, endpoint_id: str):
        from volcenginesdkarkruntime import Ark
        self.client = Ark(api_key=api_key)
        self.endpoint_id = endpoint_id

    def generate_structured_json(self, prompt: str, file_path: str = None) -> dict:
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
            temperature=0.1,
            max_tokens=8192  
        )
        
        raw_text = response.choices[0].message.content
        clean_text = raw_text.strip().removeprefix("```json").removesuffix("```").strip()
        
        try:
            return json.loads(clean_text)
        except json.JSONDecodeError as e:
            raise Exception(f"豆包返回的 JSON 格式有误: {e}\n原始返回: {raw_text[:200]}...")

class LLMFactory:
    """根据配置文件分发具体的模型 Provider"""
    @staticmethod
    def create_provider() -> BaseLLMProvider:
        provider_type = os.getenv("CB_ACTIVE_LLM", "gemini").lower()
        
        if provider_type == "gemini":
            api_key = os.getenv("CB_GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
            model_id = os.getenv("CB_GEMINI_MODEL_ID", "gemini-2.5-pro")
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