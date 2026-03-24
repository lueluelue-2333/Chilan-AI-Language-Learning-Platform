import json
from pathlib import Path
from llm_providers import BaseLLMProvider

class Task2QuizGenerator:
    def __init__(self, llm_provider: BaseLLMProvider, memory_dir: Path):
        self.llm = llm_provider
        self.memory_file = memory_dir / "global_vocab_memory.json"
        self.global_vocab = self._load_memory()

    def _load_memory(self) -> set:
        if self.memory_file.exists():
            with open(self.memory_file, "r", encoding="utf-8") as f:
                return set(json.load(f))
        return set()

    def save_memory(self):
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(list(self.global_vocab), f, ensure_ascii=False, indent=2)

    def _build_prompt(self, lesson_id: int, course_id: int, new_vocabulary: list) -> str:
        vocab_str = json.dumps(new_vocabulary, ensure_ascii=False)
        return f"""
        你是一名资深的对外汉语专家。请根据以下提取出的【本课专属新词汇表】，生成用于复习的翻译题库。
        只输出合法的 JSON，不要包含任何额外的 Markdown 标记。

        生词表内容：
        {vocab_str}

        【核心生成规则】
        1. 必须覆盖这些基础核心词汇，不要对上面没出现的词汇出题。
        2. 按照以下顺序生成：先是中译英单词，再是英译中单词，再是中译英句子，最后是英译中句子。
        3. 在所有题目中剔除用户无法回答的无意义单字（如"呢"）或强相关的人名题目。
        4. question_id: 从 1 开始递增。
        5. question_type: 严格只能是 "CN_TO_EN" 或 "EN_TO_CN"。
        6. standard_answers: 必须是数组（List/Array），尽量可以多一些。

        【强制输出结构】
        {{
            "database_items": [
                {{
                    "lesson_id": {lesson_id},
                    "question_id": 1,
                    "course_id": {course_id},
                    "question_type": "CN_TO_EN",
                    "original_text": "你好",
                    "standard_answers": ["Hello", "Hi"]
                }}
            ]
        }}
        """

    def run(self, lesson_id: int, course_id: int, raw_vocabulary: list):
        # 1. Python 本地去重逻辑
        new_vocab = []
        for v in raw_vocabulary:
            word = v.get("word")
            if word and word not in self.global_vocab:
                new_vocab.append(v)
                self.global_vocab.add(word)

        print(f"  🔍 词汇记忆去重: 提取了 {len(raw_vocabulary)} 个词，过滤已学，新增 {len(new_vocab)} 个纯生词。")

        if not new_vocab:
            print("  ▶️ [Task 2/3] 本课无新生词，跳过题库生成。")
            return []

        # 2. 纯文本大模型推理
        print(f"  ▶️ [Task 2/3] 专注为 {len(new_vocab)} 个新生词生成题库...")
        prompt = self._build_prompt(lesson_id, course_id, new_vocab)
        # 此任务为纯文本生成，无需传入 file_path
        result = self.llm.generate_structured_json(prompt, file_path=None)
        
        if result and "database_items" in result:
            return result["database_items"]
        return []