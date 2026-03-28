# -*- coding: utf-8 -*-

# 评分标准：
# 4: 完美 (Standard/Natural) - 语义完全对齐，表达地道
# 3: 优秀 (Minor variation) - 意思完全正确，但存在微小冠词、标点或非核心用词差异
# 2: 一般 (Understandable/Flawed) - 意思能懂，但存在语序不当、关键形容词缺失等瑕疵
# 1: 错误 (Logic/Entity error) - 核心语义错误、主谓关系颠倒或关键信息（性别、数字、职业）错误

test_suites = {
    "English_Evaluation": {
        "Q21: 你是老师吗? (L102)": {
            "standard": "Are you a teacher?",
            "cases": [
                ("Are you a teacher?", 4),
                ("Are you the teacher?", 3),  # 冠词变化，但在某些语境下正确
                ("You are a teacher?", 2),    # 陈述句语序当疑问句
                ("Is you a teacher?", 2),     # 严重的系动词语法错误
                ("Are you a student?", 1)     # 实体错误（老师 vs 学生）
            ]
        },
        "Q22: 我不是老师，我是学生 (L102)": {
            "standard": "I am not a teacher, I am a student.",
            "cases": [
                ("I am not a teacher, I am a student.", 4),
                ("I'm a student, not a teacher.", 3),
                ("I not a teacher, I is student.", 1), # 语法崩坏
                ("I am a teacher, I am not a student.", 1), # 逻辑完全颠倒
                ("I'm a student.", 2)         # 信息遗漏一半
            ]
        },
        "Q25: 我是北京人 (L102)": {
            "standard": "I am from Beijing.",
            "cases": [
                ("I am from Beijing.", 4),
                ("I am a Beijing person.", 3),
                ("I come from Beijing.", 4),
                ("I am Beijing.", 2),         # 逻辑错误：我是个地点
                ("He is from Beijing.", 1)    # 代词错误
            ]
        },
        "Q23: 这个女孩子是谁? (L201)": {
            "standard": "Who is this girl?",
            "cases": [
                ("Who is this girl?", 4),
                ("Who's that girl?", 3),       # 指示代词偏移 (this vs that)
                ("This girl is who?", 2),     # 中式英语语序
                ("Who is this boy?", 1)       # 性别错误
            ]
        },
        "Q26: 他是我大哥的儿子 (L201)": {
            "standard": "He is my oldest brother's son.",
            "cases": [
                ("He is my eldest brother's son.", 4),
                ("He's the son of my oldest brother.", 4),
                ("He is my brother's son.", 2), # 缺少“大哥”细节
                ("She is my oldest brother's son.", 1), # 代词性别错误
                ("He is my oldest brother's daughter.", 1) # 身份错误
            ]
        },
        "Q28: 他没有女儿 (L201)": {
            "standard": "He doesn't have a daughter.",
            "cases": [
                ("He doesn't have a daughter.", 4),
                ("He has no daughter.", 4),
                ("He hasn't a daughter.", 3),  # 稍显过时的用法
                ("He have no daughter.", 2),   # 第三人称单数错误
                ("He has a daughter.", 1)      # 逻辑否定失效
            ]
        },
        "Q21: 我家有六口人 (L202)": {
            "standard": "There are six people in my family.",
            "cases": [
                ("My family has six people.", 4),
                ("There are 6 people in my family.", 4),
                ("My family has six person.", 2), # 单复数错误
                ("My family has five people.", 1) # 数字错误
            ]
        },
        "Q23: 我爸爸是律师 (L202)": {
            "standard": "My father is a lawyer.",
            "cases": [
                ("My dad is a lawyer.", 4),
                ("My father is a lawyer.", 4),
                ("My father is lawyer.", 3),   # 缺冠词
                ("My mother is a lawyer.", 1), # 成员错误
                ("My father is a doctor.", 1)  # 职业错误
            ]
        },
        "Q25: 九月十二号是星期几? (L301)": {
            "standard": "What day of the week is September 12th?",
            "cases": [
                ("What day is September 12th?", 4),
                ("Which day is September 12th?", 4),
                ("September 12th is which day?", 2), # 语序不当
                ("What date is September 12th?", 1)  # 混淆 Day (星期) 与 Date (日期)
            ]
        },
        "Q29: 你喜欢吃中国菜还是美国菜? (L301)": {
            "standard": "Do you like to eat Chinese food or American food?",
            "cases": [
                ("Do you like to eat Chinese food or American food?", 4),
                ("Do you like Chinese food or American food?", 4),
                ("Do you like Chinese or American food?", 3),
                ("Do you prefer Chinese food or American food?", 4),
                ("You like Chinese food or American food?", 2), # 缺少助动词
                ("Do you like Chinese food and American food?", 1) # 逻辑连词错误 (or vs and)
            ]
        }
    },
    
    "Chinese_Evaluation": {
        "Q24: My family name is Li. How about you? (L101)": {
            "standard": "我姓李，你呢？",
            "cases": [
                ("我姓李。你呢？", 4),
                ("我的姓是李，你呢？", 4),
                ("我叫李，你呢？", 2), # 姓 vs 叫，语义偏差
                ("我姓李，你怎么样？", 3), # “你怎么样”略显生硬
                ("你是李吗？你呢？", 1)  # 逻辑错误
            ]
        },
        "Q28: I am not a teacher, I am a student. (L102)": {
            "standard": "我不是老师，我是学生。",
            "cases": [
                ("我不是老师，我是学生。", 4),
                ("我是学生，不是老师。", 4),
                ("我没当老师，我是一个学生。", 3),
                ("我老师不是，我是学生。", 2), # 语序瑕疵
                ("我是老师，我不是学生。", 1) # 逻辑完全反向 (Negation Flip)
            ]
        },
        "Q30: Are you Chinese? (L102)": {
            "standard": "你是中国人吗？",
            "cases": [
                ("你是中国人吗？", 4),
                ("你是华裔吗？", 2), # 范畴略有不同
                ("你是中国吗？", 2), # 缺少“人”，逻辑错误
                ("你是美国人吗？", 1) # 实体错误
            ]
        },
        "Q31: I am from New York. (L102)": {
            "standard": "我是纽约人。",
            "cases": [
                ("我来自纽约。", 4),
                ("我是纽约来的。", 3),
                ("我是纽约人。", 4),
                ("我是纽约。", 2), # 典型初学者错误
                ("我不在纽约。", 1) # 逻辑否定
            ]
        },
        "Q30: She is my older sister. (L201)": {
            "standard": "她是我姐姐。",
            "cases": [
                ("她是我姐姐。", 4),
                ("她是我姊姊。", 4),
                ("她是我大的姐姐。", 3), # 稍显冗余
                ("她是我妹妹。", 2), # 亲属称谓错误（长幼）
                ("他是我哥哥。", 1) # 性别及称谓双重错误
            ]
        },
        "Q32: He is my oldest brother's son. (L201)": {
            "standard": "他是我大哥的儿子。",
            "cases": [
                ("他是我大哥的儿子。", 4),
                ("他是我大哥哥的孩子。", 2),
                ("他是我大弟的儿子。", 2), # “大弟”逻辑矛盾
                ("我是他大哥的儿子。", 1), # 主客颠倒
                ("他是我大哥的女儿。", 1) # 性别错误
            ]
        },
        "Q25: How many people are in your family? (L202)": {
            "standard": "你家有几口人？",
            "cases": [
                ("你家有几个人？", 4),
                ("你家有几口人？", 4),
                ("你家有几个口？", 2), # 量词误用
                ("你家有什么人？", 1), # 问法变更
                ("你家有几只人？", 1) # 严重的量词侮辱性错误
            ]
        },
        "Q26: My father is a lawyer. (L202)": {
            "standard": "我爸爸是律师。",
            "cases": [
                ("我爸爸是律师。", 4),
                ("我父亲是律师。", 4),
                ("我爸爸是法律。", 2), # 属性混淆
                ("我爸爸是老师。", 1), # 职业错误
                ("我爸爸不是律师。", 1) # 逻辑否定
            ]
        },
        "Q34: What day of the week is it today? (L301)": {
            "standard": "今天是星期几？",
            "cases": [
                ("今天是星期几？", 4),
                ("今天周几？", 4),
                ("今天礼拜几？", 4),
                ("今天几号？", 2), # 混淆星期与日期
                ("昨天是星期几？", 1) # 时间错误
            ]
        },
        "Q37: I'll treat you to a meal on Thursday. (L301)": {
            "standard": "我星期四请你吃饭。",
            "cases": [
                ("我周四请你吃饭。", 4),
                ("星期四我请你吃顿饭。", 4),
                ("我星期四你请吃饭。", 2), # 语序崩溃
                ("你星期四请我吃饭。", 1), # 逻辑反转 (谁花钱)
                ("我星期五请你吃饭。", 1) # 日期错误
            ]
        },
        "Q40: How about 7:30? (L301)": {
            "standard": "七点半怎么样？",
            "cases": [
                ("七点三十可以吗？", 4),
                ("七点半行吗？", 4),
                ("七点三十怎么样？", 4),
                ("七个半点怎么样？", 2), # 语序严重错误
                ("六点半怎么样？", 1) # 时间错误
            ]
        }
    }
}