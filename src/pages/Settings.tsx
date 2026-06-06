import { useEffect, useState } from 'react';
import { Layout } from '../components/layout/Layout';
import { Card, CardHeader, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { useStore } from '../store/useStore';
import { userService } from '../services/userService';
import { adaptUser } from '../services/adapters';
import { Avatar } from '../components/ui/Avatar';
import { Bell, Shield, Moon, Sun, Building2, Link, Globe, Lock, Key } from 'lucide-react';
import { clsx } from 'clsx';
import { translations } from '../i18n/translations';
import type { Language } from '../i18n/translations';

function Toggle({ on, onChange }: { on: boolean; onChange: () => void }) {
  return (
    <button onClick={onChange} className={clsx('relative w-10 h-6 rounded-full transition-colors', on ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600')}>
      <span className={clsx('absolute top-1 w-4 h-4 rounded-full bg-white transition-transform', on ? 'translate-x-5' : 'translate-x-1')} />
    </button>
  );
}

export default function Settings() {
  const { authUser, setAuthUser, darkMode, toggleDarkMode, language, setLanguage } = useStore();
  const t = translations[language].settings;
  const roles = translations[language].roles;

  const [profileForm, setProfileForm] = useState({ name: '', phone: '', department: '' });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (authUser) {
      setProfileForm({ name: authUser.name, phone: authUser.phone || '', department: authUser.department || '' });
    }
  }, [authUser]);

  const handleSaveProfile = async () => {
    if (!authUser || !profileForm.name.trim()) return;
    setSaving(true);
    setSaved(false);
    try {
      const result = await userService.updateUser(authUser.id, {
        full_name: profileForm.name,
        phone: profileForm.phone || undefined,
        department: profileForm.department || undefined,
      });
      setAuthUser(adaptUser(result));
      setSaved(true);
    } catch {
      setAuthUser({ ...authUser, name: profileForm.name, phone: profileForm.phone, department: profileForm.department });
      setSaved(true);
    } finally {
      setSaving(false);
    }
  };

  const inputCls = "w-full bg-gray-100 border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-700 focus:outline-none focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200";
  const selectCls = "w-full bg-gray-100 border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700 focus:outline-none focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200";

  return (
    <Layout title={t.title} subtitle={t.subtitle}>
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Profile + Security + Integrations */}
        <div className="xl:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Building2 size={16} className="text-blue-500 dark:text-blue-400" />
                <span className="font-semibold text-gray-900 dark:text-white">{t.profileTitle}</span>
              </div>
            </CardHeader>
            <CardContent>
              {authUser && (
                <div className="flex items-start gap-6 mb-6">
                  <Avatar name={authUser.name} size="lg" />
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{authUser.name}</h3>
                    <p className="text-sm text-gray-500">{roles[authUser.role] ?? authUser.role}</p>
                    <p className="text-sm text-gray-500 mt-1">{authUser.email}</p>
                  </div>
                </div>
              )}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-gray-500 mb-1.5">{t.nameLabel}</label>
                  <input value={profileForm.name} onChange={e => setProfileForm(f => ({ ...f, name: e.target.value }))} type="text" className={inputCls} />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1.5">{t.emailLabel}</label>
                  <input value={authUser?.email ?? ''} disabled type="email" className={clsx(inputCls, 'opacity-60 cursor-not-allowed')} />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1.5">{t.phoneLabel}</label>
                  <input value={profileForm.phone} onChange={e => setProfileForm(f => ({ ...f, phone: e.target.value }))} type="tel" className={inputCls} />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1.5">{t.deptLabel}</label>
                  <input value={profileForm.department} onChange={e => setProfileForm(f => ({ ...f, department: e.target.value }))} type="text" className={inputCls} />
                </div>
              </div>
              <div className="mt-4 flex items-center justify-end gap-3">
                {saved && <span className="text-xs text-emerald-600 dark:text-emerald-400">{t.saved}</span>}
                <Button variant="primary" onClick={handleSaveProfile} disabled={saving}>{saving ? t.saving : t.saveChanges}</Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Shield size={16} className="text-emerald-500 dark:text-emerald-400" />
                <span className="font-semibold text-gray-900 dark:text-white">{t.securityTitle}</span>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/30 rounded-lg">
                <div className="flex items-center gap-3">
                  <Lock size={16} className="text-gray-400" />
                  <div>
                    <p className="text-sm text-gray-700 dark:text-gray-200">{t.twoFactor}</p>
                    <p className="text-xs text-gray-500">{t.twoFactorDesc}</p>
                  </div>
                </div>
                <Toggle on={false} onChange={() => {}} />
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/30 rounded-lg">
                <div className="flex items-center gap-3">
                  <Key size={16} className="text-gray-400" />
                  <div>
                    <p className="text-sm text-gray-700 dark:text-gray-200">{t.changePassword}</p>
                    <p className="text-xs text-gray-500">{t.changePasswordDesc}</p>
                  </div>
                </div>
                <Button size="sm">{t.changeBtn}</Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Link size={16} className="text-purple-500 dark:text-purple-400" />
                <span className="font-semibold text-gray-900 dark:text-white">{t.integrationsTitle}</span>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {[
                { name: 'Google Drive', desc: t.googleDriveDesc, icon: '🗂️', connected: true },
                { name: 'Telegram Bot', desc: t.telegramDesc, icon: '✈️', connected: false },
                { name: 'WhatsApp', desc: t.whatsappDesc, icon: '💬', connected: false },
                { name: 'Outlook / Email', desc: t.outlookDesc, icon: '📧', connected: true },
              ].map(({ name, desc, icon, connected }) => (
                <div key={name} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/30 rounded-lg">
                  <div className="flex items-center gap-3">
                    <span className="text-xl">{icon}</span>
                    <div>
                      <p className="text-sm text-gray-700 dark:text-gray-200">{name}</p>
                      <p className="text-xs text-gray-500">{desc}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={clsx('text-xs font-medium', connected ? 'text-emerald-600 dark:text-emerald-400' : 'text-gray-400')}>
                      {connected ? t.connected : t.notConnected}
                    </span>
                    <Button size="sm" variant={connected ? 'danger' : 'primary'}>{connected ? t.disconnectBtn : t.connectBtn}</Button>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* Right panel */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Bell size={16} className="text-amber-500 dark:text-amber-400" />
                <span className="font-semibold text-gray-900 dark:text-white">{t.notificationsTitle}</span>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {[
                { label: t.notifNewTasks, on: true },
                { label: t.notifDeadlines, on: true },
                { label: t.notifApprovals, on: true },
                { label: t.notifComments, on: false },
                { label: t.notifFinance, on: true },
                { label: t.notifEmail, on: true },
                { label: t.notifPush, on: false },
                { label: t.notifTelegram, on: false },
              ].map(({ label, on }) => (
                <div key={label} className="flex items-center justify-between">
                  <span className="text-sm text-gray-600 dark:text-gray-400">{label}</span>
                  <Toggle on={on} onChange={() => {}} />
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Globe size={16} className="text-blue-500 dark:text-blue-400" />
                <span className="font-semibold text-gray-900 dark:text-white">{t.interfaceTitle}</span>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {darkMode ? <Moon size={14} className="text-gray-400" /> : <Sun size={14} className="text-gray-400" />}
                  <span className="text-sm text-gray-600 dark:text-gray-400">{t.darkTheme}</span>
                </div>
                <Toggle on={darkMode} onChange={toggleDarkMode} />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1.5">{t.languageLabel}</label>
                <select value={language} onChange={e => setLanguage(e.target.value as Language)} className={selectCls}>
                  <option value="uz">O'zbek</option>
                  <option value="ru">Русский</option>
                  <option value="en">English</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1.5">{t.timezoneLabel}</label>
                <select className={selectCls}>
                  <option>UTC+5 (Toshkent)</option>
                  <option>UTC+3 (Moskva)</option>
                </select>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </Layout>
  );
}
