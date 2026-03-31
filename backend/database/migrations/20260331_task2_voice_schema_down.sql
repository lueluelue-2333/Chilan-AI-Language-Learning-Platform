BEGIN;

-- Roll back review_logs speech-related columns first.
ALTER TABLE public.review_logs
    DROP CONSTRAINT IF EXISTS review_logs_input_mode_check;

ALTER TABLE public.review_logs
    DROP COLUMN IF EXISTS audio_duration_ms;

ALTER TABLE public.review_logs
    DROP COLUMN IF EXISTS vector_score;

ALTER TABLE public.review_logs
    DROP COLUMN IF EXISTS asr_confidence;

ALTER TABLE public.review_logs
    DROP COLUMN IF EXISTS asr_text;

ALTER TABLE public.review_logs
    DROP COLUMN IF EXISTS input_mode;

-- Roll back language_items extensions.
ALTER TABLE public.language_items
    DROP COLUMN IF EXISTS metadata;

ALTER TABLE public.language_items
    DROP COLUMN IF EXISTS original_pinyin;

COMMIT;
