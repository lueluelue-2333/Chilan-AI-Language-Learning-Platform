import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Volume2, Headphones, RotateCcw, Languages, Mic } from 'lucide-react';
import { useTranslation } from 'react-i18next';

const THEMES = {
    CN_TO_EN: {
        badgeBg: 'bg-blue-100', badgeText: 'text-blue-700',
        badgeKey: 'practice_badge_cn_to_en', Icon: Languages,
    },
    EN_TO_CN: {
        badgeBg: 'bg-emerald-100', badgeText: 'text-emerald-700',
        badgeKey: 'practice_badge_en_to_cn', Icon: Languages,
    },
    EN_TO_CN_SPEAK: {
        badgeBg: 'bg-rose-100', badgeText: 'text-rose-700',
        badgeKey: 'practice_badge_speak', Icon: Mic,
    },
    CN_LISTEN_WRITE: {
        badgeBg: 'bg-indigo-100', badgeText: 'text-indigo-700',
        badgeKey: 'practice_badge_dictation', Icon: Headphones,
        btnActive: 'bg-indigo-700 shadow-indigo-300 scale-105',
        btnIdle: 'bg-indigo-600 hover:bg-indigo-700 shadow-indigo-200',
        ping: 'bg-indigo-400',
    },
};

export default function PracticePromptCard({ fadeInUp, originalText, questionType, onPlayAudio }) {
    const { t } = useTranslation();
    const [playCount, setPlayCount] = useState(0);
    const [isPlaying, setIsPlaying] = useState(false);

    const theme = THEMES[questionType] ?? THEMES.CN_TO_EN;
    const isListenWrite = questionType === 'CN_LISTEN_WRITE';

    const handlePlay = () => {
        if (!onPlayAudio) return;
        onPlayAudio();
        setPlayCount(c => c + 1);
        setIsPlaying(true);
        setTimeout(() => setIsPlaying(false), 2200);
    };

    if (isListenWrite) {
        return (
            <motion.div variants={fadeInUp} initial="hidden" animate="show" className="text-center mb-8">
                <div className={`inline-flex items-center gap-2 px-4 py-1.5 ${theme.badgeBg} rounded-full mb-6`}>
                    <theme.Icon size={15} className={theme.badgeText} />
                    <span className={`text-xs font-black ${theme.badgeText} uppercase tracking-widest`}>{t(theme.badgeKey)}</span>
                </div>

                <div className="flex flex-col items-center gap-5">
                    <button
                        onClick={handlePlay}
                        className={`relative w-28 h-28 rounded-full flex flex-col items-center justify-center gap-1.5 shadow-2xl transition-all active:scale-95 ${
                            isPlaying ? theme.btnActive : theme.btnIdle
                        }`}
                    >
                        {isPlaying && (
                            <span className={`absolute inset-0 rounded-full animate-ping ${theme.ping} opacity-30`} />
                        )}
                        <Volume2 size={36} className="text-white relative z-10" />
                        <span className="text-xs font-black text-indigo-200 relative z-10 tracking-wide">
                            {playCount === 0 ? t('practice_audio_play') : t('practice_audio_replay')}
                        </span>
                    </button>

                    {playCount > 0 && (
                        <div className="flex items-center gap-1.5 text-xs text-slate-400 font-medium">
                            <RotateCcw size={11} />
                            {t('practice_audio_played_times', { count: playCount })}
                        </div>
                    )}

                    <div className="flex items-center gap-1.5">
                        <kbd className="px-1.5 py-0.5 rounded border border-slate-200 bg-white text-[10px] font-mono text-slate-400 shadow-sm">↑</kbd>
                        <span className="text-xs text-slate-400">{t('practice_audio_replay')}</span>
                    </div>

                    <p className="text-base text-slate-500 font-medium">
                        {t('practice_dictation_instruction')}
                    </p>
                </div>
            </motion.div>
        );
    }

    return (
        <motion.div variants={fadeInUp} initial="hidden" animate="show" className="text-center mb-8">
            <div className={`inline-flex items-center gap-2 px-4 py-1.5 ${theme.badgeBg} rounded-full mb-4`}>
                <theme.Icon size={15} className={theme.badgeText} />
                <span className={`text-xs font-black ${theme.badgeText} uppercase tracking-widest`}>{t(theme.badgeKey)}</span>
            </div>
            <p className="text-4xl md:text-5xl font-black text-slate-900 leading-tight px-4">
                "{originalText}"
            </p>
            {onPlayAudio && (
                <p className="mt-3 text-sm text-slate-400">{t('practice_replay_hint')}</p>
            )}
        </motion.div>
    );
}
