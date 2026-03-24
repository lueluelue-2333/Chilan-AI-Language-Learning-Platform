from llm_providers import BaseLLMProvider

class Task1Extractor:
    def __init__(self, llm_provider: BaseLLMProvider):
        self.llm = llm_provider

    def _build_prompt(self, lesson_id: int, course_id: int) -> str:
        return f"""
        你是一名资深的对外汉语专家和数据工程师。请解析提供的教材 PDF，并严格按照要求提取核心内容。
        最终只输出一个合法的 JSON，不要包含任何额外的 Markdown 标记（如 ```json）。

        【核心解析规则】
        1. lesson_metadata:
            - course_id: {course_id}（英文学中文固定为1）
            - lesson_id: {lesson_id}
            - title: 这一课程的标题，例如 "Lesson {lesson_id}: 问好" (根据课文内容生成中文标题)

        2. course_content (前端展示数据):
            - dialogues: 按照原文顺序提取课文内容，包括对话者，对话内容以中文提取并标注拼音。
            - vocabulary: 提取单词、拼音、词性、英文定义。提取一个例句，必须严格拆分为纯中文 (cn)、纯拼音 (py) 和英文翻译 (en)。

        【强制输出结构】
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
            }}
        }}
        """

    def run(self, file_path: str, lesson_id: int, course_id: int):
        print(f"  ▶️ [Task 1/3] 解析 PDF 提取课文与词汇...")
        prompt = self._build_prompt(lesson_id, course_id)
        # 此任务需要多模态能力，必须传入 file_path
        return self.llm.generate_structured_json(prompt, file_path=file_path)