# Content Builder

`content_builder` 现在只负责内容生成，不直接承担数据库发布职责。

## 目录约定

- `generate.py`
  **Stage 1** 主入口。扫描 `artifacts/raw_materials/` 中的 PDF，生成 lesson JSON 和课文对话音频。
- `render_narration.py`
  **Stage 2** 主入口。读取 `artifacts/output_json/` 中的 lesson JSON，渲染母语旁白音轨并写回 JSON。
- `content_agent.py`
  串联 Task 1-4 的总编排器。
- `llm_providers.py`
  LLM / embedding provider 工厂与适配层。
- `tasks/`
  具体的教材解析、词汇题生成、视频脚本、音频渲染任务实现。
- `scripts/`
  维护脚本、诊断脚本、一次性修复脚本。
- `artifacts/`
  所有运行产物与输入素材目录。

## artifacts

- `artifacts/raw_materials/`
  待处理 PDF。
- `artifacts/output_json/`
  新生成、尚未归档的 lesson JSON。
- `artifacts/synced_json/`
  已确认保留的 lesson JSON 数据。
- `artifacts/output_audio/`
  课文音频、旁白音频等音频产物。
- `artifacts/output_video/`
  渲染得到的视频产物。
- `artifacts/archive_pdfs/`
  已处理完成的 PDF 归档。
- `artifacts/global_vocab_memory.json`
  全局词汇记忆库。
- `artifacts/test_tts_output/`
  TTS 试验脚本输出目录。

## 常用工作流

1. 把教材 PDF 放入 `artifacts/raw_materials/`
2. `python content_builder/generate.py`（Stage 1：生成 lesson JSON + 对话音频，仅本地）
3. `python content_builder/render_narration.py`（Stage 2：渲染旁白音轨，仅本地）
   - 加 `--render-video` 同时渲染讲解视频（需 Node.js）
   - 加 `--lang fr` 生成法语学习者版本
4. 确认 `artifacts/output_json/` 中的数据无误
5. `python database/sync_to_db.py`（Stage 3：上传 R2 + 入库，JSON 移至 `synced_json/`）

## scripts

- `scripts/backfill_vocab_example_pinyin.py`
  回填 vocabulary 例句拼音与 tokens。
- `scripts/reset_pipeline.py`
  清空内容产物、可选清理数据库与 COS。
- `scripts/set_video_urls.py`
  维护讲解视频 URL / COS key。
- `scripts/render_luma_test.py`
  测试 Luma 情景演绎渲染。
- `scripts/check_luma_render.py`
  查询已有 Luma 渲染任务状态。
- `scripts/render_tencent_tts_test.py`
  测试腾讯云逐句课文音频生成。
- `scripts/check_tencent_tts_render.py`
  检查腾讯云逐句音频产物。
- `scripts/test_cosyvoice.py`
  验证 CosyVoice TTS 发音效果。
