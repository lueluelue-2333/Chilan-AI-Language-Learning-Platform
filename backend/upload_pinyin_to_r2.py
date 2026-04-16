"""
一次性脚本：把 backend/pinyin_audio/ 下所有音频文件上传到 R2。
R2 路径约定：zh/audio/pinyin/{filename}

用法：
    cd backend
    python upload_pinyin_to_r2.py

上传成功后本地文件可保留（供开发时 fallback），也可删除（让生产环境走 R2）。
"""

import sys
from pathlib import Path

# 把 backend/ 加入路径，以便 import config
sys.path.insert(0, str(Path(__file__).resolve().parent))

# 加载 .env
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

from services.storage.r2_storage import R2Storage

PINYIN_DIR = Path(__file__).resolve().parent / "pinyin_audio"
R2_PREFIX = "zh/audio/pinyin"


def main():
    if not PINYIN_DIR.exists():
        print(f"❌ 目录不存在: {PINYIN_DIR}")
        sys.exit(1)

    storage = R2Storage.from_env()

    files = sorted(PINYIN_DIR.glob("*"))
    audio_files = [f for f in files if f.is_file() and f.suffix.lower() in {".wav", ".mp3"}]

    if not audio_files:
        print("⚠️  pinyin_audio/ 下没有找到音频文件。")
        sys.exit(0)

    print(f"📂 共找到 {len(audio_files)} 个音频文件，开始上传...\n")

    ok, fail = 0, 0
    for f in audio_files:
        object_key = f"{R2_PREFIX}/{f.name}"
        try:
            result = storage.upload_file(f, object_key)
            print(f"  ✅  {f.name}  →  {result['public_url']}")
            ok += 1
        except Exception as e:
            print(f"  ❌  {f.name}  →  {e}")
            fail += 1

    print(f"\n完成：{ok} 成功，{fail} 失败。")
    if fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
