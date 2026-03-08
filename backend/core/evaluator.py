import json
import google.generativeai as genai
from typing import Dict, List

class Evaluator:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        
        # 保持你的 Level 1 最好的定义，由后端 main.py 负责翻转
        self.PROMPT_TEMPLATES = {
            "CN_TO_EN": """
                You are a strict English coach. The student is translating Chinese to English.
                Source (CN): "{question}"
                Reference Answers: {standards}
                Student's Answer (EN): "{user_answer}"
                
                Evaluation Criteria:
                1. Level 1: Native-like, correct grammar, articles (a/an/the), and collocations.
                2. Level 2: Clear meaning but minor slips (e.g., singular/plural, capitalization).
                3. Level 3: Understandable but has major grammatical issues or wrong keywords.
                4. Level 4: Complete mistranslation or nonsensical English.

                Note: If the student uses a synonym not in the reference but it's natural English, give Level 1.
                Output JSON: {{ "level": int, "is_correct": bool, "explanation": "string (concise English explanation)" }}
            """,
            "EN_TO_CN": """
                你是一名严谨的中文老师。学生正在将英文翻译成中文。
                原题 (EN): "{question}"
                标准参考: {standards}
                学生回答 (CN): "{user_answer}"

                评价标准：
                1. Level 1: 表达地道，逻辑通顺，无错别字。
                2. Level 2: 意思正确但略显生硬（翻译腔），或有极个别错别字。
                3. Level 3: 意思大致对但有严重语法问题或漏掉核心成分。
                4. Level 4: 语义偏离较大。

                要求：解释尽量精简，指出中文表达的优劣。
                输出 JSON: {{ "level": int, "is_correct": bool, "explanation": "string (中英双语精简解释)" }}
            """
        }

    def get_embedding(self, text: str):
        """生成 3072 维高质量向量"""
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=text,
            task_type="semantic_similarity"
        )
        return result['embedding']

    async def judge(self, q_type: str, user_input: str, orig_text: str, std_answers: List[str], score: float) -> Dict:
        # 1. 向量极速路径
        if score > 0.985:
            return {
                "level": 1, 
                "is_correct": True, 
                "explanation": "完美匹配！表达非常地道。", 
                "judged_by": "Vector Engine"
            }
        
        # 2. LLM 深度判题
        template = self.PROMPT_TEMPLATES.get(q_type, self.PROMPT_TEMPLATES["EN_TO_CN"])
        full_prompt = template.format(question=orig_text, standards=std_answers, user_answer=user_input)
        
        response = self.model.generate_content(full_prompt)
        # 清洗 JSON
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        try:
            feedback = json.loads(clean_json)
            feedback["judged_by"] = "LLM Mentor"
            return feedback
        except Exception:
            # 兜底逻辑
            return {"level": 4, "is_correct": False, "explanation": "AI 解析异常", "judged_by": "System Error"}