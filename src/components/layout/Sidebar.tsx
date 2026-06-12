import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { clsx } from 'clsx';
import {
  LayoutDashboard, FolderKanban, CheckSquare, FileText,
  DollarSign, GitBranch, Users, BarChart3, MessageSquare,
  Settings, ChevronLeft, ChevronRight, Building2, FileSignature
} from 'lucide-react';
import { useStore } from '../../store/useStore';
import { Avatar } from '../ui/Avatar';
import { translations } from '../../i18n/translations';

export function Sidebar() {
  const { sidebarOpen, toggleSidebar, authUser, language } = useStore();
  const location = useLocation();
  const navigate = useNavigate();
  const t = translations[language];

  const navItems = [
    { to: '/', label: t.nav.dashboard, icon: LayoutDashboard },
    { to: '/projects', label: t.nav.projects, icon: FolderKanban },
    { to: '/tasks', label: t.nav.tasks, icon: CheckSquare },
    { to: '/documents', label: t.nav.documents, icon: FileText },
    { to: '/approvals', label: t.nav.approvals, icon: GitBranch },
    { to: '/finance', label: t.nav.finance, icon: DollarSign },
    { to: '/reports', label: t.nav.analytics, icon: BarChart3 },
    { to: '/requests', label: t.nav.requests, icon: MessageSquare },
    { to: '/templates', label: t.nav.templates, icon: FileSignature },
    { to: '/users', label: t.nav.employees, icon: Users },
    { to: '/settings', label: t.nav.settings, icon: Settings },
  ];

  return (
    <aside className={clsx(
      'flex flex-col border-r transition-all duration-300',
      'bg-white border-gray-200 dark:bg-gray-900 dark:border-gray-800',
      // Mobile: fixed overlay; Desktop: static in flow
      'fixed inset-y-0 left-0 z-50',
      'lg:static lg:z-auto lg:flex-shrink-0',
      // Width: always w-60 on mobile, collapsible on desktop
      'w-60',
      sidebarOpen ? 'lg:w-60' : 'lg:w-16',
      // Translate: hide off-screen on mobile when closed, always visible on desktop
      sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
    )}>
      {/* Logo */}
      <div className={clsx(
        'flex items-center gap-3 px-4 h-16 border-b border-gray-200 dark:border-gray-800',
        !sidebarOpen && 'justify-center'
      )}>
        <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
          <Building2 size={18} className="text-white" />
        </div>
        {sidebarOpen && <span className="text-gray-900 dark:text-white font-bold text-base tracking-tight">AiPlatforma</span>}
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 overflow-y-auto">
        <ul className="space-y-0.5 px-2">
          {navItems.map(({ to, label, icon: Icon }) => {
            const isActive = to === '/' ? location.pathname === '/' : location.pathname.startsWith(to);
            return (
              <li key={to}>
                <NavLink
                  to={to}
                  title={!sidebarOpen ? label : undefined}
                  className={clsx(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all',
                    isActive
                      ? 'bg-blue-50 text-blue-600 border border-blue-200 dark:bg-blue-600/20 dark:text-blue-400 dark:border-blue-600/30'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-gray-800',
                    !sidebarOpen && 'justify-center'
                  )}
                >
                  <Icon size={18} className="flex-shrink-0" />
                  {sidebarOpen && label}
                </NavLink>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* User + Toggle */}
      <div className="border-t border-gray-200 dark:border-gray-800">
        {sidebarOpen && authUser && (
          <button
            onClick={() => navigate('/settings')}
            className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          >
            <Avatar name={authUser.name} size="sm" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{authUser.name}</p>
              <p className="text-xs text-gray-500 truncate">{t.roles[authUser.role] ?? authUser.role}</p>
            </div>
          </button>
        )}
        <button
          onClick={toggleSidebar}
          className={clsx(
            'w-full flex items-center justify-center py-3 text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors dark:text-gray-500 dark:hover:text-gray-300 dark:hover:bg-gray-800',
            sidebarOpen ? 'border-t border-gray-200 dark:border-gray-800' : ''
          )}
        >
          {sidebarOpen ? <ChevronLeft size={16} /> : <ChevronRight size={16} />}
        </button>
      </div>
    </aside>
  );
}
