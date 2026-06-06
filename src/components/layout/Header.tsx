import { Bell, Search, Sun, Moon, LogOut, Globe, ChevronDown } from 'lucide-react';
import { useStore } from '../../store/useStore';
import { Avatar } from '../ui/Avatar';
import { useState } from 'react';
import { clsx } from 'clsx';
import { useNavigate } from 'react-router-dom';
import { translations } from '../../i18n/translations';
import type { Language } from '../../i18n/translations';

interface HeaderProps {
  title: string;
  subtitle?: string;
}

const langLabels: Record<Language, string> = {
  uz: "O'zbek",
  ru: 'Русский',
  en: 'English',
};

const langShort: Record<Language, string> = {
  uz: 'UZ',
  ru: 'RU',
  en: 'EN',
};

export function Header({ title, subtitle }: HeaderProps) {
  const { authUser, notifications, markAllNotificationsRead, darkMode, toggleDarkMode, logout, language, setLanguage } = useStore();
  const [showNotifs, setShowNotifs] = useState(false);
  const [showLang, setShowLang] = useState(false);
  const navigate = useNavigate();
  const t = translations[language];

  const unread = notifications.filter(n => !n.isRead && n.userId === authUser?.id).length;

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <header className="h-16 border-b flex items-center justify-between px-6 flex-shrink-0 bg-white border-gray-200 dark:bg-gray-900 dark:border-gray-800">
      <div>
        <h1 className="text-lg font-semibold text-gray-900 dark:text-white">{title}</h1>
        {subtitle && <p className="text-xs text-gray-500 dark:text-gray-500">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-2">
        {/* Search */}
        <div className="relative hidden md:block">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500" />
          <input
            placeholder={t.header.search}
            className="bg-gray-100 border border-gray-200 rounded-lg pl-9 pr-4 py-2 text-sm text-gray-700 placeholder-gray-400 focus:outline-none focus:border-blue-500 w-52 dark:bg-gray-800 dark:border-gray-700 dark:text-gray-300 dark:placeholder-gray-600"
          />
        </div>

        {/* Language switcher */}
        <div className="relative">
          <button
            onClick={() => { setShowLang(!showLang); setShowNotifs(false); }}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 transition-colors dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-gray-800"
          >
            <Globe size={15} />
            <span>{langShort[language]}</span>
            <ChevronDown size={12} className={clsx('transition-transform', showLang && 'rotate-180')} />
          </button>
          {showLang && (
            <div className="absolute right-0 top-11 w-36 bg-white border border-gray-200 rounded-xl shadow-lg z-50 overflow-hidden dark:bg-gray-800 dark:border-gray-700">
              {(Object.keys(langLabels) as Language[]).map(lang => (
                <button
                  key={lang}
                  onClick={() => { setLanguage(lang); setShowLang(false); }}
                  className={clsx(
                    'w-full flex items-center justify-between px-4 py-2.5 text-sm transition-colors',
                    lang === language
                      ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400'
                      : 'text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-700/50'
                  )}
                >
                  <span>{langLabels[lang]}</span>
                  <span className="text-xs font-bold text-gray-400 dark:text-gray-500">{langShort[lang]}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Dark mode */}
        <button
          onClick={toggleDarkMode}
          className="p-2 rounded-lg text-gray-500 hover:text-gray-700 hover:bg-gray-100 transition-colors dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-gray-800"
          title={darkMode ? 'Kunduzgi rejim' : 'Tungi rejim'}
        >
          {darkMode ? <Sun size={18} /> : <Moon size={18} />}
        </button>

        {/* Notifications */}
        <div className="relative">
          <button
            onClick={() => { setShowNotifs(!showNotifs); setShowLang(false); if (!showNotifs) markAllNotificationsRead(); }}
            className="relative p-2 rounded-lg text-gray-500 hover:text-gray-700 hover:bg-gray-100 transition-colors dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-gray-800"
          >
            <Bell size={18} />
            {unread > 0 && (
              <span className="absolute top-1 right-1 w-4 h-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
                {unread}
              </span>
            )}
          </button>
          {showNotifs && (
            <div className="absolute right-0 top-12 w-80 bg-white border border-gray-200 rounded-xl shadow-2xl z-50 overflow-hidden dark:bg-gray-800 dark:border-gray-700">
              <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
                <span className="text-sm font-semibold text-gray-900 dark:text-white">{t.header.notifications}</span>
              </div>
              <div className="max-h-80 overflow-y-auto">
                {notifications.filter(n => n.userId === authUser?.id).slice(0, 8).map(n => (
                  <div key={n.id} className={clsx(
                    'px-4 py-3 border-b border-gray-100 hover:bg-gray-50 transition-colors dark:border-gray-700/50 dark:hover:bg-gray-700/50',
                    !n.isRead && 'bg-blue-50 dark:bg-blue-900/10'
                  )}>
                    <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{n.title}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{n.message}</p>
                    <p className="text-xs text-gray-400 dark:text-gray-600 mt-1">{n.createdAt}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* User */}
        {authUser && (
          <div className="flex items-center gap-2 pl-2 border-l border-gray-200 ml-1 dark:border-gray-700">
            <Avatar name={authUser.name} size="sm" />
            <button
              onClick={handleLogout}
              className="p-2 rounded-lg text-gray-400 hover:text-red-500 hover:bg-gray-100 transition-colors dark:hover:bg-gray-800"
              title={t.header.logout}
            >
              <LogOut size={16} />
            </button>
          </div>
        )}
      </div>

      {/* Close dropdowns on outside click */}
      {(showLang || showNotifs) && (
        <div className="fixed inset-0 z-40" onClick={() => { setShowLang(false); setShowNotifs(false); }} />
      )}
    </header>
  );
}
