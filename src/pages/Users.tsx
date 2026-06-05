import { useState } from 'react';
import { Layout } from '../components/layout/Layout';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { Avatar } from '../components/ui/Avatar';
import { useStore } from '../store/useStore';
import { Plus, Search, Mail, Phone, Shield } from 'lucide-react';
import { roleLabels } from '../data/mockData';
import type { UserRole } from '../types';
import { clsx } from 'clsx';

const roleColors: Record<UserRole, string> = {
  admin: 'bg-red-900/50 text-red-400 border border-red-800',
  manager: 'bg-purple-900/50 text-purple-400 border border-purple-800',
  gip: 'bg-blue-900/50 text-blue-400 border border-blue-800',
  gip_assistant: 'bg-cyan-900/50 text-cyan-400 border border-cyan-800',
  designer: 'bg-emerald-900/50 text-emerald-400 border border-emerald-800',
  reviewer: 'bg-amber-900/50 text-amber-400 border border-amber-800',
  client: 'bg-gray-700 text-gray-400',
};

export default function Users() {
  const { users } = useStore();
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('all');
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: '', email: '', role: 'designer', department: '', phone: '' });

  const filtered = users.filter(u => {
    const ms = u.name.toLowerCase().includes(search.toLowerCase()) || u.email.toLowerCase().includes(search.toLowerCase());
    const mr = roleFilter === 'all' || u.role === roleFilter;
    return ms && mr;
  });

  const roles = Object.entries(roleLabels);

  return (
    <Layout title="Сотрудники" subtitle="Управление пользователями и доступом">
      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        {[
          { label: 'Всего', count: users.length, color: 'text-white' },
          { label: 'Активных', count: users.filter(u => u.isActive).length, color: 'text-emerald-400' },
          { label: 'ГИП', count: users.filter(u => u.role === 'gip').length, color: 'text-blue-400' },
          { label: 'Проектировщиков', count: users.filter(u => u.role === 'designer').length, color: 'text-purple-400' },
        ].map(({ label, count, color }) => (
          <div key={label} className="bg-gray-800 border border-gray-700 rounded-xl p-4">
            <p className={clsx('text-2xl font-bold', color)}>{count}</p>
            <p className="text-xs text-gray-500 mt-1">{label}</p>
          </div>
        ))}
      </div>

      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <div className="relative flex-1 min-w-48">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Поиск сотрудников..."
            className="w-full bg-gray-800 border border-gray-700 rounded-lg pl-9 pr-4 py-2 text-sm text-gray-300 placeholder-gray-600 focus:outline-none focus:border-blue-500" />
        </div>
        <div className="flex gap-2 flex-wrap">
          <button onClick={() => setRoleFilter('all')} className={`px-3 py-2 text-sm rounded-lg transition-colors ${roleFilter === 'all' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}>Все</button>
          {roles.map(([k, v]) => (
            <button key={k} onClick={() => setRoleFilter(k)} className={`px-3 py-2 text-sm rounded-lg transition-colors ${roleFilter === k ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}>{v}</button>
          ))}
        </div>
        <Button variant="primary" icon={<Plus size={16} />} onClick={() => setShowCreate(true)}>Добавить</Button>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {filtered.map(user => {
          const taskCount = useStore.getState().tasks.filter(t => t.assigneeId === user.id && t.status !== 'completed').length;
          const projectCount = useStore.getState().projects.filter(p => p.participants.includes(user.id)).length;
          return (
            <Card key={user.id} hover className="p-5">
              <div className="flex items-start justify-between mb-4">
                <Avatar name={user.name} size="lg" />
                <div className="flex flex-col items-end gap-2">
                  <span className={clsx('text-xs font-medium px-2 py-0.5 rounded-full', roleColors[user.role])}>{roleLabels[user.role]}</span>
                  <span className={clsx('w-2 h-2 rounded-full', user.isActive ? 'bg-emerald-400' : 'bg-gray-600')} />
                </div>
              </div>
              <h3 className="font-semibold text-white mb-1">{user.name}</h3>
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
              <div className="mt-4 pt-3 border-t border-gray-700 flex justify-between text-xs text-gray-500">
                <span>{projectCount} проектов</span>
                <span>{taskCount} задач</span>
              </div>
            </Card>
          );
        })}
      </div>

      {/* Create Modal */}
      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Новый сотрудник"
        footer={<div className="flex justify-end gap-3"><Button onClick={() => setShowCreate(false)}>Отмена</Button><Button variant="primary" icon={<Plus size={16} />}>Добавить</Button></div>}>
        <div className="space-y-4">
          <div>
            <label className="block text-xs text-gray-400 mb-1.5">ФИО *</label>
            <input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
              className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2.5 text-sm text-gray-200 focus:outline-none focus:border-blue-500" />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1.5">Email *</label>
            <input type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })}
              className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2.5 text-sm text-gray-200 focus:outline-none focus:border-blue-500" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">Роль</label>
              <select value={form.role} onChange={e => setForm({ ...form, role: e.target.value })}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2.5 text-sm text-gray-200 focus:outline-none focus:border-blue-500">
                {roles.map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">Отдел</label>
              <input value={form.department} onChange={e => setForm({ ...form, department: e.target.value })}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2.5 text-sm text-gray-200 focus:outline-none focus:border-blue-500" />
            </div>
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1.5">Телефон</label>
            <input value={form.phone} onChange={e => setForm({ ...form, phone: e.target.value })}
              className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2.5 text-sm text-gray-200 focus:outline-none focus:border-blue-500" />
          </div>
          <div className="bg-gray-700/30 p-3 rounded-lg flex items-center gap-2">
            <Shield size={14} className="text-blue-400" />
            <p className="text-xs text-gray-400">Доступ будет настроен в соответствии с выбранной ролью</p>
          </div>
        </div>
      </Modal>
    </Layout>
  );
}
