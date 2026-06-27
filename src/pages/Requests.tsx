import { useState } from 'react';
import { Layout } from '../components/layout/Layout';
import { Card } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { Avatar } from '../components/ui/Avatar';
import { useStore } from '../store/useStore';
import { requestService } from '../services/requestService';
import { adaptRequest } from '../services/adapters';
import { Plus, MessageSquare, Clock } from 'lucide-react';
import type { TaskPriority } from '../types';
import { clsx } from 'clsx';
import { translations } from '../i18n/translations';

export default function Requests() {
  const { requests, projects, users, addRequest, updateRequest, authUser, language } = useStore();
  const t = translations[language].requests;
  const tp = translations[language].priority;

  const statusConfig = {
    discussion: { label: t.discussion, color: 'bg-blue-50 text-blue-700 border border-blue-200 dark:bg-blue-900/50 dark:text-blue-400 dark:border-blue-800' },
    clarification: { label: t.clarification, color: 'bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-900/50 dark:text-amber-400 dark:border-amber-800' },
    approval: { label: t.onApproval, color: 'bg-purple-50 text-purple-700 border border-purple-200 dark:bg-purple-900/50 dark:text-purple-400 dark:border-purple-800' },
    completed: { label: t.completedStatus, color: 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-900/50 dark:text-emerald-400 dark:border-emerald-800' },
  };

  const [selected, setSelected] = useState<typeof requests[0] | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newComment, setNewComment] = useState('');
  const [form, setForm] = useState({ title: '', description: '', projectId: '', assigneeId: '', priority: 'medium' });

  const handleCreate = async () => {
    if (!form.title) return;
    try {
      const result = await requestService.createRequest({
        title: form.title,
        description: form.description || undefined,
        project_id: form.projectId || undefined,
        assignee_id: form.assigneeId || undefined,
        priority: form.priority,
      });
      addRequest(adaptRequest(result));
    } catch {
      addRequest({
        id: 'r' + Date.now(), title: form.title, description: form.description,
        projectId: form.projectId || undefined, assigneeId: form.assigneeId || undefined,
        creatorId: authUser?.id || 'u1', status: 'discussion',
        priority: form.priority as TaskPriority, createdAt: new Date().toISOString().split('T')[0], comments: [],
      });
    }
    setShowCreate(false);
    setForm({ title: '', description: '', projectId: '', assigneeId: '', priority: 'medium' });
  };

  const handleAddComment = async () => {
    if (!selected || !newComment.trim()) return;
    let comment = { id: 'rc' + Date.now(), userId: authUser?.id || 'u1', text: newComment, createdAt: new Date().toISOString().split('T')[0] };
    try {
      const result = await requestService.addComment(selected.id, newComment);
      comment = { id: result.id, userId: result.user_id, text: result.content, createdAt: result.created_at };
    } catch { /* keep local fallback comment */ }
    const updated = { ...selected, comments: [...selected.comments, comment] };
    updateRequest(updated);
    setSelected(updated);
    setNewComment('');
  };

  const inputCls = "w-full bg-gray-100 border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-700 focus:outline-none focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200";
  const selectCls = inputCls;

  return (
    <Layout title={t.title} subtitle={t.subtitle}>
      <div className="flex items-center justify-between mb-6">
        <div className="flex gap-2 flex-wrap">
          {Object.entries(statusConfig).map(([k, v]) => (
            <span key={k} className={clsx('text-xs px-2 py-1 rounded-full', v.color)}>
              {v.label}: {requests.filter(r => r.status === k).length}
            </span>
          ))}
        </div>
        <Button variant="primary" icon={<Plus size={16} />} onClick={() => setShowCreate(true)}>{t.newRequest}</Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
        {requests.map(req => {
          const creator = users.find(u => u.id === req.creatorId);
          const project = projects.find(p => p.id === req.projectId);
          const cfg = statusConfig[req.status as keyof typeof statusConfig] || statusConfig.discussion;
          return (
            <Card key={req.id} hover onClick={() => setSelected(req)}>
              <div className="p-4">
                <div className="flex items-start justify-between gap-2 mb-2">
                  <p className="text-sm font-medium text-gray-900 dark:text-gray-200">{req.title}</p>
                  <span className={clsx('text-xs px-2 py-0.5 rounded-full flex-shrink-0', cfg.color)}>{cfg.label}</span>
                </div>
                <p className="text-xs text-gray-500 mb-3 line-clamp-2">{req.description}</p>
                {project && <p className="text-xs text-gray-500 mb-2">📁 {project.name}</p>}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {creator && (() => {
                      const name = creator.full_name || creator.name || 'User';
                      return <><Avatar name={name} size="xs" /><span className="text-xs text-gray-500">{name.split(' ')[0]}</span></>;
                    })()}
                  </div>
                  <div className="flex items-center gap-3 text-xs text-gray-500">
                    <span className="flex items-center gap-1"><MessageSquare size={10} /> {req.comments.length}</span>
                    <span className="flex items-center gap-1"><Clock size={10} /> {req.createdAt}</span>
                  </div>
                </div>
              </div>
            </Card>
          );
        })}
        {requests.length === 0 && (
          <div className="col-span-3 text-center py-20 text-gray-400">
            <MessageSquare size={40} className="mx-auto mb-3 opacity-30" />
            <p>{t.noRequests}</p>
          </div>
        )}
      </div>

      {/* Detail Modal */}
      {selected && (
        <Modal open={!!selected} onClose={() => setSelected(null)} title={selected.title} size="lg"
          footer={
            <div className="flex gap-2 w-full">
              <input value={newComment} onChange={e => setNewComment(e.target.value)} placeholder={t.commentPlaceholder}
                className="flex-1 bg-gray-100 border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700 focus:outline-none focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200"
                onKeyDown={e => e.key === 'Enter' && handleAddComment()} />
              <Button variant="primary" onClick={handleAddComment}>{t.send}</Button>
            </div>
          }>
          <div className="space-y-4">
            <div className="flex gap-2 flex-wrap">
              <span className={clsx('text-xs px-2 py-0.5 rounded-full', (statusConfig[selected.status as keyof typeof statusConfig] || statusConfig.discussion).color)}>
                {(statusConfig[selected.status as keyof typeof statusConfig] || statusConfig.discussion).label}
              </span>
              <Badge variant="default" size="sm">{tp[selected.priority] ?? selected.priority}</Badge>
            </div>
            {selected.description && (
              <p className="text-sm text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-700/30 p-3 rounded-lg">{selected.description}</p>
            )}
            <div className="flex gap-4 text-sm">
              <div>
                <p className="text-xs text-gray-500">{t.author}</p>
                {users.find(u => u.id === selected.creatorId) && (() => {
                  const user = users.find(u => u.id === selected.creatorId)!;
                  const name = user.full_name || user.name || 'User';
                  return (
                  <div className="flex items-center gap-1.5 mt-1">
                    <Avatar name={name} size="xs" />
                    <span className="text-gray-700 dark:text-gray-300">{name}</span>
                  </div>
                  );
                })()}
              </div>
              {selected.assigneeId && (
                <div>
                  <p className="text-xs text-gray-500">{t.responsible}</p>
                  {users.find(u => u.id === selected.assigneeId) && (() => {
                      const user = users.find(u => u.id === selected.assigneeId)!;
                      const name = user.full_name || user.name || 'User';
                      return (
                    <div className="flex items-center gap-1.5 mt-1">
                      <Avatar name={name} size="xs" />
                      <span className="text-gray-700 dark:text-gray-300">{name}</span>
                    </div>
                      );
                    })()}
                </div>
              )}
            </div>
            <div className="space-y-2">
              <p className="text-xs text-gray-500">{t.commentsLabel} ({selected.comments.length})</p>
              {selected.comments.map(c => {
                const u = users.find(u => u.id === c.userId);
                return (
                  <div key={c.id} className="flex gap-2 bg-gray-50 dark:bg-gray-700/30 p-3 rounded-lg">
                    {u && <Avatar name={u.full_name || u.name || 'User'} size="xs" />}
                    <div>
                      <p className="text-xs text-gray-400 mb-1">{u?.full_name || u?.name || 'Unknown'} · {c.createdAt}</p>
                      <p className="text-sm text-gray-700 dark:text-gray-300">{c.text}</p>
                    </div>
                  </div>
                );
              })}
              {selected.comments.length === 0 && <p className="text-xs text-gray-400 text-center py-2">{t.noComments}</p>}
            </div>
          </div>
        </Modal>
      )}

      {/* Create Modal */}
      <Modal open={showCreate} onClose={() => setShowCreate(false)} title={t.newRequest}
        footer={<div className="flex justify-end gap-3"><Button onClick={() => setShowCreate(false)}>{t.cancel}</Button><Button variant="primary" onClick={handleCreate}>{t.create}</Button></div>}>
        <div className="space-y-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1.5">{t.topicLabel}</label>
            <input value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} className={inputCls} />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1.5">{t.descriptionLabel}</label>
            <textarea value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} rows={3}
              className="w-full bg-gray-100 border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-700 focus:outline-none focus:border-blue-500 resize-none dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1.5">{t.projectLabel}</label>
              <select value={form.projectId} onChange={e => setForm({ ...form, projectId: e.target.value })} className={selectCls}>
                <option value="">{t.notSelected}</option>
                {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1.5">{t.responsible}</label>
              <select value={form.assigneeId} onChange={e => setForm({ ...form, assigneeId: e.target.value })} className={selectCls}>
                <option value="">{t.notAssigned}</option>
{users.map(u => <option key={u.id} value={u.id}>{u.full_name || u.name || 'User'}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1.5">{t.priorityLabel}</label>
              <select value={form.priority} onChange={e => setForm({ ...form, priority: e.target.value })} className={selectCls}>
                {Object.entries(tp).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
          </div>
        </div>
      </Modal>
    </Layout>
  );
}
