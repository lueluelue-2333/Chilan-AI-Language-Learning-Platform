# -*- coding: utf-8 -*-
import json
import os
import sys
import warnings
from pathlib import Path

import dashscope
import voyageai
from dotenv import load_dotenv
from openai import OpenAI
from zai import ZhipuAiClient

try:
    from google import genai as google_genai
    GEMINI_SDK_MODE = "new"
except Exception:
    warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")
    import google.generativeai as google_genai
    GEMINI_SDK_MODE = "legacy"


CURRENT_FILE_PATH = Path(__file__).resolve()
PREPARATION_DIR = CURRENT_FILE_PATH.parent
BACKEND_DIR = PREPARATION_DIR.parent
ENV_PATH = BACKEND_DIR / ".env"
CACHE_PATH = PREPARATION_DIR / "test_case_embedding_cache.json"

load_dotenv(dotenv_path=ENV_PATH)

MODELS = {
    "OA-Large": os.getenv("LLM_EMBED_OPENAI_MODEL_ID", "text-embedding-3-large"),
    "Gemini": os.getenv("LLM_EMBED_GEMINI_MODEL_ID", "gemini-embedding-001"),
    "ZP-3": os.getenv("LLM_EMBED_ZHIPU_MODEL_ID", "embedding-3"),
    "Voyage-4": os.getenv("LLM_EMBED_VOYAGE_MODEL_ID", "voyage-4-large"),
    "Ali": os.getenv("LLM_EMBED_ALI_MODEL_ID", "text-embedding-v4"),
}

OPENAI_API_KEY = os.getenv("LLM_OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("LLM_GEMINI_API_KEY")
ZHIPUAI_API_KEY = os.getenv("LLM_ZHIPU_API_KEY")
VOYAGE_API_KEY = os.getenv("LLM_VOYAGE_API_KEY")
ALI_API_KEY = os.getenv("LLM_ALI_API_KEY")


def ensure_utf8_stdout():
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


class EmbeddingProviderCache:
    def __init__(self, cache_path=CACHE_PATH, auto_flush_every=20):
        self.cache_path = Path(cache_path)
        self.auto_flush_every = auto_flush_every
        self.disk_cache = self._load_disk_cache()
        self.memory_cache = {}
        self.dirty_count = 0
        self.stats = {
            "memory_hits": 0,
            "disk_hits": 0,
            "api_calls": 0,
            "saved_vectors": 0,
        }

        self.client_oa = OpenAI(api_key=OPENAI_API_KEY)
        if GEMINI_SDK_MODE == "legacy":
            google_genai.configure(api_key=GEMINI_API_KEY)
        else:
            self.client_gemini = google_genai.Client(api_key=GEMINI_API_KEY)
        self.client_zp = ZhipuAiClient(api_key=ZHIPUAI_API_KEY)
        self.client_vo = voyageai.Client(api_key=VOYAGE_API_KEY)
        dashscope.api_key = ALI_API_KEY

    def _load_disk_cache(self):
        if not self.cache_path.exists():
            return {}

        try:
            content = json.loads(self.cache_path.read_text(encoding="utf-8"))
            if isinstance(content, dict):
                return content
        except Exception as exc:
            print(f"⚠️ 读取 embedding 缓存失败，将忽略旧缓存。错误: {exc}")
        return {}

    def _save_disk_cache(self):
        tmp_path = self.cache_path.with_suffix(".tmp")
        tmp_path.write_text(
            json.dumps(self.disk_cache, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp_path.replace(self.cache_path)

    def flush(self, force=False):
        if not force and self.dirty_count == 0:
            return
        self._save_disk_cache()
        self.dirty_count = 0

    def _get_from_disk_cache(self, model_tag, model_name, text):
        return (
            self.disk_cache
            .get(model_tag, {})
            .get(model_name, {})
            .get(text)
        )

    def _set_disk_cache(self, model_tag, model_name, text, embedding):
        self.disk_cache.setdefault(model_tag, {}).setdefault(model_name, {})[text] = embedding
        self.dirty_count += 1
        self.stats["saved_vectors"] += 1
        if self.dirty_count >= self.auto_flush_every:
            self.flush()

    def _request_embedding(self, text, model_tag, model_name):
        if "OA" in model_tag:
            return self.client_oa.embeddings.create(input=[text], model=model_name).data[0].embedding
        if "Gemini" in model_tag:
            if GEMINI_SDK_MODE == "legacy":
                model_path = f"models/{model_name}" if not model_name.startswith("models/") else model_name
                return google_genai.embed_content(model=model_path, content=text, task_type="similarity")["embedding"]
            response = self.client_gemini.models.embed_content(
                model=model_name,
                contents=text,
                config={"task_type": "SEMANTIC_SIMILARITY"},
            )
            return response.embeddings[0].values
        if "ZP" in model_tag:
            return self.client_zp.embeddings.create(model=model_name, input=[text]).data[0].embedding
        if "Voyage" in model_tag:
            return self.client_vo.embed([text], model=model_name, output_dimension=2048).embeddings[0]
        if "Ali" in model_tag:
            response = dashscope.TextEmbedding.call(model=model_name, input=[text])
            if response.status_code != 200:
                raise RuntimeError(f"{response.code}: {response.message}")
            return response.output["embeddings"][0]["embedding"]
        raise ValueError(f"未知模型标签: {model_tag}")

    def get_embedding(self, text, model_tag):
        model_name = MODELS[model_tag]
        memory_key = (model_tag, model_name, text)

        if memory_key in self.memory_cache:
            self.stats["memory_hits"] += 1
            return self.memory_cache[memory_key]

        disk_embedding = self._get_from_disk_cache(model_tag, model_name, text)
        if disk_embedding is not None:
            self.stats["disk_hits"] += 1
            self.memory_cache[memory_key] = disk_embedding
            return disk_embedding

        try:
            embedding = self._request_embedding(text, model_tag, model_name)
            self.stats["api_calls"] += 1
            self.memory_cache[memory_key] = embedding
            self._set_disk_cache(model_tag, model_name, text, embedding)
            return embedding
        except Exception as exc:
            print(f"⚠️ 获取 {model_tag} ({model_name}) 失败! 错误信息: {exc}")
            self.memory_cache[memory_key] = None
            return None

    def print_stats(self, prefix=""):
        label = f"{prefix} " if prefix else ""
        print(
            f"{label}缓存统计 | memory_hit={self.stats['memory_hits']} | "
            f"disk_hit={self.stats['disk_hits']} | api_call={self.stats['api_calls']} | "
            f"new_saved={self.stats['saved_vectors']}"
        )


def collect_unique_test_texts(test_suites):
    ordered = []
    seen = set()
    for suite in test_suites.values():
        for content in suite.values():
            texts = [content["standard"]] + [answer for answer, _ in content["cases"]]
            for text in texts:
                if text not in seen:
                    seen.add(text)
                    ordered.append(text)
    return ordered
