BEGIN;

-- 1) Align language_items schema with current application usage.
ALTER TABLE public.language_items
    ADD COLUMN IF NOT EXISTS original_pinyin text;

ALTER TABLE public.language_items
    ALTER COLUMN original_pinyin SET DEFAULT ''::text;

UPDATE public.language_items
SET original_pinyin = ''
WHERE original_pinyin IS NULL;

ALTER TABLE public.language_items
    ADD COLUMN IF NOT EXISTS metadata jsonb;

ALTER TABLE public.language_items
    ALTER COLUMN metadata SET DEFAULT '{}'::jsonb;

UPDATE public.language_items
SET metadata = '{}'::jsonb
WHERE metadata IS NULL;

-- 2) Extend review_logs for speech evaluation observability.
ALTER TABLE public.review_logs
    ADD COLUMN IF NOT EXISTS input_mode character varying(16);

ALTER TABLE public.review_logs
    ALTER COLUMN input_mode SET DEFAULT 'text'::character varying;

UPDATE public.review_logs
SET input_mode = 'text'
WHERE input_mode IS NULL;

ALTER TABLE public.review_logs
    ALTER COLUMN input_mode SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'review_logs_input_mode_check'
          AND conrelid = 'public.review_logs'::regclass
    ) THEN
        ALTER TABLE public.review_logs
            ADD CONSTRAINT review_logs_input_mode_check
            CHECK (input_mode IN ('text', 'speech'));
    END IF;
END $$;

ALTER TABLE public.review_logs
    ADD COLUMN IF NOT EXISTS asr_text text;

ALTER TABLE public.review_logs
    ADD COLUMN IF NOT EXISTS asr_confidence double precision;

ALTER TABLE public.review_logs
    ADD COLUMN IF NOT EXISTS vector_score double precision;

ALTER TABLE public.review_logs
    ADD COLUMN IF NOT EXISTS audio_duration_ms integer;

COMMENT ON COLUMN public.language_items.original_pinyin IS 'Question pinyin for Chinese prompts.';
COMMENT ON COLUMN public.language_items.metadata IS 'Structured extensions (context examples, answer mode, speech config).';
COMMENT ON COLUMN public.review_logs.input_mode IS 'Answer input mode: text or speech.';
COMMENT ON COLUMN public.review_logs.asr_text IS 'ASR transcript used for speech-mode evaluation.';
COMMENT ON COLUMN public.review_logs.asr_confidence IS 'ASR confidence score (0-1).';
COMMENT ON COLUMN public.review_logs.vector_score IS 'Embedding similarity score used by tiered evaluation.';
COMMENT ON COLUMN public.review_logs.audio_duration_ms IS 'Speech recording duration in milliseconds.';

COMMIT;
