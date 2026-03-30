import json
import os
from llm_providers import BaseLLMProvider

class Task1Extractor:
    def __init__(self, llm_provider: BaseLLMProvider):
        self.llm = llm_provider
        self.pinyin_batch_size = max(1, int(os.getenv("CB_TASK1_PINYIN_BATCH_SIZE", "3")))
        self.pinyin_batch_char_limit = max(200, int(os.getenv("CB_TASK1_PINYIN_BATCH_CHAR_LIMIT", "600")))

    def _build_extract_prompt(self, lesson_id: int, course_id: int) -> str:
        # 🚀 第一步：文本提取 + 强力去噪
        return f"""
        你是一名数据提取专家。请解析提供的教材 PDF，提取核心课文内容。
        只需输出 JSON。不要做拼音拆解。

        【解析要求】
        1. lesson_metadata: course_id({course_id}), lesson_id({lesson_id}), title(根据内容生成中文标题), content_type(课文主要形式)。
        2. content_type 仅能从以下枚举中选择一个：
           - "dialogue": 以人物对话为主
           - "diary": 日记体
           - "article": 短文/文章
           - "passage": 一般叙述性课文/段落
           - "mixed": 对话与叙述混合
        3. dialogues: 按照原文顺序提取。只需提取：role (角色), chinese (中文原文), english (英文翻译)。
        4. 如果是对话类课文，按说话轮次提取，role 使用教材中的角色名。
        5. 如果是日记/文章/段落类课文，按自然句顺序切分提取；role 不要编造人物名，可统一填写为 "日记"、"课文" 或 "旁白" 中最合适的一项，并在整课内保持一致。

        【🚨 视觉去噪指令 - 极其重要】
        - 必须剔除教材中的所有注脚符号、字母标记和参考数字。
        - 例如：剔除上标字母（a, b, c, d）、注脚数字（1, 2, 3）以及特殊符号（1*）。
        - 示例：原文 "我姓 1* 李" 提取后应为 "我姓李"。
        - 必须【原封不动】地保留句子中的所有标点符号（，。？！：）。

        【强制输出结构】
        {{
            "lesson_metadata": {{
                "course_id": {course_id},
                "lesson_id": {lesson_id},
                "title": "...",
                "content_type": "dialogue"
            }},
            "course_content": {{
                "dialogues": [
                    {{ "role": "姓名", "chinese": "纯净对话内容", "english": "translation" }}
                ]
            }}
        }}
        """

    def _build_pinyin_prompt(self, dialogues_to_process: list) -> str:
        # 🚀 第二步：拼音标注 + 自动识别新词高亮
        text_content = json.dumps(dialogues_to_process, ensure_ascii=False)
        return f"""
        你是一名中文拼音标注专家。请将对话中的中文句子 (chinese) 拆分为词或字，并标注拼音。
        素材：{text_content}

        【输出要求】
        1. 保持 role 和 english 不变。
        2. words 数组：每个对象包含 cn (中文)、py (拼音) 和 highlight (布尔值)。
        
        【🚨 高亮与标点规则】
        - highlight: 如果该词是本课的核心新词（如动词、代词、关键名词），设为 true，否则为 false。
        - 标点处理：标点符号必须独立成项，py 为空 ""，highlight 为 false。
        - 示例："我姓李。" 拆分为：
          [ {{"cn": "我", "py": "wǒ", "highlight": false}}, {{"cn": "姓", "py": "xìng", "highlight": true}}, {{"cn": "李", "py": "lǐ", "highlight": false}}, {{"cn": "。", "py": "", "highlight": false}} ]

        【输出结构】
        [
            {{ 
              "role": "姓名", 
              "english": "...", 
              "words": [ {{ "cn": "词", "py": "pinyin", "highlight": true/false }} ] 
            }}
        ]
        """

    def _estimate_dialogue_size(self, dialogue: dict) -> int:
        if not isinstance(dialogue, dict):
            return 0
        role = dialogue.get("role", "") or ""
        chinese = dialogue.get("chinese", "") or ""
        english = dialogue.get("english", "") or ""
        return len(role) + len(chinese) + len(english)

    def _chunk_dialogues(self, dialogues: list):
        current_batch = []
        current_chars = 0

        for dialogue in dialogues:
            dialogue_chars = self._estimate_dialogue_size(dialogue)
            should_split = (
                current_batch
                and (
                    len(current_batch) >= self.pinyin_batch_size
                    or current_chars + dialogue_chars > self.pinyin_batch_char_limit
                )
            )
            if should_split:
                yield current_batch
                current_batch = []
                current_chars = 0

            current_batch.append(dialogue)
            current_chars += dialogue_chars

        if current_batch:
            yield current_batch

    def _generate_pinyin_batch(self, batch: list):
        pinyin_prompt = self._build_pinyin_prompt(batch)
        return self.llm.generate_structured_json(pinyin_prompt, file_path=None)

    def _annotate_batch_with_retry(self, batch: list, batch_label: str) -> list:
        try:
            batch_result = self._generate_pinyin_batch(batch)
            if isinstance(batch_result, list):
                return batch_result
            raise ValueError(f"❌ Task 1.2 {batch_label} 返回结构异常，期望 list。")
        except Exception as exc:
            error_text = str(exc)
            if "MAX_TOKENS" in error_text and len(batch) > 1:
                split_point = max(1, len(batch) // 2)
                print(
                    f"     ⚠️ {batch_label} 命中 MAX_TOKENS，正在自动拆分为 "
                    f"{split_point} + {len(batch) - split_point} 句重试..."
                )
                left_result = self._annotate_batch_with_retry(batch[:split_point], f"{batch_label}-A")
                right_result = self._annotate_batch_with_retry(batch[split_point:], f"{batch_label}-B")
                return left_result + right_result
            raise

    def _annotate_pinyin_in_batches(self, raw_dialogues: list) -> list:
        if not raw_dialogues:
            return []

        batches = list(self._chunk_dialogues(raw_dialogues))
        if len(batches) == 1:
            only_batch = batches[0]
            print(
                f"     📦 Task 1.2 以单批处理拼音标注 "
                f"(共 {len(only_batch)} 句, 约 {sum(self._estimate_dialogue_size(x) for x in only_batch)} 字符)..."
            )
            return self._annotate_batch_with_retry(only_batch, "Task 1.2 单批")

        print(
            f"     📦 Task 1.2 将按批次处理拼音标注 "
            f"(共 {len(raw_dialogues)} 句, 最多 {self.pinyin_batch_size} 句/批, "
            f"约 {self.pinyin_batch_char_limit} 字符/批, 实际 {len(batches)} 批)..."
        )
        merged_result = []

        for index, batch in enumerate(batches, start=1):
            batch_chars = sum(self._estimate_dialogue_size(x) for x in batch)
            print(f"     📦 正在处理第 {index} 组拼音标注 ({len(batch)} 句, 约 {batch_chars} 字符)...")
            batch_result = self._annotate_batch_with_retry(batch, f"Task 1.2 第 {index} 组")
            merged_result.extend(batch_result)

        return merged_result

    def run(self, lesson_id: int, course_id: int, file_path: str = None, file_obj=None):
        print(f"  ▶️ [Task 1.1] 正在从 PDF 提取纯净对话文本...")
        extract_prompt = self._build_extract_prompt(lesson_id, course_id)
        raw_result = self.llm.generate_structured_json(extract_prompt, file_path=file_path, file_obj=file_obj)
        
        if not raw_result: return None

        print(f"  ▶️ [Task 1.2] 正在标注拼音并识别重点词汇...")
        raw_dialogues = raw_result.get("course_content", {}).get("dialogues", [])
        pinyin_result = self._annotate_pinyin_in_batches(raw_dialogues)

        # 🚀 【结构封装】：匹配前端 .flatMap(t => t.lines)
        raw_result["course_content"]["dialogues"] = [
            {
                "lines": pinyin_result
            }
        ]
        
        print(f"  ✨ Task 1 解析完毕 (已净化文本并添加变色高亮标记)。")
        return raw_result
