import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
import edge_tts
from fastapi.responses import StreamingResponse

router = APIRouter(tags=["Study Flow"])

@router.get("/study/init")
async def init_daily_study(user_id: str, course_id: int):
    """
    智能学习分发大脑：
    1. 查询用户是否有到期需要复习的题目 (对接 FSRS)。
    2. 如果有，返回 practice 模式。
    3. 如果没有，读取并返回下一课的新内容 (teaching 模式)。
    """
    
    # ==========================================
    # 🧪 开发调试开关 (你可以修改这里来测试前端不同页面)
    # True = 演示“巩固复习”页面
    # False = 演示“新课教学”页面 (加载 Agent 生成的 JSON)
    # ==========================================
    FORCE_PRACTICE_MODE = False

    if FORCE_PRACTICE_MODE:
        # 【模拟】从 user_progress 查出了 2 道需要复习的题目
        return {
            "mode": "practice",
            "data": {
                "pending_items": [
                    {"question_id": 101, "question_type": "CN_TO_EN", "original_text": "你好"},
                    {"question_id": 102, "question_type": "EN_TO_CN", "original_text": "Student"}
                ]
            }
        }
    else:
        # 【真实读取】进入教学模式，加载 Agent 解析出来的课件
        # 定位到你之前生成的 lesson1_structured.json 文件
        json_path = Path(__file__).resolve().parent.parent / "content_builder" / "output_json" / "lesson1_data.json"
        
        if not json_path.exists():
            raise HTTPException(status_code=404, detail="未找到课件数据，请先运行 content_agent.py")

        with open(json_path, "r", encoding="utf-8") as f:
            lesson_data = json.load(f)

        return {
            "mode": "teaching",
            "data": {
                "lesson_content": lesson_data
            }
        }
@router.get("/study/tts")
async def generate_tts(text: str):
    """
    黄金方案 TTS 接口：调用 Edge TTS 实时生成超自然语音
    """
    if not text:
        return {"error": "文本不能为空"}

    # 默认使用微软的“晓晓” (极其自然的年轻女性声音)
    # 如果你想要男声，可以换成 "zh-CN-YunxiNeural"
    voice = "zh-CN-XiaoxiaoNeural"
    
    communicate = edge_tts.Communicate(text, voice, rate="+0%") # rate控制语速

    async def audio_stream():
        # 流式获取音频数据块，极大地降低首字节延迟
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]

    return StreamingResponse(audio_stream(), media_type="audio/mpeg")