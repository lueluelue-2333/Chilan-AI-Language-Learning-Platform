import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Loader2, ArrowLeft, Eye, EyeOff, Volume2 } from 'lucide-react';

export default function StudyPage() {
    const params = useParams();
    const courseId = params.courseId || params.id || params.category; 
    
    const navigate = useNavigate();
    const userId = localStorage.getItem('chilan_user_id') || 'test-user-id';

    const [mode, setMode] = useState('loading'); 
    const [studyData, setStudyData] = useState(null);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (courseId) {
            initDailyStudy();
        } else {
            setError("未找到课程 ID 参数");
            setMode('error');
        }
    }, [courseId]);

    const initDailyStudy = async () => {
        try {
            const response = await axios.get(`http://127.0.0.1:8000/study/init`, {
                params: { course_id: courseId, user_id: userId }
            });
            setMode(response.data.mode);
            setStudyData(response.data.data);
        } catch (err) {
            console.error("加载学习计划失败", err);
            setError("获取课件失败，请确保后端正常运行且文件路径正确。");
            setMode('error');
        }
    };

    if (mode === 'loading') {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center bg-slate-50 text-slate-500">
                <Loader2 className="animate-spin w-12 h-12 mb-4 text-blue-500" />
                <p>正在为你生成今日自适应学习计划...</p>
            </div>
        );
    }

    if (mode === 'error') {
        return (
            <div className="min-h-screen flex flex-col items-center justify-center bg-slate-50 text-red-500">
                <p>{error}</p>
                <button onClick={() => navigate(-1)} className="mt-4 px-4 py-2 bg-slate-200 text-slate-700 rounded-lg">返回</button>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-slate-50 pb-20">
            <div className="bg-white shadow-sm px-8 py-4 mb-8 flex items-center">
                <button onClick={() => navigate(-1)} className="flex items-center text-slate-500 hover:text-blue-600 transition">
                    <ArrowLeft className="mr-2" size={20} /> 返回教室
                </button>
            </div>

            {mode === 'practice' && (
                <div className="max-w-3xl mx-auto p-8 text-center bg-white rounded-2xl shadow-sm">
                    <h1 className="text-3xl font-black text-orange-600 mb-8">🧠 智能巩固复习</h1>
                    <p className="mb-8">你有 {studyData.pending_items?.length} 道题目需要复习</p>
                    <button onClick={initDailyStudy} className="px-8 py-3 bg-slate-900 text-white rounded-xl hover:bg-slate-800 transition">模拟完成复习</button>
                </div>
            )}
            
            {mode === 'teaching' && (
                <TeachingMode 
                    lessonData={studyData.lesson_content} 
                    onNextLesson={() => navigate(-1)} 
                />
            )}
        </div>
    );
}

// ==========================================
// 子组件：TeachingMode
// ==========================================
function TeachingMode({ lessonData, onNextLesson }) {
    // 🌟 状态区：同时控制拼音和翻译的显示
    const [showPinyin, setShowPinyin] = useState(true);
    const [showTranslation, setShowTranslation] = useState(true); // 新增控制翻译显示的状态

    if (!lessonData) return <div>数据缺失</div>;

    const { lesson_metadata, course_content, aigc_visual_prompt } = lessonData;
    const { dialogues, vocabulary } = course_content;

    const playAudio = (text) => {
        if (!text) return;
        const cleanText = text.replace(/<[^>]+>/g, '').replace(/\*\*/g, '');
        const audioUrl = `http://127.0.0.1:8000/study/tts?text=${encodeURIComponent(cleanText)}`;
        const audio = new Audio(audioUrl);
        audio.play().catch(err => console.error("音频播放失败:", err));
    };

    const formatHighlightedText = (text) => {
        if (!text) return "";
        const parts = text.split(/(?:\*\*|<b>)(.*?)(?:\*\*|<\/b>)/g);
        return parts.map((part, index) =>
            index % 2 === 1 ? (
                <strong key={index} className="text-blue-600 font-black px-0.5">{part}</strong>
            ) : (
                <span key={index}>{part}</span>
            )
        );
    };

    const allLines = dialogues?.flatMap(turn => turn.lines || []) || [];

    return (
        <div className="max-w-4xl mx-auto px-6">
            <h1 className="text-4xl font-black text-slate-800 mb-2">
                {lesson_metadata?.title || "未命名课程"}
            </h1>
            <p className="text-slate-500 mb-8 font-medium">Lesson ID: {lesson_metadata?.lesson_id}</p>
            
            <div className="w-full aspect-video bg-slate-900 rounded-3xl flex flex-col items-center justify-center mb-12 shadow-2xl relative overflow-hidden group">
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 to-transparent z-10"></div>
                <p className="text-white z-20 font-bold tracking-widest opacity-50 mb-2">🎬 GOOGLE VEO / AIGC 视频位</p>
                <p className="text-slate-400 z-20 text-sm max-w-lg text-center px-4 italic line-clamp-2">
                    Prompt: "{aigc_visual_prompt}"
                </p>
            </div>

            {/* 🔥 课文对话区 */}
            <section className="mb-12">
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-6 gap-4">
                    <h2 className="text-2xl font-black flex items-center gap-2">
                        <span>💬</span> 课文对话
                    </h2>
                    
                    {/* 🌟 按钮区：组合了拼音和翻译开关 */}
                    <div className="flex items-center gap-3">
                        <button 
                            onClick={() => setShowPinyin(!showPinyin)}
                            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold transition-all ${
                                showPinyin ? 'bg-blue-100 text-blue-700 hover:bg-blue-200' : 'bg-slate-200 text-slate-600 hover:bg-slate-300'
                            }`}
                        >
                            {showPinyin ? <Eye size={16} /> : <EyeOff size={16} />}
                            {showPinyin ? '隐藏拼音' : '显示拼音'}
                        </button>
                        
                        {/* 新增：翻译开关按钮 */}
                        <button 
                            onClick={() => setShowTranslation(!showTranslation)}
                            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold transition-all ${
                                showTranslation ? 'bg-indigo-100 text-indigo-700 hover:bg-indigo-200' : 'bg-slate-200 text-slate-600 hover:bg-slate-300'
                            }`}
                        >
                            {showTranslation ? <Eye size={16} /> : <EyeOff size={16} />}
                            {showTranslation ? '隐藏翻译' : '显示翻译'}
                        </button>
                    </div>
                </div>

                <div className="flex flex-col gap-6 bg-white p-6 md:p-8 rounded-3xl shadow-sm border border-slate-100">
                    {allLines.map((line, idx) => {
                        const isLeft = idx % 2 === 0; 
                        
                        return (
                            <div key={idx} className={`flex flex-col ${isLeft ? 'items-start' : 'items-end'}`}>
                                <span className="text-xs font-bold text-slate-400 mb-1 px-2 uppercase tracking-wider">
                                    {line.role}
                                </span>
                                
                                <div className={`px-5 py-4 rounded-3xl max-w-[85%] md:max-w-[70%] shadow-sm group ${
                                    isLeft 
                                    ? 'bg-slate-50 border border-slate-100 rounded-tl-sm' 
                                    : 'bg-blue-50/80 border border-blue-100 rounded-tr-sm'
                                }`}>
                                    <div className="relative">
                                        {showPinyin && line.pinyin && (
                                            <p className="text-sm text-slate-500 font-mono mb-1 leading-none transition-opacity duration-300">
                                                {line.pinyin}
                                            </p>
                                        )}
                                        
                                        <div className="flex items-center gap-3">
                                            <p className="text-xl text-slate-800 tracking-wide">
                                                {formatHighlightedText(line.chinese)}
                                            </p>
                                            
                                            <button 
                                                onClick={() => playAudio(line.chinese)}
                                                className="opacity-0 group-hover:opacity-100 p-1.5 text-blue-500 hover:bg-blue-100 hover:text-blue-700 rounded-full transition-all"
                                                title="朗读此句"
                                            >
                                                <Volume2 size={18} />
                                            </button>
                                        </div>

                                        {/* 🌟 修改点：在此处加入 {showTranslation && ...} 条件渲染判断 */}
                                        {showTranslation && line.english && (
                                            <p className="text-xs text-slate-400 italic mt-2 font-medium transition-opacity duration-300">
                                                {line.english}
                                            </p>
                                        )}
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </section>

            {/* 生词表区（保持不变） */}
            <section className="mb-12">
                <h2 className="text-2xl font-black mb-6 flex items-center gap-2">
                    <span>🔤</span> 本课生词
                </h2>
                <div className="grid grid-cols-1 gap-4">
                    {vocabulary?.map((vocab, idx) => (
                        <div key={idx} className="flex flex-col p-5 bg-white border border-slate-100 rounded-3xl shadow-sm hover:shadow-md transition">
                            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                                <div className="flex items-center gap-4">
                                    <span className="text-3xl font-black text-slate-800">{vocab.word}</span>
                                    
                                    <button 
                                        onClick={() => playAudio(vocab.word)}
                                        className="p-2 bg-blue-50 text-blue-500 hover:bg-blue-600 hover:text-white rounded-full transition-colors shadow-sm"
                                        title="朗读单词"
                                    >
                                        <Volume2 size={20} />
                                    </button>

                                    <div>
                                        <span className="text-orange-600 font-mono font-bold block">{vocab.pinyin}</span>
                                        <span className="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded uppercase font-bold mt-1 inline-block">{vocab.part_of_speech}</span>
                                    </div>
                                </div>
                                <div className="text-left md:text-right">
                                    <span className="text-base text-slate-700 font-medium">{vocab.definition}</span>
                                </div>
                            </div>
                            
                            {vocab.example_sentence && (
                                <div className="mt-4 pt-4 border-t border-slate-50">
                                    <p className="text-sm text-slate-500 flex items-center gap-2">
                                        <span className="font-bold text-slate-400 shrink-0">例句:</span> 
                                        <span className="italic">{vocab.example_sentence}</span>
                                        
                                        <button 
                                            onClick={() => playAudio(vocab.example_sentence)}
                                            className="p-1 text-slate-400 hover:text-blue-500 bg-slate-100 hover:bg-blue-100 rounded-full transition-colors ml-2"
                                            title="朗读例句"
                                        >
                                            <Volume2 size={14} />
                                        </button>
                                    </p>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </section>

            <div className="flex justify-end pt-4 pb-12">
                <button 
                    onClick={onNextLesson}
                    className="px-8 py-4 bg-blue-600 text-white font-bold rounded-2xl hover:bg-blue-700 transition shadow-lg shadow-blue-200"
                >
                    完成本课学习
                </button>
            </div>
        </div>
    );
}