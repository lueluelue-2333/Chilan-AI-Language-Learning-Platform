# -*- coding: utf-8 -*-
import sys

from embedding_provider_cache import (
    EmbeddingProviderCache,
    MODELS,
    collect_unique_test_texts,
    ensure_utf8_stdout,
)

try:
    from test_cases import test_suites
except ImportError:
    print("❌ 错误：请确保同目录下存在 test_cases.py 文件")
    sys.exit(1)


ensure_utf8_stdout()


def run_precompute():
    service = EmbeddingProviderCache(auto_flush_every=10)
    texts = collect_unique_test_texts(test_suites)
    total_texts = len(texts)
    total_tasks = total_texts * len(MODELS)
    current_task = 0

    print("🧰 开始预生成 test_cases embedding 缓存...")
    print(f"📚 共 {total_texts} 条唯一文本，{len(MODELS)} 个模型，总任务数 {total_tasks}。")

    for text_index, text in enumerate(texts, start=1):
        print(f"\n📝 文本 {text_index}/{total_texts}: {text[:80]}")
        for model_index, model_tag in enumerate(MODELS, start=1):
            current_task += 1
            print(f"   🔹 [{current_task}/{total_tasks}] {model_tag}")
            service.get_embedding(text, model_tag)

    service.flush(force=True)
    service.print_stats(prefix="✅ [Precompute]")
    print("🎉 test_cases embedding 缓存预生成完成。")


if __name__ == "__main__":
    run_precompute()
