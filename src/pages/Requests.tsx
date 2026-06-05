import { useState } from 'react';
import { Layout } from '../components/layout/Layout';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { Avatar } from '../components/ui/Avatar';
import { useStore } from '../store/useStore';
import { Plus, MessageSquare, Clock } from 'lucide-react';
import { priorityLabels } from '../data/mockData';
import { clsx } from 'clsx';

const statusConfig = {
  discussion: { label: 'Обсуждение', color: 'bg-blue-900/50 text-blue-400 border border-blue-800' },
  clarification: { label: 'Уточнение', color: 'bg-amber-900/50 text-amber-400 border border-amber-800' },
  approval: { label: 'На согласовании', color: 'bg-purple-900/50 text-purple-400 border border-purple-800' },
  completed: { label: 'Выполнено', color: 'bg-emerald-900/50 text-emerald-400 border border-emerald-800' },
};

export default function Requests() {
  const { requests, projects, users, addRequest, updateRequest, authUser } = useStore();
  const [selected, setSelected] = useState<typeof requests[0] | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newComment, setNewComment] = useState('');
  const [form, setForm] = useState({ title: '', description: '', projectId: '', assigneeId: '', priority: 'medium' });

  const handleCreate = () => {
    if (!form.title) return;
    addRequest({
      id: 'r' + Date.now(), title: form.title, description: form.description,
      projectId: form.projectId || undefined, assigneeId: form.assigneeId || undefined,
      creatorId: authUser?.id || 'u1', status: 'discussion',
      priority: form.priority as any, createdAt: new Date().toISOString().split('T')[0], comments: [],
    });
    setShowCreate(false);
    setForm({ title: '', description: '', projectId: '', assigneeId: '', priority: 'medium' });
  };

  const handleAddComment = () => {
    if (!selected || !newComment.trim()) return;
    const updated = {
      ...selected,
      comments: [...selected.comments, { id: 'rc' + Date.now(), userId: authUser?.id || 'u1', text: newComment, createdAt: new Date().toISOString().split('T')[0] }]
    };
    updateRequest(updated);
    setSelected(updated);
    setNewComment('');
  };

  return (
    <Layout title="Запросы и обсуждения" subtitle="Внутренние запросы и переписка">
      <div className="flex items-center justify-between mb-6">
        <div className="flex gap-2">
          {Object.entries(statusConfig).map(([k, v]) => (
            <span key={k} className={clsx('text-xs px-2 py-1 rounded-full', v.color)}>
              {v.label}: {requests.filter(r => r.status === k).length}
            </span>
          ))}
        </div>
        <Button variant="primary" icon={<Plus size={16} />} onClick={() => setShowCreate(true)}>Новый запрос</Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
        {requests.map(req => {
          const creator = users.find(u => u.id === req.creatorId);
          const project = projects.find(p => p.id === req.projectId);
          const cfg = statusConfig[req.status];
          return (
            <Card key={req.id} hover onClick={() => setSelected(req)}>
              <div className="p-4">
                <div className="flex items-start justify-between gap-2 mb-2">
                  <p className="text-sm font-medium text-gray-200">{req.title}</p>
                  <span className={clsx('text-xs px-2 py-0.5 rounded-full flex-shrink-0', cfg.color)}>{cfg.label}</span>
                </div>
                <p className="text-xs text-gray-500 mb-3 line-clamp-2">{req.description}</p>
                {project && <p className="text-xs text-gray-600 mb-2">📁 {project.name}</p>}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {creator && <><Avatar name={creator.name} size="xs" /><span className="text-xs text-gray-500">{creator.name.split(' ')[0]}</span></>}
                  </div>
                  <div className="flex items-center gap-3 text-xs text-gray-600">
                    <span className="flex items-center gap-1"><MessageSquare size={10} /> {req.comments.length}</span>
                    <span className="flex items-center gap-1"><Clock size={10} /> {req.createdAt}</span>
                  </div>
                </div>
              </div>
            </Card>
          );
        })}
        {requests.length === 0 && (
          <div className="col-span-3 text-center py-20 text-gray-600">
            <MessageSquare size={40} className="mx-auto mb-3 opacity-30" />
            <p>Запросов нет</p>
          </div>
        )}
      </div>

      {/* Detail Modal */}
      {selected && (
        <Modal open={!!selected} onClose={() => setSelected(null)} title={selected.title} size="lg"
          footer={
            <div className="flex gap-2 w-full">
              <input value={newComment} onChange={e => setNewComment(e.target.value)} placeholder="Написать комментарий..."
                className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
                onKeyDown={e => e.key === 'Enter' && handleAddComment()} />
              <Button variant="primary" onClick={handleAddComment}>Отправить</Button>
            </div>
          }>
          <div className="space-y-4">
            <div className="flex gap-2">
              <span className={clsx('text-xs px-2 py-0.5 rounded-full', statusConfig[selected.status].color)}>{statusConfig[selected.status].label}</span>
              <Badge variant="default" size="sm">{priorityLabels[selected.priority]}</Badge>
            </div>
            {selected.description && <p className="text-sm text-gray-400 bg-gray-700/30 p-3 rounded-lg">{selected.description}</p>}
            <div className="flex gap-4 text-sm">
              <div>
                <p className="text-xs text-gray-500">Автор</p>
                {users.find(u => u.id === selected.creatorId) && (
                  <div className="flex items-center gap-1.5 mt-1">
                    <Avatar name={users.find(u => u.id === selected.creatorId)!.name} size="xs" />
                    <span className="text-gray-300">{users.find(u => u.id === selected.creatorId)!.name}</span>
                  </div>
                )}
              </div>
              {selected.assigneeId && (
                <div>
                  <p className="text-xs text-gray-500">Ответственный</p>
                  {users.find(u => u.id === selected.assigneeId) && (
                    <div className="flex items-center gap-1.5 mt-1">
                      <Avatar name={users.find(u => u.id === selected.assigneeId)!.name} size="xs" />
                      <span className="text-gray-300">{users.find(u => u.id === selected.assigneeId)!.name}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
            <div className="space-y-2">
              <p className="text-xs text-gray-500">Комментарии ({selected.comments.length})</p>
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
              {selected.comments.length === 0 && <p className="text-xs text-gray-600 text-center py-2">Нет комментариев</p>}
            </div>
          </div>
        </Modal>
      )}

      {/* Create Modal */}
      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Новый запрос"
        footer={<div className="flex justify-end gap-3"><Button onClick={() => setShowCreate(false)}>Отмена</Button><Button variant="primary" onClick={handleCreate}>Создать</Button></div>}>
        <div className="space-y-4">
          <div>
            <label className="block text-xs text-gray-400 mb-1.5">Тема *</label>
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
              <label className="block text-xs text-gray-400 mb-1.5">Ответственный</label>
              <select value={form.assigneeId} onChange={e => setForm({ ...form, assigneeId: e.target.value })}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2.5 text-sm text-gray-200 focus:outline-none focus:border-blue-500">
                <option value="">— Не выбран —</option>
                {users.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}
              </select>
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
