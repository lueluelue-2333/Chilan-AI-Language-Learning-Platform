import React from 'react';
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { User, Shield, Bell, Globe, ArrowLeft, Mail, Fingerprint } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function Personal_Setting() {
    const { t } = useTranslation();
    const email = localStorage.getItem('chilan_user_email');
    const userId = localStorage.getItem('chilan_user_id');

    return (
        <div className="min-h-screen bg-slate-50 p-8 font-sans">
            <div className="max-w-3xl mx-auto">
                <Link to="/" className="inline-flex items-center gap-2 text-slate-400 hover:text-blue-600 font-bold text-sm mb-8 transition-colors">
                    <ArrowLeft size={16} /> {t('auth_back_home')}
                </Link>

                <h1 className="text-4xl font-black text-slate-900 mb-12">{t('settings_title')}</h1>

                <div className="space-y-6">
                    {/* 账号信息卡片 */}
                    <div className="bg-white rounded-[2.5rem] p-8 shadow-sm border border-slate-100">
                        <h2 className="text-sm font-black text-slate-400 uppercase tracking-[0.2em] mb-8 flex items-center gap-2">
                            <User size={16} /> {t('nav_account_title')}
                        </h2>
                        
                        <div className="space-y-6">
                            <InfoRow icon={<Mail size={18}/>} label="Email" value={email} />
                            <InfoRow icon={<Fingerprint size={18}/>} label="User UUID" value={userId} isCode />
                        </div>
                    </div>

                    {/* 偏好设置卡片 */}
                    <div className="bg-white rounded-[2.5rem] p-8 shadow-sm border border-slate-100">
                        <div className="flex flex-col gap-2">
                            <SettingToggle icon={<Globe size={18}/>} label="界面语言" value="自动 (Follow System)" />
                            <SettingToggle icon={<Bell size={18}/>} label="学习提醒" value="已开启" />
                            <SettingToggle icon={<Shield size={18}/>} label="隐私保护" value="最高等级" />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

function InfoRow({ icon, label, value, isCode }) {
    return (
        <div className="flex items-center justify-between py-2">
            <div className="flex items-center gap-3 text-slate-500">
                {icon} <span className="text-sm font-bold">{label}</span>
            </div>
            <span className={`text-sm font-bold ${isCode ? 'font-mono text-blue-600 bg-blue-50 px-2 py-1 rounded-md' : 'text-slate-800'}`}>
                {value}
            </span>
        </div>
    );
}

function SettingToggle({ icon, label, value }) {
    return (
        <button className="flex items-center justify-between w-full py-4 hover:bg-slate-50 px-4 -mx-4 rounded-2xl transition-colors group">
            <div className="flex items-center gap-3 text-slate-600 font-bold text-sm">
                {icon} {label}
            </div>
            <span className="text-xs font-bold text-slate-400 group-hover:text-blue-600 transition-colors">{value}</span>
        </button>
    );
}