/**
 * 这里的 SVG 采用 Data URI 格式，线条设为白色，透明度较低。
 * 你可以根据需要替换其中的 path 数据来改变建筑图案。
 */

// 英语文化底纹 (大本钟 / 伦敦地标风格)
const patternUk = `data:image/svg+xml,%3Csvg width='100' height='100' viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' stroke='%23ffffff' stroke-width='1.2' opacity='0.15'%3E%3Cpath d='M20 20h15v60H20zM22 15l5.5-10 5.5 10M25 25v10M30 25v10M20 40h15M20 50h15' /%3E%3Cpath d='M60 30h30v40H60zM70 20l5-10 5 10M65 40h20M65 50h20' /%3E%3C/g%3E%3C/svg%3E`;

// 中文文化底纹 (故宫 / 东方建筑风格)
const patternCn = `data:image/svg+xml,%3Csvg width='100' height='100' viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' stroke='%23ffffff' stroke-width='1.2' opacity='0.15'%3E%3Cpath d='M10 60l10-10h60l10 10H10zM20 60v15h60V60' /%3E%3Cpath d='M35 50l5-15h20l5 15M40 35l10-10 10 10' /%3E%3Cpath d='M30 75v10M50 75v10M70 75v10' /%3E%3C/g%3E%3C/svg%3E`;

// 其他文化底纹 (作为演示)
const patternDefault = `data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' stroke='%23ffffff' stroke-width='1' opacity='0.1'%3E%3Cpath d='M30 0L0 30M60 30L30 60' /%3E%3C/g%3E%3C/svg%3E`;

// 导出课程图案对
export const coursePatternPairs = {
    'EN_TO_CN': { left: patternUk, right: patternCn },
    'CN_TO_EN': { left: patternCn, right: patternUk },
    'default': { left: patternDefault, right: patternDefault }
};

// 导出课程主题色 (纯色)
export const courseThemes = {
    'EN_TO_CN': 'bg-[#E11D48]', // 玫瑰红
    'CN_TO_EN': 'bg-[#2563EB]', // 宝石蓝
    'FR_TO_CN': 'bg-[#4F46E5]', // 靛蓝
    'JP_TO_CN': 'bg-[#DB2777]', // 玫粉
    'default': 'bg-slate-600'
};