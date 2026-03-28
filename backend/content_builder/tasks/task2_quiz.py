import json
import time
from pathlib import Path
from llm_providers import BaseLLMProvider

class Task2QuizGenerator:
    def __init__(self, llm_provider: BaseLLMProvider, memory_dir: Path):
        self.llm = llm_provider
        self.memory_file = memory_dir / "global_vocab_memory.json"
        # 🚀 这里的 global_vocab 现在的结构是字典: { "单词": [ {词义1...}, {词义2...} ] }
        self.global_vocab = self._load_memory()

    def _load_memory(self) -> dict:
        if self.memory_file.exists():
            with open(self.memory_file, "r", encoding="utf-8") as f:
                try:
                    return json.load(f)
                except:
                    return {}
        return {}

    def save_memory(self, new_vocab_list: list, lesson_id: int):
        """
        🚀 升级版保存逻辑：将本课新词的完整信息（释义、例句）追加到全局词典中
        """
        # 重新加载一次以确保数据最新
        full_dict = self._load_memory()

        for v in new_vocab_list:
            word = v.get("word")
            definition = v.get("definition")
            
            entry = {
                "definition": definition,
                "pinyin": v.get("pinyin"),
                "part_of_speech": v.get("part_of_speech"),
                "example": v.get("example_sentence"), # 包含 cn, py, en
                "lesson_id": lesson_id
            }

            if word not in full_dict:
                full_dict[word] = []
            
            # 💡 防重复检查：如果该单词下已存在完全相同的释义，则不重复添加
            learned_definitions = [e["definition"] for e in full_dict[word]]
            if definition not in learned_definitions:
                full_dict[word].append(entry)

        # 创建目录（如果不存在）
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(full_dict, f, ensure_ascii=False, indent=2)

    def _inject_historical_context(self, current_vocab: list) -> list:
        """
        🚀 打捞逻辑：为当前生词注入该词在之前课程中学过的所有用法
        """
        for v in current_vocab:
            word = v.get("word")
            # 如果记忆库里有这个词的历史记录，则捞出来
            if word in self.global_vocab:
                v["historical_usages"] = self.global_vocab[word]
        return current_vocab

    # --- Task 2.1a: 提取单词基本信息 (骨架) ---
    def _build_vocab_base_prompt(self) -> str:
        return """
        你是一名数据提取专家。
        🚨 【核心禁令】：严禁使用你自身的知识储备！你必须【且仅能】提取 PDF 页面中物理显示的文字。
        
        【提取要求】
        1. 仅定位 PDF 中的“生词表/Vocabulary”板块。
        2. 仅提取字段：单词(word)、拼音(pinyin)、词性(part_of_speech)、英文定义(definition)。
        3. 如果当前 PDF 页面没有任何生词表，请直接返回 {"vocabulary": []}。
        4. 严禁自行添加任何 PDF 中不存在的单词（哪怕你觉得这一课应该学这些词）。
        
        【输出格式】
        只输出合法的 JSON，不包含任何 Markdown 标记。
        { "vocabulary": [ { "word": "...", "pinyin": "...", "part_of_speech": "...", "definition": "..." } ] }
        """
    
    def _build_vocab_example_prompt(self, word_list: list) -> str:
        words_str = ", ".join([w.get("word", "") for w in word_list])
        return f"""
        你是一名数据提取专家。请从 PDF 中为以下单词提取原书配套的【官方例句】。
        单词列表：{words_str}

        【🚨 提取准则】
        1. 必须且仅能提取 PDF 中物理显示的原文例句。
        2. 严禁（FATAL ERROR）根据单词自行造句，严禁从你的知识库中引用外部例句。
        3. 必须保持中文、拼音、英文的严格对齐。

        【强制输出结构】
        - 必须返回一个 JSON 数组，长度必须为 {len(word_list)}。
        - 如果某个单词在 PDF 中没有找到配套例句，该项必须返回以下空对象：
          {{ "cn": "", "py": "", "en": "" }}
        - 示例结构：
          [
            {{ "cn": "我是学生。", "py": "Wǒ shì xuésheng.", "en": "I am a student." }},
            {{ "cn": "", "py": "", "en": "" }} 
          ]
        """

    # --- Task 2.2a: 专门提取重点句子 ---
    def _build_key_sentences_prompt(self) -> str:
        return """
        你是一名数据提取专家。请解析 PDF，并【直接搬运】书中的“重点句子/Key Sentences”部分。
        只输出合法的 JSON 格式。

        【🚨 提取准则】
        1. 必须定位到 PDF 中专门的“重点句子”或“核心句型”区域。
        2. 严禁推测，严禁根据课文内容自己拼凑句子。
        3. 每一个条目必须包含：中文全文(cn)、纯拼音(py) 和 英文翻译(en)。

        【强制输出结构】
        - 如果在 PDF 中未发现该板块，请务必返回：{{ "key_sentences": [] }}
        - 正常结构示例：
          {{
            "key_sentences": [
                {{ "cn": "句子原文", "py": "jùzi yuánwén", "en": "sentence" }}
            ]
          }}
        """

    def _build_grammar_extract_prompt(self) -> str:
        return """
        你是一名数据提取专家。请解析 PDF，提取书中的“语法/练习(Grammar/Exercises)”部分。
        只输出合法的 JSON 格式。

        【🚨 提取准则】
        1. 仅限提取课后习题中用于“翻译练习”或“完成句子”的原文。
        2. 严禁（STOP）引入任何与本教材内容、本课主题无关的句子。
        3. 严禁为了凑数而自行生成练习题。

        【强制输出结构】
        - 如果在 PDF 中未发现适合的练习句，请务必返回：{{ "grammar_practice": [] }}
        - 正常结构示例：
          {{
            "grammar_practice": [
                {{ "cn": "练习句原文", "py": "liànxíjù yuánwén", "en": "exercise" }}
            ]
          }}
        """
    
    # --- Task 2.3a: 专门生成单词题 (100% 覆盖) ---
    def _build_word_quiz_prompt(self, lesson_id: int, course_id: int, vocabulary_with_history: list) -> str:
        vocab_str = json.dumps(vocabulary_with_history, ensure_ascii=False)
        vocab_count = len(vocabulary_with_history)
        
        return f"""
        你是一名严谨的词汇练习编写专家。请为提供的【核心词汇表】生成全量翻译练习。
        
        【素材清单】
        本课核心词汇（共 {vocab_count} 个）：{vocab_str}

        【🚨 核心生成规则 - 必须 100% 遵守】
        1. **词汇全覆盖 (Word-Level Full Coverage)**：
           - 你必须为【核心词汇表】中的【每一个】单词生成两道题：
             * 一道中译英 (CN_TO_EN)
             * 一道英译中 (EN_TO_CN)
           - 意味着如果你收到了 {vocab_count} 个词，你【必须】产出 {vocab_count * 2} 道词汇题。
        
        2. **单例句约束 (One Context Example)**：
           - 每道题目【只需且仅能】提供 1 个关联例句（context_examples 数组长度必须为 1）。
           - 必须从素材中提供的 example_sentence 或 historical_usages 中提取。

        3. **禁止幻觉**：
           - 题目和例句必须 100% 来源于提供的素材，严禁引入清单外的任何主题或复杂句型。

        【强制输出结构】
        {{
            "database_items": [
                {{
                    "lesson_id": {lesson_id},
                    "question_id": 0,
                    "course_id": {course_id},
                    "question_type": "CN_TO_EN 或 EN_TO_CN",
                    "original_text": "单词文本",
                    "original_pinyin": "拼音(中文题目必填)",
                    "standard_answers": ["标准答案"],
                    "context_examples": [
                        {{ "cn": "唯一例句", "py": "pinyin", "en": "translation" }}
                    ]
                }}
            ]
        }}
        """

    # --- Task 2.3b: 专门生成句子题 (精选生成) ---
    def _build_sentence_quiz_prompt(self, lesson_id: int, course_id: int, combined_practice: list) -> str:
        grammar_str = json.dumps(combined_practice, ensure_ascii=False)
        
        return f"""
        你是一名资深的对外汉语专家。请根据提供的【原句素材】生成精选翻译题库。
        
        【素材清单】
        课文/语法原句素材：{grammar_str}

        【🚨 核心生成规则 - 必须 100% 遵守】
        1. **句子翻译 (Sentence-Level)**：
           - 从素材中挑选最核心的句子生成 5-8 道精选翻译题。
           - 必须包含中译英 (CN_TO_EN) 和 英译中 (EN_TO_CN) 两种形式。

        2. **无例句要求**：
           - 句子翻译题【不需要】提供 context_examples，直接返回题目即可。

        3. **禁止幻觉**：
           - 题目必须 100% 来源于提供的素材，严禁自行编造清单外的内容。

        【强制输出结构】
        {{
            "database_items": [
                {{
                    "lesson_id": {lesson_id},
                    "question_id": 0,
                    "course_id": {course_id},
                    "question_type": "CN_TO_EN 或 EN_TO_CN",
                    "original_text": "句子原文",
                    "original_pinyin": "拼音(中文题目必填)",
                    "standard_answers": ["标准答案"]
                }}
            ]
        }}
        """

    def run(self, lesson_id: int, course_id: int, file_path: str = None, file_obj=None):
        # --- [Task 2.1a] 提取词汇基本信息 ---
        print(f"  ▶️ [Task 2.1a] 提取词汇基本信息 (骨架)...")
        v_base_res = self.llm.generate_structured_json(self._build_vocab_base_prompt(), file_path=file_path, file_obj=file_obj)
        raw_vocab = v_base_res.get("vocabulary", []) if isinstance(v_base_res, dict) else []
        
        new_vocab_base = []
        if isinstance(raw_vocab, list):
            for v in raw_vocab:
                if isinstance(v, dict):
                    word = v.get("word")
                    definition = v.get("definition")
                    # 校验一词多义
                    if word not in self.global_vocab or definition not in [e["definition"] for e in self.global_vocab[word]]:
                        new_vocab_base.append(v)
                    else:
                        print(f"  ⏭️ 跳过已掌握的词义: {word} ({definition})")
        
        if not new_vocab_base:
            print("  ⚠️ 本课无新生词义。")
        
        time.sleep(2)

        # --- [Task 2.1b] 提取官方例句 ---
        new_vocab = []
        if new_vocab_base:
            print(f"  ▶️ [Task 2.1b] 正在回填官方例句 (针对 {len(new_vocab_base)} 个新词义)...")
            v_ex_res = self.llm.generate_structured_json(self._build_vocab_example_prompt(new_vocab_base), file_path=file_path, file_obj=file_obj)
            if isinstance(v_ex_res, list) and len(v_ex_res) == len(new_vocab_base):
                for i, v in enumerate(new_vocab_base):
                    v["example_sentence"] = v_ex_res[i]
                    new_vocab.append(v)
            else:
                new_vocab = new_vocab_base

        time.sleep(2)

        # --- [Task 2.2a/b] 提取素材 ---
        print(f"  ▶️ [Task 2.2a/b] 提取核心重点句与语法练习...")
        s_result = self.llm.generate_structured_json(self._build_key_sentences_prompt(), file_path=file_path, file_obj=file_obj)
        key_sentences = s_result.get("key_sentences", []) if isinstance(s_result, dict) and isinstance(s_result.get("key_sentences"), list) else []
        
        g_result = self.llm.generate_structured_json(self._build_grammar_extract_prompt(), file_path=file_path, file_obj=file_obj)
        grammar_exercises = g_result.get("grammar_practice", []) if isinstance(g_result, dict) and isinstance(g_result.get("grammar_practice"), list) else []

        combined_practice = []
        for item in (key_sentences + grammar_exercises):
            if isinstance(item, dict): combined_practice.append(item)

        # 注入历史上下文
        vocab_with_history = self._inject_historical_context(new_vocab)
        time.sleep(1)

        # --- [Task 2.3 拆分生成 - 微批处理版] ---
        
        # 🚀 2.3a 单词翻译题 (分批生成)
        all_word_items = []
        batch_size = 4  
        
        if vocab_with_history:
            print(f"  ▶️ [Task 2.3a] 开始微批处理单词题 (共 {len(vocab_with_history)} 个词)...")
            for i in range(0, len(vocab_with_history), batch_size):
                batch = vocab_with_history[i : i + batch_size]
                current_batch_num = (i // batch_size) + 1
                print(f"     📦 正在生成第 {current_batch_num} 组单词题目...")
                
                word_q_prompt = self._build_word_quiz_prompt(lesson_id, course_id, batch)
                word_q_res = self.llm.generate_structured_json(word_q_prompt, file_path=None, file_obj=None)
                
                if word_q_res and isinstance(word_q_res, dict):
                    batch_items = word_q_res.get("database_items", [])
                    all_word_items.extend(batch_items)
                
                time.sleep(2)

        # 🚀 2.3b 句子翻译题
        print(f"  ▶️ [Task 2.3b] 正在生成精选句子题库...")
        sent_q_prompt = self._build_sentence_quiz_prompt(lesson_id, course_id, combined_practice)
        sent_q_res = self.llm.generate_structured_json(sent_q_prompt, file_path=None, file_obj=None)
        sent_items = sent_q_res.get("database_items", []) if isinstance(sent_q_res, dict) else []

        # 🚀 【核心修改：按类型强制排序】
        # 1. 汇总所有题目
        all_raw_items = all_word_items + sent_items
        
        # 2. 按照题型分类到两个桶里
        cn_to_en_pool = [i for i in all_raw_items if i.get("question_type") == "CN_TO_EN"]
        en_to_cn_pool = [i for i in all_raw_items if i.get("question_type") == "EN_TO_CN"]
        
        # 3. 按照“先中译英，后英译中”重新组合
        sorted_items = cn_to_en_pool + en_to_cn_pool

        # 🚀 【结果清理与重排 ID】
        valid_items = []
        for index, item in enumerate(sorted_items):
            if isinstance(item, dict) and item.get("original_text") and item.get("standard_answers"):
                item["question_id"] = index + 1  # 重新分配连续的递增 ID
                valid_items.append(item)

        # 🚀 持久化更新
        if new_vocab:
            self.save_memory(new_vocab, lesson_id)
            print(f"  ✅ Task 2 完整结束，已将新词义及例句存入词典。")

        return {
            "vocabulary": new_vocab,
            "database_items": valid_items
        }