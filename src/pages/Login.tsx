import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useStore } from '../store/useStore';
import { Building2, Eye, EyeOff, Lock, Mail } from 'lucide-react';
import { translations } from '../i18n/translations';

export default function Login() {
  const [email, setEmail] = useState('admin@platform.uz');
  const [password, setPassword] = useState('admin123');
  const [showPass, setShowPass] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, language } = useStore();
  const navigate = useNavigate();
  const t = translations[language].login;

  const handleLogin = async (e: { preventDefault(): void }) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    const ok = await login(email, password);
    if (ok) {
      navigate('/');
    } else {
      setError(t.error);
    }
    setLoading(false);
  };

  const roleLabels = translations[language].roles;

  const demoUsers = [
    { email: 'admin@platform.uz', role: roleLabels.admin, color: 'text-red-500 dark:text-red-400' },
    { email: 'manager@platform.uz', role: roleLabels.manager, color: 'text-purple-500 dark:text-purple-400' },
    { email: 'gip1@platform.uz', role: roleLabels.gip, color: 'text-blue-500 dark:text-blue-400' },
    { email: 'designer1@platform.uz', role: roleLabels.designer, color: 'text-emerald-500 dark:text-emerald-400' },
  ];

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-950 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 via-transparent to-purple-500/10 dark:from-blue-950/30 dark:to-purple-950/20" />

      <div className="relative w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg shadow-blue-500/30">
            <Building2 size={32} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">AiPlatforma</h1>
          <p className="text-gray-500 mt-1 text-sm">{t.platformSubtitle}</p>
        </div>

        {/* Form */}
        <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-xl dark:bg-gray-800 dark:border-gray-700 dark:shadow-2xl">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">{t.title}</h2>
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1.5">{t.email}</label>
              <div className="relative">
                <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500" />
                <input
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  type="email"
                  required
                  className="w-full bg-gray-50 border border-gray-300 rounded-xl pl-10 pr-4 py-3 text-sm text-gray-900 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200"
                />
              </div>
            </div>
            <div>
              <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1.5">{t.password}</label>
              <div className="relative">
                <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500" />
                <input
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  type={showPass ? 'text' : 'password'}
                  required
                  className="w-full bg-gray-50 border border-gray-300 rounded-xl pl-10 pr-10 py-3 text-sm text-gray-900 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200"
                />
                <button
                  type="button"
                  onClick={() => setShowPass(!showPass)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>
            {error && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2 dark:text-red-400 dark:bg-red-900/20 dark:border-red-900">
                {error}
              </p>
            )}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 rounded-xl transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {loading && <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />}
              {loading ? t.submitting : t.submit}
            </button>
          </form>

          <div className="mt-4 text-center">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Hisobingiz yo'qmi?{' '}
              <Link to="/register" className="text-blue-600 hover:text-blue-700 font-medium dark:text-blue-400">
                Ro'yxatdan o'tish
              </Link>
            </p>
          </div>

          <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
            <p className="text-xs text-gray-500 mb-3 text-center">{t.demoAccounts}</p>
            <div className="grid grid-cols-2 gap-2">
              {demoUsers.map(u => (
                <button
                  key={u.email}
                  onClick={() => setEmail(u.email)}
                  className="text-left px-3 py-2 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors dark:bg-gray-700/50 dark:hover:bg-gray-700"
                >
                  <p className={`text-xs font-medium ${u.color}`}>{u.role}</p>
                  <p className="text-xs text-gray-500 truncate">{u.email}</p>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
