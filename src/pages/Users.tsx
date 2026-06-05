import { useState } from 'react';
import { Layout } from '../components/layout/Layout';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { Avatar } from '../components/ui/Avatar';
import { useStore } from '../store/useStore';
import { Plus, Search, Mail, Phone, Shield } from 'lucide-react';
import type { UserRole } from '../types';
import { clsx } from 'clsx';
import { translations } from '../i18n/translations';

const roleColors: Record<UserRole, string> = {
  admin: 'bg-red-50 text-red-700 border border-red-200 dark:bg-red-900/50 dark:text-red-400 dark:border-red-800',
  manager: 'bg-purple-50 text-purple-700 border border-purple-200 dark:bg-purple-900/50 dark:text-purple-400 dark:border-purple-800',
  gip: 'bg-blue-50 text-blue-700 border border-blue-200 dark:bg-blue-900/50 dark:text-blue-400 dark:border-blue-800',
  gip_assistant: 'bg-cyan-50 text-cyan-700 border border-cyan-200 dark:bg-cyan-900/50 dark:text-cyan-400 dark:border-cyan-800',
  designer: 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-900/50 dark:text-emerald-400 dark:border-emerald-800',
  reviewer: 'bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-900/50 dark:text-amber-400 dark:border-amber-800',
  client: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400',
};

export default function Users() {
  const { users, language } = useStore();
  const t = translations[language].users;
  const roles = translations[language].roles;

  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('all');
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: '', email: '', role: 'designer', department: '', phone: '' });

  const filtered = users.filter(u => {
    const ms = u.name.toLowerCase().includes(search.toLowerCase()) || u.email.toLowerCase().includes(search.toLowerCase());
    const mr = roleFilter === 'all' || u.role === roleFilter;
    return ms && mr;
  });

  const roleEntries = Object.entries(roles);

  const filterBtnCls = (active: boolean) =>
    `px-3 py-2 text-sm rounded-lg transition-colors ${active ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700'}`;

  const inputCls = "w-full bg-gray-100 border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-700 focus:outline-none focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200";

  return (
    <Layout title={t.title} subtitle={t.subtitle}>
      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        {[
          { label: t.total, count: users.length, color: 'text-gray-900 dark:text-white' },
          { label: t.active, count: users.filter(u => u.isActive).length, color: 'text-emerald-600 dark:text-emerald-400' },
          { label: t.gipCount, count: users.filter(u => u.role === 'gip').length, color: 'text-blue-600 dark:text-blue-400' },
          { label: t.designersCount, count: users.filter(u => u.role === 'designer').length, color: 'text-purple-600 dark:text-purple-400' },
        ].map(({ label, count, color }) => (
          <div key={label} className="bg-white border border-gray-200 rounded-xl p-4 dark:bg-gray-800 dark:border-gray-700">
            <p className={clsx('text-2xl font-bold', color)}>{count}</p>
            <p className="text-xs text-gray-500 mt-1">{label}</p>
          </div>
        ))}
      </div>

      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <div className="relative flex-1 min-w-48">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500" />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder={t.searchPlaceholder}
            className="w-full bg-gray-100 border border-gray-200 rounded-lg pl-9 pr-4 py-2 text-sm text-gray-700 placeholder-gray-400 focus:outline-none focus:border-blue-500 dark:bg-gray-800 dark:border-gray-700 dark:text-gray-300 dark:placeholder-gray-600" />
        </div>
        <div className="flex gap-2 flex-wrap">
          <button onClick={() => setRoleFilter('all')} className={filterBtnCls(roleFilter === 'all')}>{t.all}</button>
          {roleEntries.map(([k, v]) => (
            <button key={k} onClick={() => setRoleFilter(k)} className={filterBtnCls(roleFilter === k)}>{v}</button>
          ))}
        </div>
        <Button variant="primary" icon={<Plus size={16} />} onClick={() => setShowCreate(true)}>{t.addButton}</Button>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {filtered.map(user => {
          const taskCount = useStore.getState().tasks.filter(task => task.assigneeId === user.id && task.status !== 'completed').length;
          const projectCount = useStore.getState().projects.filter(p => p.participants.includes(user.id)).length;
          return (
            <Card key={user.id} hover className="p-5">
              <div className="flex items-start justify-between mb-4">
                <Avatar name={user.name} size="lg" />
                <div className="flex flex-col items-end gap-2">
                  <span className={clsx('text-xs font-medium px-2 py-0.5 rounded-full', roleColors[user.role])}>{roles[user.role] ?? user.role}</span>
                  <span className={clsx('w-2 h-2 rounded-full', user.isActive ? 'bg-emerald-400' : 'bg-gray-400 dark:bg-gray-600')} />
                </div>
              </div>
              <h3 className="font-semibold text-gray-900 dark:text-white mb-1">{user.name}</h3>
              {user.department && <p className="text-xs text-gray-500 mb-3">{user.department}</p>}
              <div className="space-y-2 text-xs">
                <div className="flex items-center gap-2 text-gray-500">
                  <Mail size={12} className="flex-shrink-0" />
                  <span className="truncate">{user.email}</span>
                </div>
                {user.phone && (
                  <div className="flex items-center gap-2 text-gray-500">
                    <Phone size={12} className="flex-shrink-0" />
                    <span>{user.phone}</span>
                  </div>
                )}
              </div>
              <div className="mt-4 pt-3 border-t border-gray-200 dark:border-gray-700 flex justify-between text-xs text-gray-500">
                <span>{projectCount} {t.projectsCount}</span>
                <span>{taskCount} {t.tasksCount}</span>
              </div>
            </Card>
          );
        })}
      </div>

      {/* Create Modal */}
      <Modal open={showCreate} onClose={() => setShowCreate(false)} title={t.newEmployee}
        footer={<div className="flex justify-end gap-3"><Button onClick={() => setShowCreate(false)}>{translations[language].common.cancel}</Button><Button variant="primary" icon={<Plus size={16} />}>{t.addButton}</Button></div>}>
        <div className="space-y-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1.5">{t.fullNameLabel}</label>
            <input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className={inputCls} />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1.5">{t.emailLabel}</label>
            <input type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} className={inputCls} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1.5">{t.roleLabel}</label>
              <select value={form.role} onChange={e => setForm({ ...form, role: e.target.value })} className={inputCls}>
                {roleEntries.map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1.5">{t.departmentLabel}</label>
              <input value={form.department} onChange={e => setForm({ ...form, department: e.target.value })} className={inputCls} />
            </div>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1.5">{t.phoneLabel}</label>
            <input value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })} className={inputCls} />
          </div>
          <div className="bg-blue-50 dark:bg-gray-700/30 p-3 rounded-lg flex items-center gap-2">
            <Shield size={14} className="text-blue-500 dark:text-blue-400" />
            <p className="text-xs text-gray-600 dark:text-gray-400">{t.accessNote}</p>
          </div>
        </div>
      </Modal>
    </Layout>
  );
}
