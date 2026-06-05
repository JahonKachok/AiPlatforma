import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '../components/layout/Layout';
import { Card } from '../components/ui/Card';
import { Badge, getProjectStatusBadge, getPriorityBadge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { Avatar } from '../components/ui/Avatar';
import { useStore } from '../store/useStore';
import { Plus, Search, Filter, Clock, Users, DollarSign, Layers } from 'lucide-react';
import type { Project } from '../types';
import { translations } from '../i18n/translations';

const inputCls = "w-full bg-gray-100 border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-700 focus:outline-none focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200";
const selectCls = "w-full bg-gray-100 border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-700 focus:outline-none focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200";

function ProjectCard({ project }: { project: Project }) {
  const { users, language } = useStore();
  const t = translations[language];
  const navigate = useNavigate();
  const gip = users.find(u => u.id === project.gipId);
  const progress = project.budget > 0 ? Math.round((project.paid / project.budget) * 100) : 0;
  const taskCount = useStore.getState().tasks.filter(t => t.projectId === project.id).length;

  return (
    <Card hover onClick={() => navigate(`/projects/${project.id}`)} className="flex flex-col">
      <div className="p-5">
        <div className="flex items-start justify-between gap-2 mb-3">
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white text-base leading-tight">{project.name}</h3>
            <p className="text-sm text-gray-500 mt-1">{project.client}</p>
          </div>
          <Badge variant={getProjectStatusBadge(project.status)}>{t.projectStatus[project.status] ?? project.status}</Badge>
        </div>

        <div className="grid grid-cols-2 gap-2 mb-4 text-xs">
          <div className="flex items-center gap-1.5 text-gray-500">
            <Clock size={12} /> {t.projects.until} {project.deadline}
          </div>
          <div className="flex items-center gap-1.5 text-gray-500">
            <Layers size={12} /> {t.projectStage[project.stage] ?? project.stage}
          </div>
          <div className="flex items-center gap-1.5 text-gray-500">
            <Users size={12} /> {project.participants.length} {t.projects.participants}
          </div>
          <div className="flex items-center gap-1.5 text-gray-500">
            <DollarSign size={12} /> {(project.budget / 1000000).toFixed(0)} {t.dashboard.mln}
          </div>
        </div>

        <div className="mb-4">
          <div className="flex justify-between text-xs text-gray-500 mb-1">
            <span>{t.projects.paymentLabel}</span>
            <span>{progress}%</span>
          </div>
          <div className="h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div className="h-full bg-emerald-500 rounded-full transition-all" style={{ width: `${progress}%` }} />
          </div>
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {gip && <><Avatar name={gip.name} size="xs" /><span className="text-xs text-gray-500">{gip.name}</span></>}
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={getPriorityBadge(project.priority)}>{t.priority[project.priority] ?? project.priority}</Badge>
            <span className="text-xs text-gray-400">{taskCount} {t.projects.tasksCount}</span>
          </div>
        </div>
      </div>
    </Card>
  );
}

export default function Projects() {
  const { projects, users, addProject, authUser, language } = useStore();
  const t = translations[language];
  const pt = t.projects;
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: '', client: '', address: '', stage: 'concept', deadline: '', gipId: '', budget: '', priority: 'medium' });

  const filtered = projects.filter(p => {
    const matchSearch = p.name.toLowerCase().includes(search.toLowerCase()) || p.client.toLowerCase().includes(search.toLowerCase());
    const matchStatus = statusFilter === 'all' || p.status === statusFilter;
    return matchSearch && matchStatus;
  });

  const gips = users.filter(u => u.role === 'gip' || u.role === 'admin' || u.role === 'manager');

  const handleCreate = () => {
    if (!form.name || !form.client) return;
    const project: Project = {
      id: 'p' + Date.now(), name: form.name, client: form.client, address: form.address,
      stage: form.stage as any, status: 'planning', deadline: form.deadline,
      startDate: new Date().toISOString().split('T')[0], gipId: form.gipId,
      budget: Number(form.budget) || 0, paid: 0, priority: form.priority as any,
      participants: form.gipId ? [form.gipId] : [],
      sections: [], objects: [],
    };
    addProject(project);
    setShowCreate(false);
    setForm({ name: '', client: '', address: '', stage: 'concept', deadline: '', gipId: '', budget: '', priority: 'medium' });
  };

  const filterBtnCls = (active: boolean) =>
    `px-3 py-2 text-sm rounded-lg transition-colors ${active ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700'}`;

  const statusFilters = [
    { key: 'all', label: pt.all },
    { key: 'active', label: t.projectStatus.active },
    { key: 'planning', label: t.projectStatus.planning },
    { key: 'completed', label: t.projectStatus.completed },
    { key: 'paused', label: t.projectStatus.paused },
  ];

  return (
    <Layout title={pt.title} subtitle={`${projects.length} ${pt.inSystem}`}>
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <div className="relative flex-1 min-w-48">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500" />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder={pt.searchPlaceholder}
            className="w-full bg-gray-100 border border-gray-200 rounded-lg pl-9 pr-4 py-2 text-sm text-gray-700 placeholder-gray-400 focus:outline-none focus:border-blue-500 dark:bg-gray-800 dark:border-gray-700 dark:text-gray-300 dark:placeholder-gray-600" />
        </div>
        <div className="flex gap-2 flex-wrap">
          {statusFilters.map(({ key, label }) => (
            <button key={key} onClick={() => setStatusFilter(key)} className={filterBtnCls(statusFilter === key)}>{label}</button>
          ))}
        </div>
        {(authUser?.role === 'admin' || authUser?.role === 'manager' || authUser?.role === 'gip') && (
          <Button variant="primary" icon={<Plus size={16} />} onClick={() => setShowCreate(true)}>{pt.newProject}</Button>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-6">
        {[
          { label: pt.total, count: projects.length, color: 'text-gray-700 dark:text-gray-400' },
          { label: pt.active, count: projects.filter(p => p.status === 'active').length, color: 'text-emerald-600 dark:text-emerald-400' },
          { label: pt.planning, count: projects.filter(p => p.status === 'planning').length, color: 'text-blue-600 dark:text-blue-400' },
          { label: pt.completed, count: projects.filter(p => p.status === 'completed').length, color: 'text-gray-500' },
          { label: pt.paused, count: projects.filter(p => p.status === 'paused').length, color: 'text-amber-600 dark:text-amber-400' },
        ].map(({ label, count, color }) => (
          <div key={label} className="bg-white border border-gray-200 rounded-xl p-4 dark:bg-gray-800 dark:border-gray-700">
            <p className={`text-2xl font-bold ${color}`}>{count}</p>
            <p className="text-xs text-gray-500 mt-1">{label}</p>
          </div>
        ))}
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filtered.map(p => <ProjectCard key={p.id} project={p} />)}
        {filtered.length === 0 && (
          <div className="col-span-3 text-center py-20 text-gray-400">
            <Filter size={40} className="mx-auto mb-3 opacity-30" />
            <p>{pt.notFound}</p>
          </div>
        )}
      </div>

      {/* Create Modal */}
      <Modal open={showCreate} onClose={() => setShowCreate(false)} title={pt.createTitle} size="lg"
        footer={<div className="flex justify-end gap-3"><Button onClick={() => setShowCreate(false)}>{pt.cancel}</Button><Button variant="primary" onClick={handleCreate}>{pt.create}</Button></div>}>
        <div className="grid grid-cols-2 gap-4">
          {[
            { label: pt.nameLabel, key: 'name', type: 'text', span: 2 },
            { label: pt.clientLabel, key: 'client', type: 'text', span: 1 },
            { label: pt.addressLabel, key: 'address', type: 'text', span: 1 },
            { label: pt.deadlineLabel, key: 'deadline', type: 'date', span: 1 },
            { label: pt.budgetLabel, key: 'budget', type: 'number', span: 1 },
          ].map(({ label, key, type, span }) => (
            <div key={key} className={span === 2 ? 'col-span-2' : ''}>
              <label className="block text-xs text-gray-500 mb-1.5">{label}</label>
              <input type={type} value={(form as any)[key]} onChange={e => setForm({ ...form, [key]: e.target.value })} className={inputCls} />
            </div>
          ))}
          <div>
            <label className="block text-xs text-gray-500 mb-1.5">{pt.stageLabel}</label>
            <select value={form.stage} onChange={e => setForm({ ...form, stage: e.target.value })} className={selectCls}>
              {Object.entries(t.projectStage).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1.5">{pt.priorityLabel}</label>
            <select value={form.priority} onChange={e => setForm({ ...form, priority: e.target.value })} className={selectCls}>
              {Object.entries(t.priority).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>
          <div className="col-span-2">
            <label className="block text-xs text-gray-500 mb-1.5">{pt.gipLabel}</label>
            <select value={form.gipId} onChange={e => setForm({ ...form, gipId: e.target.value })} className={selectCls}>
              <option value="">{pt.notAssigned}</option>
              {gips.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}
            </select>
          </div>
        </div>
      </Modal>
    </Layout>
  );
}
