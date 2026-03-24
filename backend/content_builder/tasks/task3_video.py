import json
from llm_providers import BaseLLMProvider

class Task3VideoGenerator:
    def __init__(self, llm_provider: BaseLLMProvider):
        self.llm = llm_provider

    def _build_prompt(self, metadata: dict, dialogues: list) -> str:
        content_str = json.dumps({"metadata": metadata, "dialogues": dialogues}, ensure_ascii=False)
        return f"""
        你是一位专业的中文教学视频导演。请根据以下课文的场景和对话内容，为本节课设计教学短视频的分镜脚本。
        同时，请为每一幕生成用于 Sora 或 Midjourney 的高保真英文画面提示词。
        只输出合法的 JSON，不要包含任何额外的 Markdown 标记。

        课文内容：
        {content_str}

        【强制输出结构】
        {{
            "aigc_visual_prompt": "一段用于生成整个课程封面的 Midjourney 英文提示词",
            "video_script": [
                {{
                    "scene": 1,
                    "description_cn": "王小明在咖啡厅向朋友挥手打招呼的画面",
                    "aigc_prompt_en": "A realistic cinematic shot of a young Asian man waving his hand in a modern bright cafe, 4k, photorealistic --ar 16:9"
                }}
            ]
        }}
        """

    def run(self, metadata: dict, dialogues: list):
        print(f"  ▶️ [Task 3/3] 正在构思 AIGC 教学视频分镜与提示词...")
        prompt = self._build_prompt(metadata, dialogues)
        # 纯文本发散推理，无需 PDF
        result = self.llm.generate_structured_json(prompt, file_path=None)
        
        if result:
            return result
        return {"aigc_visual_prompt": "", "video_script": []}