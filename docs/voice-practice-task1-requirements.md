# 语音练习题任务一（需求冻结）v1.0

- 目标: 冻结“课后语音作答题”第一版产品规则，作为后续开发的唯一口径。
- 范围: Learn Chinese by English 主流程（study page + evaluate API）。

## 1. 产品定义（冻结）

- 新题型代码: `EN_TO_CN_SPEAK`
- 用户任务: 阅读英文题干，口头说出中文答案。
- 判题链路: `语音 -> ASR 转写文本 -> Tier1 正则 -> Tier2 Embedding -> Tier3 LLM`
- 关键说明: Embedding 仅用于“文本语义相似度”，不负责语音识别。

## 2. MVP 范围（冻结）

- 仅新增 `EN_TO_CN_SPEAK`，不改动现有 `CN_TO_EN` / `EN_TO_CN` 行为。
- 先不保存原始音频文件，仅保存评测必要日志（见第 6 节）。
- 每课建议生成 3~5 道语音题（由内容生成任务实现）。

## 3. 评分规则 v1（冻结）

- 输入文本: 语音题统一使用 ASR 返回文本（`asr_text`）进入三层判题。
- Tier1（精确匹配）:
  - 归一化后与任一 `standard_answers` 完全一致 -> 直接通过。
- Tier2（向量相似）:
  - `sim_score >= 0.88` -> 直接通过。
  - `0.78 <= sim_score < 0.88` -> 进入 Tier3 LLM 复核。
  - `sim_score < 0.78` -> 直接不通过。
- Tier3（LLM 复核）:
  - 仅在灰区（`[0.78, 0.88)`）触发。
  - 输出继续沿用现有结构：`level/isCorrect/message/judgedBy`。

## 4. ASR 与重录策略（冻结）

- ASR 低置信度阈值: `asr_confidence < 0.60`
- 低置信度处理: 不进判题，直接提示“请重录”。
- 单题最大重录次数: `3` 次。
- 单次录音上限: `15` 秒。
- 空转写处理: `asr_text` 为空时按低置信度处理。

## 5. 交互规则（冻结）

- 语音题展示按钮: `开始录音 -> 停止录音 -> 转写预览 -> 提交判题`。
- 用户可在提交前手动重录，不允许直接编辑 `asr_text`（MVP）。
- 判题失败反馈优先包含:
  - 识别到的文本（用于纠错）
  - 建议标准表达（简短）

## 6. 数据与接口契约（冻结）

### 6.1 题目数据（language_items.metadata）

语音题在 `metadata` 中至少包含:

```json
{
  "answer_mode": "speech",
  "speech_eval_config": {
    "pass_threshold": 0.88,
    "review_threshold": 0.78,
    "min_asr_confidence": 0.60,
    "max_attempts": 3,
    "max_duration_sec": 15,
    "allow_paraphrase": true
  }
}
```

### 6.2 判题入参（/study/evaluate）

在现有请求体基础上扩展:

- `input_mode`: `"text" | "speech"`
- `asr_text`: string（speech 模式必填）
- `audio_meta`: object（可选，含 `duration_ms/confidence/provider`）

### 6.3 评测日志（review_logs 扩展字段）

MVP 记录:

- `input_mode`
- `asr_text`
- `asr_confidence`
- `vector_score`
- `audio_duration_ms`

## 7. 非目标（冻结）

- 不做发音打分（phoneme/pronunciation scoring）。
- 不做方言纠音策略。
- 不做多语种课程复用（先固定中文课程）。

## 8. 验收标准（任务一完成标准）

- 团队对题型、阈值、重录、接口字段无歧义。
- 后续任务（二到十）必须引用本文件，不得自定义阈值。
- 阈值调整需改版本号（`v1.0 -> v1.1`）并记录变更原因。
