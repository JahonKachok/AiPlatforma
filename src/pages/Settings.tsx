import { Layout } from '../components/layout/Layout';
import { Card, CardHeader, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { useStore } from '../store/useStore';
import { Avatar } from '../components/ui/Avatar';
import { roleLabels } from '../data/mockData';
import { Bell, Shield, Moon, Sun, Building2, Link, Globe, Lock, Key } from 'lucide-react';
import { clsx } from 'clsx';

function Toggle({ on, onChange }: { on: boolean; onChange: () => void }) {
  return (
    <button onClick={onChange} className={clsx('relative w-10 h-6 rounded-full transition-colors', on ? 'bg-blue-600' : 'bg-gray-600')}>
      <span className={clsx('absolute top-1 w-4 h-4 rounded-full bg-white transition-transform', on ? 'translate-x-5' : 'translate-x-1')} />
    </button>
  );
}

export default function Settings() {
  const { authUser, darkMode, toggleDarkMode } = useStore();

  return (
    <Layout title="Настройки" subtitle="Настройки профиля и системы">
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Profile */}
        <div className="xl:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Building2 size={16} className="text-blue-400" />
                <span className="font-semibold text-white">Профиль пользователя</span>
              </div>
            </CardHeader>
            <CardContent>
              {authUser && (
                <div className="flex items-start gap-6 mb-6">
                  <Avatar name={authUser.name} size="lg" />
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-white">{authUser.name}</h3>
                    <p className="text-sm text-gray-500">{roleLabels[authUser.role]}</p>
                    <p className="text-sm text-gray-500 mt-1">{authUser.email}</p>
                  </div>
                </div>
              )}
              <div className="grid grid-cols-2 gap-4">
                {[
                  { label: 'Имя', value: authUser?.name, type: 'text' },
                  { label: 'Email', value: authUser?.email, type: 'email' },
                  { label: 'Телефон', value: authUser?.phone || '', type: 'tel' },
                  { label: 'Отдел', value: authUser?.department || '', type: 'text' },
                ].map(({ label, value, type }) => (
                  <div key={label}>
                    <label className="block text-xs text-gray-400 mb-1.5">{label}</label>
                    <input defaultValue={value} type={type}
                      className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2.5 text-sm text-gray-200 focus:outline-none focus:border-blue-500" />
                  </div>
                ))}
              </div>
              <div className="mt-4 flex justify-end">
                <Button variant="primary">Сохранить изменения</Button>
              </div>
            </CardContent>
          </Card>

          {/* Security */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Shield size={16} className="text-emerald-400" />
                <span className="font-semibold text-white">Безопасность</span>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-3 bg-gray-700/30 rounded-lg">
                <div className="flex items-center gap-3">
                  <Lock size={16} className="text-gray-400" />
                  <div>
                    <p className="text-sm text-gray-200">Двухфакторная аутентификация</p>
                    <p className="text-xs text-gray-500">Дополнительная защита входа</p>
                  </div>
                </div>
                <Toggle on={false} onChange={() => {}} />
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-700/30 rounded-lg">
                <div className="flex items-center gap-3">
                  <Key size={16} className="text-gray-400" />
                  <div>
                    <p className="text-sm text-gray-200">Изменить пароль</p>
                    <p className="text-xs text-gray-500">Последнее изменение: 30 дней назад</p>
                  </div>
                </div>
                <Button size="sm">Изменить</Button>
              </div>
            </CardContent>
          </Card>

          {/* Integrations */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Link size={16} className="text-purple-400" />
                <span className="font-semibold text-white">Интеграции</span>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {[
                { name: 'Google Drive', desc: 'Синхронизация файлов', icon: '🗂️', connected: true },
                { name: 'Telegram Bot', desc: 'Уведомления в Telegram', icon: '✈️', connected: false },
                { name: 'WhatsApp', desc: 'Уведомления в WhatsApp', icon: '💬', connected: false },
                { name: 'Outlook / Email', desc: 'Email-уведомления', icon: '📧', connected: true },
              ].map(({ name, desc, icon, connected }) => (
                <div key={name} className="flex items-center justify-between p-3 bg-gray-700/30 rounded-lg">
                  <div className="flex items-center gap-3">
                    <span className="text-xl">{icon}</span>
                    <div>
                      <p className="text-sm text-gray-200">{name}</p>
                      <p className="text-xs text-gray-500">{desc}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={clsx('text-xs font-medium', connected ? 'text-emerald-400' : 'text-gray-500')}>{connected ? 'Подключено' : 'Не подключено'}</span>
                    <Button size="sm" variant={connected ? 'danger' : 'primary'}>{connected ? 'Отключить' : 'Подключить'}</Button>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* Right panel */}
        <div className="space-y-6">
          {/* Notifications */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Bell size={16} className="text-amber-400" />
                <span className="font-semibold text-white">Уведомления</span>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {[
                { label: 'Новые задачи', on: true },
                { label: 'Дедлайны', on: true },
                { label: 'Согласования', on: true },
                { label: 'Комментарии', on: false },
                { label: 'Финансовые', on: true },
                { label: 'Email-уведомления', on: true },
                { label: 'Push-уведомления', on: false },
                { label: 'Telegram-уведомления', on: false },
              ].map(({ label, on }) => (
                <div key={label} className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">{label}</span>
                  <Toggle on={on} onChange={() => {}} />
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Appearance */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Globe size={16} className="text-blue-400" />
                <span className="font-semibold text-white">Интерфейс</span>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {darkMode ? <Moon size={14} className="text-gray-400" /> : <Sun size={14} className="text-gray-400" />}
                  <span className="text-sm text-gray-400">Тёмная тема</span>
                </div>
                <Toggle on={darkMode} onChange={toggleDarkMode} />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1.5">Язык</label>
                <select className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500">
                  <option>Русский</option>
                  <option>O'zbekcha</option>
                  <option>English</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1.5">Временная зона</label>
                <select className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500">
                  <option>UTC+5 (Ташкент)</option>
                  <option>UTC+3 (Москва)</option>
                </select>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </Layout>
  );
}
