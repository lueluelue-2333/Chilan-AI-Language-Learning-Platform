import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import { Loader2, Send, CheckCircle2, XCircle, Sparkles } from 'lucide-react';

const fadeInUp = {
    hidden: { opacity: 0, y: 30 },
    show: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 100, damping: 20 } }
};

export default function PracticeSection({ questions, isReview, onAllDone }) {
    const [currentIndex, setCurrentIndex] = useState(0);
    const [userAnswer, setUserAnswer] = useState('');
    const [isEvaluating, setIsEvaluating] = useState(false);
    const [feedback, setFeedback] = useState(null);
    
    // 🌟 1. 引用答题框，用于控制聚焦
    const inputRef = useRef(null);

    const currentQuestion = questions[currentIndex];

    // 🌟 2. 自动聚焦逻辑：进入新题或清除反馈后，立刻聚焦
    useEffect(() => {
        if (!feedback && !isEvaluating && inputRef.current) {
            // 给微小的延迟确保 DOM 已经渲染完毕
            const timer = setTimeout(() => {
                inputRef.current.focus();
            }, 100);
            return () => clearTimeout(timer);
        }
    }, [currentIndex, feedback, isEvaluating]);

    // 监听键盘 Enter
    useEffect(() => {
        const handleEnter = (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (feedback) handleNext();
                else if (userAnswer.trim() && !isEvaluating) handleSubmit();
            }
        };
        window.addEventListener('keydown', handleEnter);
        return () => window.removeEventListener('keydown', handleEnter);
    }, [userAnswer, feedback, isEvaluating]);

    const handleSubmit = async () => {
        setIsEvaluating(true);
        try {
            const res = await axios.post(`http://127.0.0.1:8000/study/evaluate`, {
                user_id: localStorage.getItem('chilan_user_id') || 'test-user-id',
                lesson_id: currentQuestion.lesson_id || 101,
                question_id: currentQuestion.question_id,
                question_type: currentQuestion.question_type,
                original_text: currentQuestion.original_text,
                standard_answers: Array.isArray(currentQuestion.standard_answers) ? currentQuestion.standard_answers : [currentQuestion.standard_answers],
                user_answer: userAnswer
            });
            setFeedback(res.data.data);
        } catch (e) {
            setFeedback({ isCorrect: false, message: "判题服务连接失败，请重试。" });
        } finally {
            setIsEvaluating(false);
        }
    };

    const handleNext = () => {
        if (currentIndex < questions.length - 1) {
            setCurrentIndex(prev => prev + 1);
            setUserAnswer('');
            setFeedback(null);
        } else {
            onAllDone();
        }
    };

    if (!currentQuestion) return null;

    return (
        // 🌟 3. 增加 pt-32 确保远离 Navbar，max-w-4xl 让布局更开阔
        <div className="max-w-4xl mx-auto px-6 pt-32 pb-20">
            {/* 顶部标题：字号加大，增加呼吸感 */}
            <motion.div variants={fadeInUp} initial="hidden" animate="show" className="text-center mb-16">
                <div className="flex items-center justify-center gap-3 mb-4">
                    <Sparkles className="text-blue-500" size={28} />
                    <h1 className="text-5xl font-black text-slate-900 tracking-tight">
                        {isReview ? "智能巩固复习" : "随堂强化练习"}
                    </h1>
                </div>
                <div className="inline-block px-6 py-2 bg-slate-200/50 rounded-full text-sm font-black text-slate-500 tracking-widest uppercase">
                    Task {currentIndex + 1} of {questions.length}
                </div>
            </motion.div>

            {/* 题目展示：字号大幅提升至 text-5xl */}
            <motion.div variants={fadeInUp} initial="hidden" animate="show" className="text-center mb-16">
                <span className="text-base font-bold text-blue-500 uppercase tracking-[0.3em] block mb-4">
                    {currentQuestion.question_type === 'CN_TO_EN' ? 'Translate to English' : '请翻译成中文'}
                </span>
                <p className="text-4xl md:text-5xl font-black text-slate-900 leading-tight px-4">
                    “{currentQuestion.original_text}”
                </p>
            </motion.div>

            {/* 输入区域：加厚阴影和更大的内边距 */}
            <motion.div variants={fadeInUp} initial="hidden" animate="show" className="bg-white p-10 md:p-12 rounded-[3rem] shadow-xl shadow-slate-200/50 border border-slate-100">
                <textarea 
                    ref={inputRef} // 🌟 挂载 Ref
                    value={userAnswer}
                    onChange={(e) => setUserAnswer(e.target.value)}
                    disabled={isEvaluating || feedback}
                    placeholder="在这里输入你的答案..."
                    // 🌟 字号提升至 text-2xl，增加行高
                    className="w-full h-40 p-6 bg-slate-50 border-2 border-slate-100 rounded-[2rem] text-2xl font-medium focus:border-blue-500 focus:bg-white transition-all outline-none mb-8 resize-none leading-relaxed"
                />

                <AnimatePresence mode="wait">
                    {!feedback ? (
                        <motion.button 
                            key="submit-btn"
                            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                            onClick={handleSubmit}
                            disabled={!userAnswer.trim() || isEvaluating}
                            className="w-full py-6 bg-slate-900 text-white rounded-[1.5rem] font-black text-xl hover:bg-blue-600 disabled:bg-slate-200 transition-all flex items-center justify-center gap-3 shadow-lg shadow-slate-200"
                        >
                            {isEvaluating ? <Loader2 className="animate-spin" /> : <Send size={24} />}
                            {isEvaluating ? 'AI 导师正在阅卷...' : '提交答案'}
                        </motion.button>
                    ) : (
                        <motion.div 
                            key="feedback-area"
                            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                            className="space-y-6"
                        >
                            <div className={`p-8 rounded-[2rem] border-2 ${
                                feedback.isCorrect 
                                ? 'bg-green-50 border-green-100' 
                                : 'bg-red-50 border-red-100'
                            }`}>
                                <div className="flex gap-5">
                                    {feedback.isCorrect 
                                        ? <CheckCircle2 className="text-green-500 shrink-0" size={32} /> 
                                        : <XCircle className="text-red-500 shrink-0" size={32} />
                                    }
                                    <div>
                                        <h4 className={`text-xl font-black mb-2 ${feedback.isCorrect ? 'text-green-800' : 'text-red-800'}`}>
                                            {feedback.isCorrect ? '太棒了，完全正确！' : 'AI 导师的优化建议'}
                                        </h4>
                                        {/* 评价文字也同步放大 */}
                                        <p className="text-slate-700 text-lg leading-relaxed font-medium">
                                            {feedback.message}
                                        </p>
                                    </div>
                                </div>
                            </div>
                            <button 
                                onClick={handleNext} 
                                className="w-full py-6 bg-blue-600 text-white rounded-[1.5rem] font-black text-xl hover:bg-blue-700 transition-all flex items-center justify-center shadow-lg shadow-blue-100"
                            >
                                {currentIndex === questions.length - 1 ? '完成所有练习' : '进入下一题'} 
                                <span className="ml-3 text-blue-200 font-normal text-sm tracking-widest uppercase">Press Enter</span>
                            </button>
                        </motion.div>
                    )}
                </AnimatePresence>
            </motion.div>
        </div>
    );
}