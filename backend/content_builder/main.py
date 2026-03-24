import os
import json
import time
import re
import shutil
from pathlib import Path
from dotenv import load_dotenv

# 引入我们刚才拆分好的工厂和总代理
from llm_providers import LLMFactory
from content_agent import ContentCreatorAgent

def main():
    # 1. 绝对路径配置
    CURRENT_DIR = Path(__file__).resolve().parent          # backend/content_builder/
    BASE_DIR = CURRENT_DIR.parent                          # backend/
    
    # 向上寻找 backend/.env 文件
    load_dotenv(dotenv_path=BASE_DIR / ".env")
    
    # 2. 引擎初始化
    try:
        provider = LLMFactory.create_provider()
        agent = ContentCreatorAgent(provider=provider, memory_dir=CURRENT_DIR)
        print(f"🔧 当前激活模型引擎: {type(provider).__name__}")
    except Exception as e:
        print(f"❌ 系统初始化失败: {e}")
        return

    # 3. 文件夹管理
    raw_dir = CURRENT_DIR / "raw_materials"
    output_dir = CURRENT_DIR / "output_json"
    archive_dir = CURRENT_DIR / "archive_pdfs"
    
    for d in [raw_dir, output_dir, archive_dir]:
        d.mkdir(parents=True, exist_ok=True)
    
    # 4. 扫描执行
    pdf_files = list(raw_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"📭 raw_materials 为空，没有需要处理的 PDF。")
        return

    print(f"📦 发现 {len(pdf_files)} 个新教材准备处理！\n" + "="*45)

    for pdf_path in pdf_files:
        file_name = pdf_path.stem
        numbers = re.findall(r'\d+', file_name)
        if not numbers:
            print(f"⚠️ 警告：无法从文件名 {file_name} 提取编号，跳过。")
            continue
            
        lesson_id = int(numbers[0])
        result = agent.parse_textbook(str(pdf_path), lesson_id=lesson_id)
        
        if result:
            # 数据落盘
            output_file = output_dir / f"lesson{lesson_id}_data.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"✅ 管线全部完成，数据落盘: {output_file.name}")
            
            # PDF 归档
            try:
                archive_path = archive_dir / pdf_path.name
                if archive_path.exists():
                    archive_path = archive_dir / f"{pdf_path.stem}_{int(time.time())}.pdf"
                shutil.move(str(pdf_path), str(archive_path))
                print(f"📁 教材已安全归档。")
            except Exception as e:
                print(f"⚠️ 归档文件时发生错误: {e}")
        else:
            print(f"❌ {file_name}.pdf 处理失败，保留在原处等待排查。")
        
        print("-" * 45)

if __name__ == "__main__":
    main()