import { useEffect, useState } from 'react';
import { Layout } from '../components/layout/Layout';
import { Card, CardHeader, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { useStore } from '../store/useStore';
import { userService } from '../services/userService';
import { telegramService } from '../services/telegramService';
import { adminService, type BackupInfo } from '../services/adminService';
import { adaptUser } from '../services/adapters';
import { Avatar } from '../components/ui/Avatar';
import {
  Bell, Shield, Moon, Sun, Building2, Link, Globe, Lock, Key, Pencil, Check,
  Calendar, ClipboardList, ShieldCheck, MessageSquare, DollarSign, Mail, Smartphone, Send,
  HardDrive, DatabaseBackup, Download,
} from 'lucide-react';
import { clsx } from 'clsx';
import { translations } from '../i18n/translations';
import type { Language } from '../i18n/translations';

function Toggle({ on, onChange }: { on: boolean; onChange: () => void }) {
  return (
    <label className="relative cursor-pointer flex-shrink-0">
      <input
        type="checkbox"
        role="switch"
        checked={on}
        onChange={onChange}
        className="sr-only peer"
      />
      <div className="w-9 h-5 bg-slate-300 rounded-full peer-checked:bg-blue-600 peer-focus-visible:ring-2 peer-focus-visible:ring-blue-500 transition-colors dark:bg-neutral-700" />
      <div className="absolute left-0.5 top-0.5 w-[15.5px] h-[15.5px] bg-white rounded-full transition-transform peer-checked:translate-x-4" />
    </label>
  );
}

const badgeColors = {
  blue: 'bg-blue-50 text-blue-600 dark:bg-blue-500/10 dark:text-blue-400',
  emerald: 'bg-emerald-50 text-emerald-600 dark:bg-emerald-500/10 dark:text-emerald-400',
  purple: 'bg-purple-50 text-purple-600 dark:bg-purple-500/10 dark:text-purple-400',
  amber: 'bg-amber-50 text-amber-600 dark:bg-amber-500/10 dark:text-amber-400',
  rose: 'bg-rose-50 text-rose-600 dark:bg-rose-500/10 dark:text-rose-400',
  indigo: 'bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400',
  cyan: 'bg-cyan-50 text-cyan-600 dark:bg-cyan-500/10 dark:text-cyan-400',
  orange: 'bg-orange-50 text-orange-600 dark:bg-orange-500/10 dark:text-orange-400',
} as const;

function IconBadge({ icon, color, size = 'md' }: { icon: React.ReactNode; color: keyof typeof badgeColors; size?: 'sm' | 'md' }) {
  return (
    <div className={clsx('rounded-lg flex items-center justify-center flex-shrink-0', size === 'md' ? 'w-10 h-10' : 'w-8 h-8', badgeColors[color])}>
      {icon}
    </div>
  );
}

export default function Settings() {
  const { authUser, setAuthUser, darkMode, toggleDarkMode, language, setLanguage } = useStore();
  const t = translations[language].settings;
  const roles = translations[language].roles;
  const common = translations[language].common;

  const [profileForm, setProfileForm] = useState({ name: '', phone: '', department: '' });
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [twoFactor, setTwoFactor] = useState(true);
  const [notifPrefs, setNotifPrefs] = useState({
    newTasks: true, deadlines: true, approvals: true, comments: false,
    finance: true, email: true, push: false, telegram: false,
  });
  const [backups, setBackups] = useState<BackupInfo[]>([]);
  const [creatingBackup, setCreatingBackup] = useState(false);
  const [telegramLinking, setTelegramLinking] = useState(false);
  const [telegramLinkData, setTelegramLinkData] = useState<any>(null);

  const isAdmin = authUser && ['admin', 'manager'].includes(authUser.role);

  useEffect(() => {
    if (authUser) {
      setProfileForm({ name: authUser.full_name || authUser.name || '', phone: authUser.phone || '', department: authUser.department || '' });
    }
  }, [authUser]);

  useEffect(() => {
    if (!isAdmin) return;
    adminService.getBackups().then(setBackups).catch(() => {});
  }, [isAdmin]);

  const handleCreateBackup = async () => {
    setCreatingBackup(true);
    try {
      await adminService.createBackup();
      setBackups(await adminService.getBackups());
    } catch { /* backend unavailable */ }
    setCreatingBackup(false);
  };

  const handleTelegramLink = async () => {
    if (!authUser) {
      console.error('No auth user');
      return;
    }
    setTelegramLinking(true);
    try {
      console.log('Creating Telegram link for user:', authUser.id);
      const data = await telegramService.createTelegramLink(authUser.id);
      console.log('Link created:', data);

      setTelegramLinkData(data);

      if (data && data.telegram_link) {
        // Open Telegram link in new window
        setTimeout(() => {
          const telegramWindow = window.open(data.telegram_link, '_blank');
          if (!telegramWindow) {
            console.error('Failed to open Telegram window');
            alert('Telegramni ochish uchun bu linkni bosing:\n' + data.telegram_link);
          }
        }, 500);
      } else {
        console.error('No telegram_link in response:', data);
        alert('Token olingan lekin link bo\'lmadi');
      }
    } catch (error) {
      console.error('Failed to create Telegram link:', error);
      alert('Xatolik: ' + (error instanceof Error ? error.message : 'Unknown error'));
    }
    setTelegramLinking(false);
  };

  const handleTelegramUnlink = async () => {
    if (!authUser) return;
    setTelegramLinking(true);
    try {
      console.log('Unlinking Telegram for user:', authUser.id);
      await telegramService.removeTelegramLink(authUser.id);
      setAuthUser({ ...authUser, telegram_chat_id: null });
      console.log('Telegram unlinked successfully');
    } catch (error) {
      console.error('Failed to unlink Telegram:', error);
      alert('Xatolik: ' + (error instanceof Error ? error.message : 'Unknown error'));
    }
    setTelegramLinking(false);
  };

  const handleToggleEdit = () => {
    if (editing && authUser) {
      setProfileForm({ name: authUser.full_name || authUser.name || '', phone: authUser.phone || '', department: authUser.department || '' });
    }
    setEditing(e => !e);
  };

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
    } catch {
      setAuthUser({ ...authUser, name: profileForm.name, phone: profileForm.phone, department: profileForm.department });
    } finally {
      setSaved(true);
      setSaving(false);
      setEditing(false);
    }
  };

  const inputCls = "w-full bg-gray-100 border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-700 focus:outline-none focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200 disabled:opacity-60 disabled:cursor-not-allowed";
  const selectCls = "w-full bg-gray-100 border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700 focus:outline-none focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200";

  const notifItems: { key: keyof typeof notifPrefs; label: string; desc: string; icon: React.ReactNode; color: keyof typeof badgeColors }[] = [
    { key: 'newTasks', label: t.notifNewTasks, desc: t.notifNewTasksDesc, icon: <ClipboardList size={16} />, color: 'blue' },
    { key: 'deadlines', label: t.notifDeadlines, desc: t.notifDeadlinesDesc, icon: <Calendar size={16} />, color: 'rose' },
    { key: 'approvals', label: t.notifApprovals, desc: t.notifApprovalsDesc, icon: <ShieldCheck size={16} />, color: 'indigo' },
    { key: 'comments', label: t.notifComments, desc: t.notifCommentsDesc, icon: <MessageSquare size={16} />, color: 'emerald' },
    { key: 'finance', label: t.notifFinance, desc: t.notifFinanceDesc, icon: <DollarSign size={16} />, color: 'purple' },
    { key: 'email', label: t.notifEmail, desc: t.notifEmailDesc, icon: <Mail size={16} />, color: 'blue' },
    { key: 'push', label: t.notifPush, desc: t.notifPushDesc, icon: <Smartphone size={16} />, color: 'orange' },
    { key: 'telegram', label: t.notifTelegram, desc: t.notifTelegramDesc, icon: <Send size={16} />, color: 'cyan' },
  ];

  const integrations: { name: string; desc: string; icon: React.ReactNode; color: keyof typeof badgeColors; connected: boolean }[] = [
    { name: 'Telegram', desc: t.telegramDesc, icon: <Send size={18} />, color: 'cyan', connected: !!authUser?.telegram_chat_id },
    { name: 'Google Drive', desc: t.googleDriveDesc, icon: <HardDrive size={18} />, color: 'blue', connected: false },
  ];

  return (
    <Layout title={t.title} subtitle={t.subtitle}>
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Profile + Security + Integrations */}
        <div className="xl:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2.5">
                <IconBadge icon={<Building2 size={16} />} color="blue" size="sm" />
                <span className="font-semibold text-gray-900 dark:text-white">{t.profileTitle}</span>
              </div>
            </CardHeader>
            <CardContent>
              {authUser && (() => {
                const userName = authUser.full_name || authUser.name || 'User';
                return (
                <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-6">
                  <div className="flex items-start gap-4">
                    <Avatar name={userName} size="lg" />
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{userName}</h3>
                        <Badge variant="info">{roles[authUser.role] ?? authUser.role}</Badge>
                      </div>
                      <p className="text-sm text-gray-500 mt-1">{authUser.email}</p>
                    </div>
                  </div>
                  <Button variant="secondary" size="sm" icon={<Pencil size={14} />} onClick={handleToggleEdit}>
                    {editing ? common.cancel : common.edit}
                  </Button>
                </div>
                );
              })()}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-gray-500 mb-1.5">{t.nameLabel}</label>
                  <input value={profileForm.name} onChange={e => setProfileForm(f => ({ ...f, name: e.target.value }))} disabled={!editing} type="text" className={inputCls} />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1.5">{t.emailLabel}</label>
                  <input value={authUser?.email ?? ''} disabled type="email" className={inputCls} />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1.5">{t.phoneLabel}</label>
                  <input value={profileForm.phone} onChange={e => setProfileForm(f => ({ ...f, phone: e.target.value }))} disabled={!editing} type="tel" className={inputCls} />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1.5">{t.deptLabel}</label>
                  <input value={profileForm.department} onChange={e => setProfileForm(f => ({ ...f, department: e.target.value }))} disabled={!editing} type="text" className={inputCls} />
                </div>
              </div>
              <div className="mt-4 flex items-center justify-end gap-3">
                {saved && <span className="text-xs text-emerald-600 dark:text-emerald-400">{t.saved}</span>}
                <Button variant="primary" icon={<Check size={14} />} onClick={handleSaveProfile} disabled={saving || !editing}>{saving ? t.saving : t.saveChanges}</Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center gap-2.5">
                <IconBadge icon={<Shield size={16} />} color="emerald" size="sm" />
                <span className="font-semibold text-gray-900 dark:text-white">{t.securityTitle}</span>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between gap-3 p-3.5 bg-emerald-50/60 dark:bg-emerald-500/5 border border-emerald-100 dark:border-emerald-900/40 rounded-lg">
                <div className="flex items-center gap-3 min-w-0">
                  <Lock size={16} className="text-emerald-500 flex-shrink-0" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-700 dark:text-gray-200 truncate">{t.twoFactor}</p>
                    <p className="text-xs text-gray-500 truncate">{t.twoFactorDesc}</p>
                  </div>
                </div>
                <Toggle on={twoFactor} onChange={() => setTwoFactor(v => !v)} />
              </div>
              <div className="flex items-center justify-between gap-3 p-3.5 bg-gray-50 dark:bg-gray-700/30 rounded-lg">
                <div className="flex items-center gap-3 min-w-0">
                  <Key size={16} className="text-gray-400 flex-shrink-0" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-700 dark:text-gray-200 truncate">{t.changePassword}</p>
                    <p className="text-xs text-gray-500 truncate">{t.changePasswordDesc}</p>
                  </div>
                </div>
                <button className="flex-shrink-0 px-3 py-1.5 text-xs font-medium rounded-lg border border-emerald-300 text-emerald-700 hover:bg-emerald-50 dark:border-emerald-700 dark:text-emerald-400 dark:hover:bg-emerald-900/20 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/50">
                  {t.changeBtn}
                </button>
              </div>
            </CardContent>
          </Card>

          {isAdmin && (
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2.5">
                  <IconBadge icon={<DatabaseBackup size={16} />} color="cyan" size="sm" />
                  <span className="font-semibold text-gray-900 dark:text-white">{t.backupTitle}</span>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between gap-3 p-3.5 bg-cyan-50/60 dark:bg-cyan-500/5 border border-cyan-100 dark:border-cyan-900/40 rounded-lg">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-700 dark:text-gray-200">{t.backupTitle}</p>
                    <p className="text-xs text-gray-500">{t.backupDesc}</p>
                  </div>
                  <Button size="sm" variant="primary" loading={creatingBackup} onClick={handleCreateBackup}>
                    {creatingBackup ? t.backupCreating : t.backupBtn}
                  </Button>
                </div>
                {backups.length > 0 && (
                  <div className="space-y-1.5">
                    <p className="text-xs text-gray-500 font-medium">{t.backupList}</p>
                    {backups.slice(0, 5).map(b => (
                      <div key={b.filename} className="flex items-center justify-between gap-3 px-3 py-2 bg-gray-50 dark:bg-gray-700/30 rounded-lg">
                        <div className="min-w-0">
                          <p className="text-xs font-mono text-gray-700 dark:text-gray-300 truncate">{b.filename}</p>
                          <p className="text-[11px] text-gray-500">{(b.size / 1024 / 1024).toFixed(1)} MB · {new Date(b.created_at).toLocaleString()}</p>
                        </div>
                        <button
                          onClick={() => adminService.downloadBackup(b.filename)}
                          className="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 dark:hover:text-gray-200 dark:hover:bg-gray-700 transition-colors flex-shrink-0"
                          title={common.export}
                        >
                          <Download size={14} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <div className="flex items-center gap-2.5">
                <IconBadge icon={<Link size={16} />} color="purple" size="sm" />
                <span className="font-semibold text-gray-900 dark:text-white">{t.integrationsTitle}</span>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {integrations.map(({ name, desc, icon, color, connected }) => (
                <div key={name} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 p-3.5 bg-gray-50 dark:bg-gray-700/30 rounded-lg">
                  <div className="flex items-center gap-3 min-w-0">
                    <IconBadge icon={icon} color={color} />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-700 dark:text-gray-200 truncate">{name}</p>
                      <p className="text-xs text-gray-500 truncate">{desc}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2.5 flex-shrink-0">
                    <Badge variant={connected ? 'success' : 'default'}>{connected ? t.connected : t.notConnected}</Badge>
                    {name === 'Telegram' ? (
                      <Button
                        size="sm"
                        variant={connected ? 'danger' : 'primary'}
                        loading={telegramLinking}
                        onClick={connected ? handleTelegramUnlink : handleTelegramLink}
                      >
                        {connected ? t.disconnectBtn : t.connectBtn}
                      </Button>
                    ) : (
                      <Button size="sm" variant={connected ? 'danger' : 'primary'} disabled>
                        {connected ? t.disconnectBtn : t.connectBtn}
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          {telegramLinkData && (
            <Card className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
              <CardHeader>
                <div className="flex items-center gap-2.5">
                  <span className="font-semibold text-blue-900 dark:text-blue-300">🔗 Telegram Linking Token</span>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <p className="text-xs text-blue-700 dark:text-blue-400 mb-2">Token:</p>
                  <div className="bg-white dark:bg-gray-800 p-2 rounded border border-blue-200 dark:border-blue-700">
                    <code className="text-xs text-gray-700 dark:text-gray-300 break-all">{telegramLinkData.token}</code>
                  </div>
                </div>
                <div>
                  <p className="text-xs text-blue-700 dark:text-blue-400 mb-2">Telegram Link:</p>
                  <a href={telegramLinkData.telegram_link} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:text-blue-700 dark:text-blue-400 text-xs break-all">
                    {telegramLinkData.telegram_link}
                  </a>
                </div>
                <div className="bg-blue-100 dark:bg-blue-800/50 p-2 rounded text-xs text-blue-800 dark:text-blue-200">
                  <p>📱 Telegramda bosing yoki bu komanada yuboring:</p>
                  <code className="block mt-1 bg-white dark:bg-gray-800 p-1 rounded">/link {telegramLinkData.token}</code>
                </div>
                <button onClick={() => setTelegramLinkData(null)} className="text-xs text-blue-600 dark:text-blue-400 hover:underline">
                  Yopish
                </button>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right panel */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2.5">
                <IconBadge icon={<Bell size={16} />} color="amber" size="sm" />
                <span className="font-semibold text-gray-900 dark:text-white">{t.notificationsTitle}</span>
              </div>
            </CardHeader>
            <CardContent className="space-y-1">
              {notifItems.map(({ key, label, desc, icon, color }) => (
                <div key={key} className="flex items-center justify-between gap-3 py-2.5">
                  <div className="flex items-center gap-3 min-w-0">
                    <IconBadge icon={icon} color={color} size="sm" />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-700 dark:text-gray-200 truncate">{label}</p>
                      <p className="text-xs text-gray-500 truncate">{desc}</p>
                    </div>
                  </div>
                  <Toggle on={notifPrefs[key]} onChange={() => setNotifPrefs(p => ({ ...p, [key]: !p[key] }))} />
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div className="flex items-center gap-2.5">
                <IconBadge icon={<Globe size={16} />} color="blue" size="sm" />
                <span className="font-semibold text-gray-900 dark:text-white">{t.interfaceTitle}</span>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  <IconBadge icon={darkMode ? <Moon size={16} /> : <Sun size={16} />} color="indigo" size="sm" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-700 dark:text-gray-200 truncate">{t.darkTheme}</p>
                    <p className="text-xs text-gray-500 truncate">{t.darkThemeDesc}</p>
                  </div>
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
