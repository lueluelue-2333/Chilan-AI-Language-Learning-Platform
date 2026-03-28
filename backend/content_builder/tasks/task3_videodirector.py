import json
from llm_providers import BaseLLMProvider

class Task3VideoGenerator:
    def __init__(self, llm_provider: BaseLLMProvider):
        self.llm = llm_provider

    def _build_prompt(self, metadata: dict, dialogues: list, vocabulary: list, grammar: list) -> str:
        # 🚀 将全课素材整合为上下文，让导演知道本课重点教什么
        context = {
            "metadata": metadata,
            "dialogues": dialogues,
            "key_vocabulary": vocabulary[:10],  # 取核心词汇
            "grammar_points": grammar[:5]       # 取语法练习
        }
        content_str = json.dumps(context, ensure_ascii=False)
        
        return f"""
        你是一位专业的中文教学视频导演。请根据以下课件内容，为本节课设计一套【可直接对接视频生成 API】的教学短视频分镜脚本。
        同时，请为每一幕生成用于 Sora 或 Midjourney 的高保真英文画面提示词。
        只输出合法的 JSON，不要包含任何额外的 Markdown 标记。

        课文内容与教学重点：
        {content_str}

        【核心生成规则】
        1. 风格一致性：在 global_config 中设定一个统一的 visual_style（如：3D Pixar style, Cinematic, or Anime）。
        2. 角色定义：详细描述角色的外貌（英文），确保 AI 生成视频时人物形象在各分镜中保持一致。
        3. 分镜设计：提炼 3-6 个关键分镜，画面提示词（video_api_prompt_en）需包含环境、动作、镜头语言和光影细节。
        4. 教学融合：在分镜画面中自然体现本节课的重点词汇，并在 screen_overlay 中标注。

        【强制输出结构】
        {{
            "global_config": {{
                "visual_style": "整体视觉风格描述",
                "character_definitions": [
                    {{ "name": "角色名", "appearance_description_en": "详细的英文外貌描述词" }}
                ]
            }},
            "video_scenes": [
                {{
                    "scene_id": 1,
                    "scene_description_cn": "分镜画面描述",
                    "video_api_prompt_en": "Detailed AI prompt in English for video generation",
                    "camera_movement": "镜头动作 (如 Static, Zoom in, Pan)",
                    "voice_over": {{
                        "role": "说话人",
                        "content": "台词原文",
                        "pinyin": "拼音"
                    }},
                    "screen_overlay": {{
                        "main_text": "屏幕显示的重点词或句子",
                        "sub_text": "翻译/注释"
                    }}
                }}
            ]
        }}
        """

    def run(self, metadata: dict, dialogues: list, vocabulary: list = None, grammar: list = None):
        """
        🚀 修正点：增加 vocabulary 和 grammar 参数，确保与 ContentCreatorAgent 调用完全对齐
        """
        print(f"  ▶️ [Task 3/3] 正在以‘AI 导演’模式构思教学视频分镜与提示词...")
        
        # 容错处理：确保即使传入为空也能正常构建 Prompt
        vocabulary = vocabulary if vocabulary else []
        grammar = grammar if grammar else []
        
        prompt = self._build_prompt(metadata, dialogues, vocabulary, grammar)
        
        # 🚀 修正点：显式传递 file_path=None 和 file_obj=None
        # 这样做是为了确保调用完全符合 llm_providers.py 中最新的 generate_structured_json 签名
        result = self.llm.generate_structured_json(
            prompt, 
            file_path=None, 
            file_obj=None
        )
        
        if result and isinstance(result, dict):
            # 打印生成结果的简报
            scenes_count = len(result.get("video_scenes", []))
            print(f"  ✨ 导演脚本构思完毕，共生成 {scenes_count} 个核心分镜。")
            return result
            
        return {
            "global_config": {},
            "video_scenes": []
        }