import { useState } from 'react';
import { Layout } from '../components/layout/Layout';
import { Card } from '../components/ui/Card';
import { Badge, getTaskStatusBadge, getPriorityBadge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { Avatar } from '../components/ui/Avatar';
import { useStore } from '../store/useStore';
import { Plus, MessageSquare, Paperclip, AlertTriangle, LayoutGrid, List } from 'lucide-react';
import { taskStatusLabels, priorityLabels } from '../data/mockData';
import type { Task, TaskStatus } from '../types';
import { clsx } from 'clsx';

const COLUMNS: { status: TaskStatus; label: string; color: string }[] = [
  { status: 'new', label: 'Новые', color: 'border-blue-700' },
  { status: 'in_progress', label: 'В работе', color: 'border-purple-700' },
  { status: 'review', label: 'На проверке', color: 'border-amber-700' },
  { status: 'revision', label: 'Доработка', color: 'border-red-700' },
  { status: 'approved', label: 'Согласовано', color: 'border-emerald-700' },
  { status: 'completed', label: 'Завершено', color: 'border-gray-700' },
];

function TaskCard({ task, onClick }: { task: Task; onClick: () => void }) {
  const { users, projects } = useStore();
  const assignee = users.find(u => u.id === task.assigneeId);
  const project = projects.find(p => p.id === task.projectId);
  const isOverdue = task.status !== 'completed' && new Date(task.deadline) < new Date();

  return (
    <div onClick={onClick} className="bg-gray-800 border border-gray-700 rounded-xl p-3.5 cursor-pointer hover:border-gray-600 hover:bg-gray-750 transition-all">
      <div className="flex items-start justify-between gap-2 mb-2">
        <p className="text-sm text-gray-200 font-medium leading-tight">{task.title}</p>
        <Badge variant={getPriorityBadge(task.priority)} size="sm">{priorityLabels[task.priority]}</Badge>
      </div>
      {project && <p className="text-xs text-gray-600 mb-2 truncate">{project.name}</p>}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {assignee && <><Avatar name={assignee.name} size="xs" /><span className="text-xs text-gray-500 truncate max-w-20">{assignee.name.split(' ')[0]}</span></>}
        </div>
        <div className="flex items-center gap-2 text-xs">
          {task.comments.length > 0 && <span className="text-gray-600 flex items-center gap-0.5"><MessageSquare size={10} /> {task.comments.length}</span>}
          {task.attachments.length > 0 && <span className="text-gray-600 flex items-center gap-0.5"><Paperclip size={10} /> {task.attachments.length}</span>}
          <span className={clsx('flex items-center gap-0.5', isOverdue ? 'text-red-400' : 'text-gray-600')}>
            {isOverdue && <AlertTriangle size={10} />} {task.deadline}
          </span>
        </div>
      </div>
    </div>
  );
}

export default function Tasks() {
  const { tasks, projects, users, addTask, updateTask, authUser } = useStore();
  const [view, setView] = useState<'kanban' | 'list'>('kanban');
  const [selected, setSelected] = useState<Task | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [filterProject, setFilterProject] = useState('all');
  const [filterAssignee, setFilterAssignee] = useState('all');
  const [form, setForm] = useState({ title: '', description: '', projectId: '', assigneeId: '', deadline: '', priority: 'medium', status: 'new' });

  const filtered = tasks.filter(t => {
    const mp = filterProject === 'all' || t.projectId === filterProject;
    const ma = filterAssignee === 'all' || t.assigneeId === filterAssignee;
    return mp && ma;
  });

  const handleCreate = () => {
    if (!form.title) return;
    addTask({
      id: 't' + Date.now(), title: form.title, description: form.description,
      projectId: form.projectId, assigneeId: form.assigneeId,
      creatorId: authUser?.id || 'u1', status: form.status as any,
      priority: form.priority as any, deadline: form.deadline,
      createdAt: new Date().toISOString().split('T')[0],
      updatedAt: new Date().toISOString().split('T')[0],
      attachments: [], comments: [],
    });
    setShowCreate(false);
    setForm({ title: '', description: '', projectId: '', assigneeId: '', deadline: '', priority: 'medium', status: 'new' });
  };

  return (
    <Layout title="Задачи" subtitle={`${tasks.length} задач в системе`}>
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <select value={filterProject} onChange={e => setFilterProject(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500">
          <option value="all">Все проекты</option>
          {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <select value={filterAssignee} onChange={e => setFilterAssignee(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500">
          <option value="all">Все исполнители</option>
          {users.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}
        </select>
        <div className="flex gap-1 ml-auto">
          <button onClick={() => setView('kanban')} className={clsx('p-2 rounded-lg transition-colors', view === 'kanban' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700')}>
            <LayoutGrid size={16} />
          </button>
          <button onClick={() => setView('list')} className={clsx('p-2 rounded-lg transition-colors', view === 'list' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700')}>
            <List size={16} />
          </button>
        </div>
        <Button variant="primary" icon={<Plus size={16} />} onClick={() => setShowCreate(true)}>Новая задача</Button>
      </div>

      {/* Kanban */}
      {view === 'kanban' && (
        <div className="flex gap-4 overflow-x-auto pb-4">
          {COLUMNS.map(col => {
            const colTasks = filtered.filter(t => t.status === col.status);
            return (
              <div key={col.status} className="flex-shrink-0 w-64">
                <div className={clsx('flex items-center justify-between mb-3 px-1 pb-2 border-b-2', col.color)}>
                  <span className="text-sm font-semibold text-gray-300">{col.label}</span>
                  <span className="text-xs bg-gray-700 text-gray-400 rounded-full px-2 py-0.5">{colTasks.length}</span>
                </div>
                <div className="space-y-2">
                  {colTasks.map(t => <TaskCard key={t.id} task={t} onClick={() => setSelected(t)} />)}
                  {colTasks.length === 0 && <div className="text-center py-8 text-gray-700 text-xs">Нет задач</div>}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* List */}
      {view === 'list' && (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-700">
                  {['Задача', 'Проект', 'Исполнитель', 'Статус', 'Приоритет', 'Дедлайн'].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs text-gray-500 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map(t => {
                  const assignee = users.find(u => u.id === t.assigneeId);
                  const project = projects.find(p => p.id === t.projectId);
                  const isOverdue = t.status !== 'completed' && new Date(t.deadline) < new Date();
                  return (
                    <tr key={t.id} onClick={() => setSelected(t)} className="border-b border-gray-800 hover:bg-gray-800/50 cursor-pointer transition-colors">
                      <td className="px-4 py-3">
                        <p className="text-sm text-gray-200 max-w-xs truncate">{t.title}</p>
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-500">{project?.name}</td>
                      <td className="px-4 py-3">
                        {assignee && <div className="flex items-center gap-2"><Avatar name={assignee.name} size="xs" /><span className="text-xs text-gray-400">{assignee.name}</span></div>}
                      </td>
                      <td className="px-4 py-3"><Badge variant={getTaskStatusBadge(t.status)} size="sm">{taskStatusLabels[t.status]}</Badge></td>
                      <td className="px-4 py-3"><Badge variant={getPriorityBadge(t.priority)} size="sm">{priorityLabels[t.priority]}</Badge></td>
                      <td className={clsx('px-4 py-3 text-xs', isOverdue ? 'text-red-400' : 'text-gray-500')}>
                        {isOverdue && <AlertTriangle size={10} className="inline mr-1" />}{t.deadline}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Task Detail Modal */}
      {selected && (
        <Modal open={!!selected} onClose={() => setSelected(null)} title={selected.title} size="lg"
          footer={
            <div className="flex items-center justify-between">
              <div className="flex gap-2">
                {COLUMNS.map(col => (
                  <button key={col.status} onClick={() => { updateTask({ ...selected, status: col.status }); setSelected({ ...selected, status: col.status }); }}
                    className={clsx('px-3 py-1.5 text-xs rounded-lg transition-colors', selected.status === col.status ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-400 hover:bg-gray-600')}>
                    {col.label}
                  </button>
                ))}
              </div>
              <Button onClick={() => setSelected(null)}>Закрыть</Button>
            </div>
          }>
          <div className="space-y-4">
            <div className="flex gap-2">
              <Badge variant={getTaskStatusBadge(selected.status)}>{taskStatusLabels[selected.status]}</Badge>
              <Badge variant={getPriorityBadge(selected.priority)}>{priorityLabels[selected.priority]}</Badge>
            </div>
            {selected.description && <p className="text-sm text-gray-400 bg-gray-700/30 p-3 rounded-lg">{selected.description}</p>}
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="bg-gray-700/30 p-3 rounded-lg">
                <p className="text-xs text-gray-500 mb-1">Исполнитель</p>
                {users.find(u => u.id === selected.assigneeId) && <div className="flex items-center gap-2"><Avatar name={users.find(u => u.id === selected.assigneeId)!.name} size="xs" /><span className="text-gray-200">{users.find(u => u.id === selected.assigneeId)!.name}</span></div>}
              </div>
              <div className="bg-gray-700/30 p-3 rounded-lg">
                <p className="text-xs text-gray-500 mb-1">Дедлайн</p>
                <p className="text-gray-200">{selected.deadline}</p>
              </div>
            </div>
            {selected.comments.length > 0 && (
              <div>
                <p className="text-xs text-gray-500 mb-2">Комментарии</p>
                <div className="space-y-2">
                  {selected.comments.map(c => {
                    const u = users.find(u => u.id === c.userId);
                    return (
                      <div key={c.id} className="flex gap-2 bg-gray-700/30 p-3 rounded-lg">
                        {u && <Avatar name={u.name} size="xs" />}
                        <div>
                          <p className="text-xs text-gray-400 mb-1">{u?.name} · {c.createdAt}</p>
                          <p className="text-sm text-gray-300">{c.text}</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </Modal>
      )}

      {/* Create Modal */}
      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Новая задача" size="lg"
        footer={<div className="flex justify-end gap-3"><Button onClick={() => setShowCreate(false)}>Отмена</Button><Button variant="primary" onClick={handleCreate}>Создать</Button></div>}>
        <div className="space-y-4">
          <div>
            <label className="block text-xs text-gray-400 mb-1.5">Название *</label>
            <input value={form.title} onChange={e => setForm({ ...form, title: e.target.value })}
              className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2.5 text-sm text-gray-200 focus:outline-none focus:border-blue-500" />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1.5">Описание</label>
            <textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} rows={3}
              className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2.5 text-sm text-gray-200 focus:outline-none focus:border-blue-500 resize-none" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">Проект</label>
              <select value={form.projectId} onChange={e => setForm({ ...form, projectId: e.target.value })}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2.5 text-sm text-gray-200 focus:outline-none focus:border-blue-500">
                <option value="">— Не выбран —</option>
                {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">Исполнитель</label>
              <select value={form.assigneeId} onChange={e => setForm({ ...form, assigneeId: e.target.value })}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2.5 text-sm text-gray-200 focus:outline-none focus:border-blue-500">
                <option value="">— Не назначен —</option>
                {users.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">Дедлайн</label>
              <input type="date" value={form.deadline} onChange={e => setForm({ ...form, deadline: e.target.value })}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2.5 text-sm text-gray-200 focus:outline-none focus:border-blue-500" />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">Приоритет</label>
              <select value={form.priority} onChange={e => setForm({ ...form, priority: e.target.value })}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2.5 text-sm text-gray-200 focus:outline-none focus:border-blue-500">
                {Object.entries(priorityLabels).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
          </div>
        </div>
      </Modal>
    </Layout>
  );
}
