import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Building2, Eye, EyeOff, Lock, Mail, User, Phone, Briefcase } from 'lucide-react';
import { authService } from '../services/authService';

const roles = [
  { value: 'designer', label: 'Проектировщик / Loyihachi' },
  { value: 'gip', label: 'ГИП / Bosh muhandis' },
  { value: 'gip_assistant', label: 'Помощник ГИПа / GIP yordamchisi' },
  { value: 'manager', label: 'Менеджер / Menejer' },
  { value: 'reviewer', label: 'Проверяющий / Tekshiruvchi' },
  { value: 'client', label: 'Клиент / Mijoz' },
];

export default function Register() {
  const [form, setForm] = useState({
    full_name: '',
    email: '',
    password: '',
    confirmPassword: '',
    role: 'designer',
    department: '',
    phone: '',
  });
  const [showPass, setShowPass] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (form.password !== form.confirmPassword) {
      setError('Parollar mos kelmayapti');
      return;
    }
    if (form.password.length < 6) {
      setError('Parol kamida 6 ta belgidan iborat bo\'lishi kerak');
      return;
    }

    setLoading(true);
    try {
      await authService.register({
        email: form.email,
        password: form.password,
        full_name: form.full_name,
        role: form.role,
        department: form.department || undefined,
        phone: form.phone || undefined,
      });
      navigate('/login', { state: { registered: true } });
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      setError(axiosErr.response?.data?.detail || 'Ro\'yxatdan o\'tishda xatolik yuz berdi');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-950 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 via-transparent to-purple-500/10 dark:from-blue-950/30 dark:to-purple-950/20" />

      <div className="relative w-full max-w-md">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg shadow-blue-500/30">
            <Building2 size={32} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">AiPlatforma</h1>
          <p className="text-gray-500 mt-1 text-sm">Yangi hisob yaratish</p>
        </div>

        <div className="bg-white border border-gray-200 rounded-2xl p-6 shadow-xl dark:bg-gray-800 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">Ro'yxatdan o'tish</h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1.5">To'liq ism *</label>
              <div className="relative">
                <User size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  name="full_name"
                  value={form.full_name}
                  onChange={handleChange}
                  type="text"
                  required
                  placeholder="Ism Familiya"
                  className="w-full bg-gray-50 border border-gray-300 rounded-xl pl-10 pr-4 py-3 text-sm text-gray-900 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1.5">Email *</label>
              <div className="relative">
                <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  name="email"
                  value={form.email}
                  onChange={handleChange}
                  type="email"
                  required
                  placeholder="email@example.com"
                  className="w-full bg-gray-50 border border-gray-300 rounded-xl pl-10 pr-4 py-3 text-sm text-gray-900 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1.5">Parol *</label>
              <div className="relative">
                <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  name="password"
                  value={form.password}
                  onChange={handleChange}
                  type={showPass ? 'text' : 'password'}
                  required
                  placeholder="Kamida 6 ta belgi"
                  className="w-full bg-gray-50 border border-gray-300 rounded-xl pl-10 pr-10 py-3 text-sm text-gray-900 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200"
                />
                <button
                  type="button"
                  onClick={() => setShowPass(!showPass)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1.5">Parolni tasdiqlash *</label>
              <div className="relative">
                <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  name="confirmPassword"
                  value={form.confirmPassword}
                  onChange={handleChange}
                  type={showPass ? 'text' : 'password'}
                  required
                  placeholder="Parolni qaytaring"
                  className="w-full bg-gray-50 border border-gray-300 rounded-xl pl-10 pr-4 py-3 text-sm text-gray-900 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1.5">Lavozim *</label>
              <div className="relative">
                <Briefcase size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                <select
                  name="role"
                  value={form.role}
                  onChange={handleChange}
                  className="w-full bg-gray-50 border border-gray-300 rounded-xl pl-10 pr-4 py-3 text-sm text-gray-900 focus:outline-none focus:border-blue-500 appearance-none dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200"
                >
                  {roles.map(r => (
                    <option key={r.value} value={r.value}>{r.label}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1.5">Bo'lim</label>
                <input
                  name="department"
                  value={form.department}
                  onChange={handleChange}
                  type="text"
                  placeholder="Masalan: AD"
                  className="w-full bg-gray-50 border border-gray-300 rounded-xl px-3 py-3 text-sm text-gray-900 focus:outline-none focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1.5">Telefon</label>
                <div className="relative">
                  <Phone size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input
                    name="phone"
                    value={form.phone}
                    onChange={handleChange}
                    type="tel"
                    placeholder="+998901234567"
                    className="w-full bg-gray-50 border border-gray-300 rounded-xl pl-9 pr-3 py-3 text-sm text-gray-900 focus:outline-none focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200"
                  />
                </div>
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
              {loading ? 'Ro\'yxatdan o\'tilmoqda...' : 'Ro\'yxatdan o\'tish'}
            </button>
          </form>

          <div className="mt-4 text-center">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Hisobingiz bormi?{' '}
              <Link to="/login" className="text-blue-600 hover:text-blue-700 font-medium dark:text-blue-400">
                Kirish
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
