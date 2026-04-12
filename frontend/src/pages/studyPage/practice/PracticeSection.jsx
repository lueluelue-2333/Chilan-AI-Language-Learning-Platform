import React, { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { Loader2, Send, Sparkles } from 'lucide-react';
import apiClient from '../../../api/apiClient';
import { claimGlobalAudio, releaseGlobalAudio } from '../../../utils/audioPlayback';
import AIThinkingIndicator from './components/AIThinkingIndicator';
import PracticeAnswerPanel from './components/PracticeAnswerPanel';
import PracticeFeedbackPanel from './components/PracticeFeedbackPanel';
import PracticePromptCard from './components/PracticePromptCard';
import usePracticeKeyboardShortcuts from './hooks/usePracticeKeyboardShortcuts';
import usePracticeKnowledgeDetails from './hooks/usePracticeKnowledgeDetails';
import usePracticeFlow from './hooks/usePracticeFlow';
import useSpeechPractice from './hooks/useSpeechPractice';

const fadeInUp = {
    hidden: { opacity: 0, y: 15 },
    show: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 100, damping: 20 } }
};

const staggerContainer = {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: { staggerChildren: 0.08 } }
};

export default function PracticeSection({ questions, isReview, onAllDone, userId, courseId, lessonId, initialIndex = 0 }) {
    const { t, i18n } = useTranslation();
    const [currentIndex, setCurrentIndex] = useState(0);
    const [isFocused, setIsFocused] = useState(false);

    const inputRef = useRef(null);
    const speechActionsRef = useRef(null);
    const speechPrimaryButtonRef = useRef(null);
    const speechSubmitButtonRef = useRef(null);
    const lastAutoPlayedKeyRef = useRef('');

    useEffect(() => {
        const safeIndex = Number.isInteger(initialIndex)
            ? Math.max(0, Math.min(initialIndex, Math.max(questions.length - 1, 0)))
            : 0;
        setCurrentIndex(safeIndex);
    }, [initialIndex, questions]);

    const currentQuestion = questions[currentIndex];

    const {
        speechMode,
        speechConfig,
        isRecording,
        isTranscribing,
        speechTranscript,
        speechMeta,
        recordingSeconds,
        recordAttempts,
        speechError,
        liveWaveform,
        lowConfidence,
        setSpeechError,
        handleStartRecording,
        handleStopRecording,
        cleanupMedia,
        resetSpeechState
    } = useSpeechPractice({
        currentQuestion,
        onTranscriptReady: null,
        onResetFeedback: null
    });

    const {
        userAnswer,
        setUserAnswer,
        lastSubmittedAnswer,
        isEvaluating,
        feedback,
        setFeedback,
        knowledgeDetails,
        setKnowledgeDetails,
        typedFeedbackMessage,
        activeAnswer,
        speechShouldRetry,
        hasSpeechTranscript,
        isPerfectFeedback,
        isTypingFeedback,
        isResubmitDisabled,
        feedbackTone,
        handleSubmit,
    } = usePracticeFlow({
        currentQuestion,
        userId,
        t,
        speechMode,
        speechTranscript,
        speechMeta,
        isRecording,
        isTranscribing,
        lowConfidence,
        setSpeechError,
        cleanupMedia,
        resetSpeechState,
    });

    useEffect(() => {
        setUserAnswer(speechMode ? speechTranscript : '');
    }, [speechMode, speechTranscript, setUserAnswer]);

    const primaryButtonClass = 'bg-blue-600 text-white hover:bg-blue-700 shadow-blue-100';
    const secondaryButtonClass = 'bg-slate-900 text-white hover:bg-slate-800 shadow-slate-200';
    const textPromptLabel = currentQuestion?.question_type === 'CN_TO_EN'
        ? t('practice_prompt_cn_to_en')
        : t('practice_prompt_en_to_cn');
    const speechPreviewText = speechTranscript
        || (isRecording
            ? '正在聆听，请开始说话。'
            : isTranscribing
                ? '录音已结束，正在生成识别结果。'
                : '还没有识别结果，点击下方按钮开始录音。');
    const speechInlineHint = isTranscribing
        ? { tone: 'bg-sky-50 text-sky-700 border-sky-100', text: '已经收到录音，正在转换成文字。', emphasis: 'info' }
        : speechError
            ? {
                tone: lowConfidence ? 'bg-amber-50 text-amber-700 border-amber-100' : 'bg-rose-50 text-rose-700 border-rose-100',
                text: speechError,
                emphasis: lowConfidence ? 'warning' : 'error'
            }
            : null;
    const config = feedbackTone;

    const playAudio = (text) => {
        if (!text) return;
        const API_BASE = import.meta.env.VITE_APP_API_BASE_URL;
        const audio = new Audio(`${API_BASE}/study/tts?text=${encodeURIComponent(text)}`);
        claimGlobalAudio(audio);
        audio.onpause = () => releaseGlobalAudio(audio);
        audio.onended = () => releaseGlobalAudio(audio);
        audio.onerror = () => releaseGlobalAudio(audio);
        audio.play().catch(() => releaseGlobalAudio(audio));
    };

    const focusAndMoveCursorToEnd = () => {
        if (inputRef.current) {
            const len = userAnswer.length;
            inputRef.current.focus();
            inputRef.current.setSelectionRange(len, len);
        }
    };

    const handleNext = () => {
        if (currentIndex < questions.length - 1) {
            setCurrentIndex((prev) => prev + 1);
        } else {
            onAllDone();
        }
    };

    useEffect(() => {
        if (!currentQuestion || speechMode || currentQuestion.question_type !== 'CN_TO_EN') return;

        const questionKey = `${currentQuestion.item_id || currentQuestion.question_id || currentIndex}:${currentQuestion.original_text || ''}`;
        if (lastAutoPlayedKeyRef.current === questionKey) return;

        lastAutoPlayedKeyRef.current = questionKey;
        const timer = setTimeout(() => {
            playAudio(currentQuestion.original_text);
        }, 250);

        return () => clearTimeout(timer);
    }, [currentQuestion, currentIndex, speechMode]);

    useEffect(() => {
        if (!questions?.length || !userId || !courseId || !lessonId || isReview) return;
        const syncProgress = async () => {
            try {
                await apiClient.post('/study/practice_progress', {
                    user_id: userId,
                    course_id: Number(courseId),
                    lesson_id: lessonId,
                    current_index: currentIndex,
                });
            } catch (e) {
                console.error('同步练习进度失败:', e);
            }
        };
        syncProgress();
    }, [currentIndex, questions, userId, courseId, lessonId, isReview]);

    useEffect(() => {
        if (speechMode) return;
        if (!feedback && !inputRef.current) return;

        if (!feedback && inputRef.current) {
            const timer = setTimeout(() => { focusAndMoveCursorToEnd(); }, 100);
            return () => clearTimeout(timer);
        }
        if (feedback && feedback.level === 1) {
            focusAndMoveCursorToEnd();
        }
    }, [currentIndex, feedback, speechMode, userAnswer]);

    usePracticeKnowledgeDetails({
        feedback,
        currentQuestion,
        setKnowledgeDetails,
    });

    useEffect(() => {
        if (!speechMode) return;
        const timer = setTimeout(() => {
            const shouldFocusSubmit = !feedback && !isRecording && !isTranscribing && hasSpeechTranscript && !lowConfidence && !speechShouldRetry;
            if (shouldFocusSubmit) {
                speechSubmitButtonRef.current?.focus();
            } else {
                speechPrimaryButtonRef.current?.focus();
            }
        }, 80);
        return () => clearTimeout(timer);
    }, [speechMode, currentIndex, feedback, isRecording, isTranscribing, hasSpeechTranscript, lowConfidence, speechShouldRetry]);

    usePracticeKeyboardShortcuts({
        speechMode,
        feedback,
        inputRef,
        userAnswer,
        lastSubmittedAnswer,
        handleSubmit,
        handleNext,
        speechActionsRef,
        speechTranscript,
        isRecording,
        isTranscribing,
        lowConfidence,
        speechShouldRetry,
        handleStartRecording,
        handleStopRecording,
    });

    if (!currentQuestion) return null;

    const speechPrimaryLabel = isRecording ? '结束录音' : hasSpeechTranscript ? '重新录音' : '开始录音';
    const speechPrimaryTone = isRecording || !hasSpeechTranscript || lowConfidence || speechShouldRetry
        ? primaryButtonClass
        : secondaryButtonClass;

    return (
        <AnimatePresence mode="wait">
            <motion.div
                key={`practice-${i18n.language}`}
                variants={staggerContainer}
                initial="hidden"
                animate="show"
                exit={{ opacity: 0, y: -10, transition: { duration: 0.18 } }}
                className="max-w-5xl mx-auto px-6 pt-20 pb-0"
            >
                <motion.div variants={fadeInUp} initial="hidden" animate="show" className="flex items-center justify-center gap-5 mb-8">
                    <div className="flex items-center gap-3">
                        <Sparkles className="text-blue-500" size={28} />
                        <h1 className="text-5xl font-black text-slate-900 tracking-tight">
                            {isReview ? t('practice_title_review') : t('practice_title_lesson')}
                        </h1>
                    </div>
                    <div className="px-5 py-1.5 bg-slate-200/50 rounded-full text-xl font-black text-slate-500 tracking-tighter">
                        {currentIndex + 1} / {questions.length}
                    </div>
                </motion.div>

                <PracticePromptCard
                    fadeInUp={fadeInUp}
                    speechMode={speechMode}
                    promptLabel={textPromptLabel}
                    originalText={currentQuestion.original_text}
                />

                <motion.div variants={fadeInUp} initial="hidden" animate="show" className="bg-white p-8 md:p-10 rounded-[2.5rem] shadow-xl shadow-slate-200/40 border border-slate-100">
                    <PracticeAnswerPanel
                        speechMode={speechMode}
                        value={userAnswer}
                        inputRef={inputRef}
                        onChange={(e) => setUserAnswer(e.target.value)}
                        onFocus={() => setIsFocused(true)}
                        onBlur={() => setIsFocused(false)}
                        placeholder={isFocused ? '' : t('practice_input_placeholder')}
                        disabled={feedback && feedback.level >= 2}
                        isFocused={isFocused}
                        statusTone={feedback ? config?.inputTone : null}
                        isRecording={isRecording}
                        isTranscribing={isTranscribing}
                        recordAttempts={recordAttempts}
                        maxDurationSec={speechConfig.max_duration_sec}
                        recordingSeconds={recordingSeconds}
                        liveWaveform={liveWaveform}
                        speechPreviewText={speechPreviewText}
                        speechInlineHint={speechInlineHint}
                        onPrimaryAction={isRecording ? handleStopRecording : handleStartRecording}
                        primaryLabel={speechPrimaryLabel}
                        primaryDisabled={isTranscribing}
                        showSubmit={hasSpeechTranscript && !isRecording && !isTranscribing}
                        onSubmit={handleSubmit}
                        submitDisabled={!activeAnswer.trim() || isEvaluating || lowConfidence || speechShouldRetry}
                        isEvaluating={isEvaluating}
                        primaryButtonRef={speechMode ? speechPrimaryButtonRef : undefined}
                        submitButtonRef={speechMode ? speechSubmitButtonRef : undefined}
                        actionsRef={speechMode ? speechActionsRef : undefined}
                        primaryButtonClass={speechPrimaryTone}
                        secondaryButtonClass={secondaryButtonClass}
                    />

                    <AnimatePresence mode="wait">
                        {!feedback && !isEvaluating ? (
                            !speechMode && (
                                <motion.button
                                    key="text-submit"
                                    whileTap={{ scale: 0.98 }}
                                    onClick={handleSubmit}
                                    disabled={!userAnswer.trim() || isEvaluating}
                                    className={`w-full py-5 rounded-[1.2rem] font-black text-xl disabled:bg-slate-200 transition-all flex items-center justify-center gap-3 shadow-lg ${primaryButtonClass}`}
                                >
                                    {isEvaluating ? <Loader2 className="animate-spin" /> : <Send size={22} />}
                                    {isEvaluating ? t('practice_evaluating') : t('practice_submit')}
                                </motion.button>
                            )
                        ) : feedback ? (
                            <PracticeFeedbackPanel
                                feedback={feedback}
                                isPerfectFeedback={isPerfectFeedback}
                                isTypingFeedback={isTypingFeedback}
                                typedFeedbackMessage={typedFeedbackMessage}
                                speechMode={speechMode}
                                onRetry={speechMode ? handleStartRecording : handleSubmit}
                                onSkip={handleNext}
                                onNext={handleNext}
                                retryDisabled={speechMode ? (isRecording || isTranscribing) : isResubmitDisabled}
                                currentIndex={currentIndex}
                                totalQuestions={questions.length}
                                isBusy={isTranscribing}
                                primaryButtonRef={speechMode ? speechPrimaryButtonRef : undefined}
                                actionsRef={speechMode ? speechActionsRef : undefined}
                                primaryButtonClass={primaryButtonClass}
                                secondaryButtonClass={secondaryButtonClass}
                                currentQuestion={currentQuestion}
                                knowledgeDetails={knowledgeDetails}
                            />
                        ) : (
                            <motion.div
                                key="thinking-area"
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -3, scale: 0.985, filter: 'blur(2px)' }}
                                transition={{ duration: 0.28, ease: 'easeOut' }}
                                className="space-y-5"
                            >
                                <AIThinkingIndicator label="AI 导师正在分析你的回答..." />
                            </motion.div>
                        )}
                    </AnimatePresence>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    );
}
