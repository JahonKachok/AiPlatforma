import { useState, useRef } from 'react';
import { Layout } from '../components/layout/Layout';
import { Card } from '../components/ui/Card';
import { Badge, getTaskStatusBadge, getPriorityBadge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { Avatar } from '../components/ui/Avatar';
import { useStore } from '../store/useStore';
import {
  Plus, MessageSquare, Paperclip, AlertTriangle, LayoutGrid, List,
  Calendar, ChevronLeft, ChevronRight, Pencil, Trash2, X, Check,
} from 'lucide-react';
import type { Task, TaskStatus } from '../types';
import { clsx } from 'clsx';
import { translations } from '../i18n/translations';

const selectCls = "bg-gray-100 border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700 focus:outline-none focus:border-blue-500 dark:bg-gray-800 dark:border-gray-700 dark:text-gray-300";
const fieldCls = "w-full bg-gray-100 border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-700 focus:outline-none focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200";

const COLUMNS: { status: TaskStatus; color: string }[] = [
  { status: 'new',        color: 'border-blue-400 dark:border-blue-700' },
  { status: 'in_progress',color: 'border-purple-400 dark:border-purple-700' },
  { status: 'review',     color: 'border-amber-400 dark:border-amber-700' },
  { status: 'revision',   color: 'border-red-400 dark:border-red-700' },
  { status: 'approved',   color: 'border-emerald-400 dark:border-emerald-700' },
  { status: 'completed',  color: 'border-gray-400 dark:border-gray-700' },
];

const emptyForm = { title: '', description: '', projectId: '', assigneeId: '', deadline: '', priority: 'medium', status: 'new' as TaskStatus };

// ─── TaskCard ────────────────────────────────────────────────────────────────
function TaskCard({
  task, language, onClick, onDragStart, onDragEnd, isDragging,
}: {
  task: Task; language: string;
  onClick: () => void;
  onDragStart: () => void; onDragEnd: () => void; isDragging: boolean;
}) {
  const { users, projects } = useStore();
  const t = translations[language as keyof typeof translations];
  const assignee = users.find(u => u.id === task.assigneeId);
  const project = projects.find(p => p.id === task.projectId);
  const isOverdue = task.status !== 'completed' && task.deadline && new Date(task.deadline) < new Date();

  return (
    <div
      draggable
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      onClick={onClick}
      className={clsx(
        'bg-white border rounded-xl p-3.5 cursor-grab active:cursor-grabbing hover:shadow-sm transition-all select-none',
        'dark:bg-gray-800 dark:border-gray-700 dark:hover:border-gray-600',
        isDragging ? 'opacity-40 scale-95 border-blue-400 dark:border-blue-600' : 'border-gray-200 hover:border-gray-300',
      )}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <p className="text-sm text-gray-800 dark:text-gray-200 font-medium leading-tight">{task.title}</p>
        <Badge variant={getPriorityBadge(task.priority)} size="sm">{t.priority[task.priority] ?? task.priority}</Badge>
      </div>
      {project && <p className="text-xs text-gray-400 mb-2 truncate">{project.name}</p>}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {assignee && (
            <><Avatar name={assignee.name} size="xs" />
              <span className="text-xs text-gray-500 truncate max-w-20">{assignee.name.split(' ')[0]}</span></>
          )}
        </div>
        <div className="flex items-center gap-2 text-xs">
          {task.comments.length > 0 && <span className="text-gray-400 flex items-center gap-0.5"><MessageSquare size={10} />{task.comments.length}</span>}
          {task.attachments.length > 0 && <span className="text-gray-400 flex items-center gap-0.5"><Paperclip size={10} />{task.attachments.length}</span>}
          {task.deadline && (
            <span className={clsx('flex items-center gap-0.5', isOverdue ? 'text-red-500 dark:text-red-400' : 'text-gray-400')}>
              {isOverdue && <AlertTriangle size={10} />}{task.deadline}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── CalendarView ─────────────────────────────────────────────────────────────
function CalendarView({ tasks, language, onTaskClick }: { tasks: Task[]; language: string; onTaskClick: (t: Task) => void }) {
  const [cur, setCur] = useState(() => { const d = new Date(); return { year: d.getFullYear(), month: d.getMonth() }; });
  const t = translations[language as keyof typeof translations];

  const daysInMonth = new Date(cur.year, cur.month + 1, 0).getDate();
  const firstDay = (new Date(cur.year, cur.month, 1).getDay() + 6) % 7; // Mon-start

  const monthNames = language === 'uz'
    ? ['Yanvar','Fevral','Mart','Aprel','May','Iyun','Iyul','Avgust','Sentabr','Oktabr','Noyabr','Dekabr']
    : language === 'en'
    ? ['January','February','March','April','May','June','July','August','September','October','November','December']
    : ['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'];

  const dayNames = language === 'uz'
    ? ['Du','Se','Ch','Pa','Ju','Sh','Ya']
    : language === 'en'
    ? ['Mo','Tu','We','Th','Fr','Sa','Su']
    : ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'];

  const prev = () => setCur(c => c.month === 0 ? { year: c.year - 1, month: 11 } : { ...c, month: c.month - 1 });
  const next = () => setCur(c => c.month === 11 ? { year: c.year + 1, month: 0 } : { ...c, month: c.month + 1 });

  const today = new Date();
  const pad = (n: number) => String(n).padStart(2, '0');

  const cells: (number | null)[] = [...Array(firstDay).fill(null), ...Array.from({ length: daysInMonth }, (_, i) => i + 1)];
  while (cells.length % 7 !== 0) cells.push(null);

  const getTasksForDay = (day: number) => {
    const key = `${cur.year}-${pad(cur.month + 1)}-${pad(day)}`;
    return tasks.filter(task => task.deadline && task.deadline.startsWith(key));
  };

  const statusDot: Record<TaskStatus, string> = {
    new: 'bg-blue-400', in_progress: 'bg-purple-400', review: 'bg-amber-400',
    revision: 'bg-red-400', approved: 'bg-emerald-400', completed: 'bg-gray-400',
  };

  return (
    <div className="bg-white border border-gray-200 rounded-2xl overflow-hidden dark:bg-gray-800 dark:border-gray-700">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <button onClick={prev} className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
          <ChevronLeft size={16} className="text-gray-500 dark:text-gray-400" />
        </button>
        <h2 className="font-semibold text-gray-900 dark:text-white">{monthNames[cur.month]} {cur.year}</h2>
        <button onClick={next} className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
          <ChevronRight size={16} className="text-gray-500 dark:text-gray-400" />
        </button>
      </div>

      {/* Day names */}
      <div className="grid grid-cols-7 border-b border-gray-200 dark:border-gray-700">
        {dayNames.map(d => (
          <div key={d} className="py-2 text-center text-xs font-medium text-gray-500 dark:text-gray-400">{d}</div>
        ))}
      </div>

      {/* Cells */}
      <div className="grid grid-cols-7">
        {cells.map((day, i) => {
          if (!day) return <div key={`empty-${i}`} className="h-24 border-b border-r border-gray-100 dark:border-gray-700/50 last:border-r-0" />;
          const dayTasks = getTasksForDay(day);
          const isToday = day === today.getDate() && cur.month === today.getMonth() && cur.year === today.getFullYear();
          const isWeekend = (i % 7) >= 5;
          return (
            <div key={day}
              className={clsx(
                'h-24 p-1.5 border-b border-r border-gray-100 dark:border-gray-700/50 last:border-r-0 overflow-hidden',
                isWeekend && 'bg-gray-50/50 dark:bg-gray-700/20',
              )}>
              <div className={clsx(
                'text-xs font-medium w-6 h-6 flex items-center justify-center rounded-full mb-1',
                isToday ? 'bg-blue-600 text-white' : 'text-gray-600 dark:text-gray-400',
              )}>{day}</div>
              <div className="space-y-0.5">
                {dayTasks.slice(0, 3).map(task => (
                  <button key={task.id} onClick={() => onTaskClick(task)}
                    className="w-full text-left flex items-center gap-1 hover:bg-gray-100 dark:hover:bg-gray-600 rounded px-1 py-0.5 transition-colors">
                    <span className={clsx('w-1.5 h-1.5 rounded-full flex-shrink-0', statusDot[task.status])} />
                    <span className="text-xs text-gray-600 dark:text-gray-300 truncate">{task.title}</span>
                  </button>
                ))}
                {dayTasks.length > 3 && (
                  <span className="text-xs text-gray-400 px-1">+{dayTasks.length - 3}</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Main ─────────────────────────────────────────────────────────────────────
export default function Tasks() {
  const { tasks, projects, users, addTask, updateTask, deleteTask, authUser, language } = useStore();
  const t = translations[language];
  const tt = t.tasks;
  const tc = t.common;

  const [view, setView] = useState<'kanban' | 'list' | 'calendar'>('kanban');
  const [selected, setSelected] = useState<Task | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [editForm, setEditForm] = useState<typeof emptyForm>(emptyForm);
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({ ...emptyForm });
  const [filterProject, setFilterProject] = useState('all');
  const [filterAssignee, setFilterAssignee] = useState('all');
  const [draggedId, setDraggedId] = useState<string | null>(null);
  const [dropTarget, setDropTarget] = useState<TaskStatus | null>(null);

  const filtered = tasks.filter(task => {
    const mp = filterProject === 'all' || task.projectId === filterProject;
    const ma = filterAssignee === 'all' || task.assigneeId === filterAssignee;
    return mp && ma;
  });

  // ── Drag handlers ──
  const handleDragStart = (taskId: string) => { setDraggedId(taskId); };
  const handleDragEnd = () => { setDraggedId(null); setDropTarget(null); };
  const handleDragOver = (e: React.DragEvent, status: TaskStatus) => {
    e.preventDefault();
    setDropTarget(status);
  };
  const handleDrop = (e: React.DragEvent, status: TaskStatus) => {
    e.preventDefault();
    const id = draggedId;
    if (!id) return;
    const task = tasks.find(t => t.id === id);
    if (task && task.status !== status) updateTask({ ...task, status });
    setDraggedId(null);
    setDropTarget(null);
  };

  // ── Open task detail ──
  const openTask = (task: Task) => {
    setSelected(task);
    setEditForm({
      title: task.title, description: task.description, projectId: task.projectId,
      assigneeId: task.assigneeId, deadline: task.deadline, priority: task.priority,
      status: task.status,
    });
    setEditMode(false);
  };

  const handleSaveEdit = () => {
    if (!selected || !editForm.title) return;
    const updated = { ...selected, ...editForm };
    updateTask(updated);
    setSelected(updated);
    setEditMode(false);
  };

  const handleDelete = () => {
    if (!selected) return;
    deleteTask(selected.id);
    setSelected(null);
  };

  // ── Create ──
  const handleCreate = () => {
    if (!createForm.title) return;
    addTask({
      id: 't' + Date.now(), title: createForm.title, description: createForm.description,
      projectId: createForm.projectId, assigneeId: createForm.assigneeId,
      creatorId: authUser?.id || '', status: createForm.status,
      priority: createForm.priority as Task['priority'],
      deadline: createForm.deadline,
      createdAt: new Date().toISOString().split('T')[0],
      updatedAt: new Date().toISOString().split('T')[0],
      attachments: [], comments: [],
    });
    setShowCreate(false);
    setCreateForm({ ...emptyForm });
  };

  const viewBtnCls = (active: boolean) =>
    clsx('p-2 rounded-lg transition-colors', active ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-500 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700');

  return (
    <Layout title={tt.title} subtitle={`${tasks.length} ${tt.inSystem}`}>
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <select value={filterProject} onChange={e => setFilterProject(e.target.value)} className={selectCls}>
          <option value="all">{tt.allProjects}</option>
          {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <select value={filterAssignee} onChange={e => setFilterAssignee(e.target.value)} className={selectCls}>
          <option value="all">{tt.allAssignees}</option>
          {users.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}
        </select>
        <div className="flex gap-1 ml-auto">
          <button onClick={() => setView('kanban')} className={viewBtnCls(view === 'kanban')} title="Kanban"><LayoutGrid size={16} /></button>
          <button onClick={() => setView('list')} className={viewBtnCls(view === 'list')} title="List"><List size={16} /></button>
          <button onClick={() => setView('calendar')} className={viewBtnCls(view === 'calendar')} title="Calendar"><Calendar size={16} /></button>
        </div>
        <Button variant="primary" icon={<Plus size={16} />} onClick={() => setShowCreate(true)}>{tt.newTask}</Button>
      </div>

      {/* ── KANBAN ── */}
      {view === 'kanban' && (
        <div className="flex gap-4 overflow-x-auto pb-4">
          {COLUMNS.map(col => {
            const colTasks = filtered.filter(task => task.status === col.status);
            const isOver = dropTarget === col.status;
            return (
              <div key={col.status} className="flex-shrink-0 w-64"
                onDragOver={e => handleDragOver(e, col.status)}
                onDragLeave={() => setDropTarget(null)}
                onDrop={e => handleDrop(e, col.status)}>
                <div className={clsx('flex items-center justify-between mb-3 px-1 pb-2 border-b-2', col.color)}>
                  <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">{t.taskStatus[col.status]}</span>
                  <span className="text-xs bg-gray-100 text-gray-500 rounded-full px-2 py-0.5 dark:bg-gray-700 dark:text-gray-400">{colTasks.length}</span>
                </div>
                <div className={clsx('space-y-2 min-h-16 rounded-xl p-1 transition-colors', isOver && draggedId ? 'bg-blue-50 dark:bg-blue-900/20' : '')}>
                  {colTasks.map(task => (
                    <TaskCard key={task.id} task={task} language={language}
                      onClick={() => openTask(task)}
                      onDragStart={() => handleDragStart(task.id)}
                      onDragEnd={handleDragEnd}
                      isDragging={draggedId === task.id}
                    />
                  ))}
                  {colTasks.length === 0 && !isOver && (
                    <div className="text-center py-8 text-gray-400 text-xs">{tt.noTasks}</div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ── LIST ── */}
      {view === 'list' && (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  {[tt.tableTask, tt.tableProject, tt.tableAssignee, tt.tableStatus, tt.tablePriority, tt.tableDeadline].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs text-gray-500 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map(task => {
                  const assignee = users.find(u => u.id === task.assigneeId);
                  const project = projects.find(p => p.id === task.projectId);
                  const isOverdue = task.status !== 'completed' && task.deadline && new Date(task.deadline) < new Date();
                  return (
                    <tr key={task.id} onClick={() => openTask(task)}
                      className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer transition-colors dark:border-gray-800 dark:hover:bg-gray-800/50">
                      <td className="px-4 py-3"><p className="text-sm text-gray-800 dark:text-gray-200 max-w-xs truncate">{task.title}</p></td>
                      <td className="px-4 py-3 text-xs text-gray-500">{project?.name}</td>
                      <td className="px-4 py-3">
                        {assignee && <div className="flex items-center gap-2"><Avatar name={assignee.name} size="xs" /><span className="text-xs text-gray-500">{assignee.name}</span></div>}
                      </td>
                      <td className="px-4 py-3"><Badge variant={getTaskStatusBadge(task.status)} size="sm">{t.taskStatus[task.status] ?? task.status}</Badge></td>
                      <td className="px-4 py-3"><Badge variant={getPriorityBadge(task.priority)} size="sm">{t.priority[task.priority] ?? task.priority}</Badge></td>
                      <td className={clsx('px-4 py-3 text-xs', isOverdue ? 'text-red-500 dark:text-red-400' : 'text-gray-500')}>
                        {isOverdue && <AlertTriangle size={10} className="inline mr-1" />}{task.deadline}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* ── CALENDAR ── */}
      {view === 'calendar' && (
        <CalendarView tasks={filtered} language={language} onTaskClick={openTask} />
      )}

      {/* ── TASK DETAIL / EDIT MODAL ── */}
      {selected && (
        <Modal open={!!selected} onClose={() => { setSelected(null); setEditMode(false); }}
          title={editMode ? tc.edit : selected.title} size="lg"
          footer={
            <div className="flex items-center justify-between gap-2">
              {editMode ? (
                <>
                  <button onClick={() => setEditMode(false)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors">
                    <X size={14} /> {tc.cancel}
                  </button>
                  <Button variant="primary" icon={<Check size={14} />} onClick={handleSaveEdit}>{tc.save}</Button>
                </>
              ) : (
                <>
                  <div className="flex items-center gap-2">
                    <button onClick={() => setEditMode(true)}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600">
                      <Pencil size={13} /> {tc.edit}
                    </button>
                    <button onClick={handleDelete}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg bg-red-50 text-red-600 hover:bg-red-100 transition-colors dark:bg-red-900/30 dark:text-red-400 dark:hover:bg-red-900/50">
                      <Trash2 size={13} /> {tc.delete}
                    </button>
                  </div>
                  <div className="flex gap-1.5 flex-wrap">
                    {COLUMNS.map(col => (
                      <button key={col.status}
                        onClick={() => { updateTask({ ...selected, status: col.status }); setSelected({ ...selected, status: col.status }); }}
                        className={clsx('px-2.5 py-1 text-xs rounded-lg transition-colors',
                          selected.status === col.status
                            ? 'bg-blue-600 text-white'
                            : 'bg-gray-100 text-gray-500 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-400 dark:hover:bg-gray-600')}>
                        {t.taskStatus[col.status]}
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>
          }>
          {editMode ? (
            <div className="space-y-4">
              <div>
                <label className="block text-xs text-gray-500 mb-1.5">{tt.nameLabel}</label>
                <input value={editForm.title} onChange={e => setEditForm({ ...editForm, title: e.target.value })} className={fieldCls} />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1.5">{tt.descriptionLabel}</label>
                <textarea value={editForm.description} onChange={e => setEditForm({ ...editForm, description: e.target.value })} rows={3} className={clsx(fieldCls, 'resize-none')} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-gray-500 mb-1.5">{tt.projectLabel}</label>
                  <select value={editForm.projectId} onChange={e => setEditForm({ ...editForm, projectId: e.target.value })} className={fieldCls}>
                    <option value="">{tt.notSelected}</option>
                    {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1.5">{tt.assigneeLabel}</label>
                  <select value={editForm.assigneeId} onChange={e => setEditForm({ ...editForm, assigneeId: e.target.value })} className={fieldCls}>
                    <option value="">{tt.notAssigned}</option>
                    {users.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1.5">{tt.deadlineLabel}</label>
                  <input type="date" value={editForm.deadline} onChange={e => setEditForm({ ...editForm, deadline: e.target.value })} className={fieldCls} />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1.5">{tt.priorityLabel}</label>
                  <select value={editForm.priority} onChange={e => setEditForm({ ...editForm, priority: e.target.value })} className={fieldCls}>
                    {Object.entries(t.priority).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex gap-2">
                <Badge variant={getTaskStatusBadge(selected.status)}>{t.taskStatus[selected.status]}</Badge>
                <Badge variant={getPriorityBadge(selected.priority)}>{t.priority[selected.priority]}</Badge>
              </div>
              {selected.description && (
                <p className="text-sm text-gray-500 bg-gray-50 dark:bg-gray-700/30 p-3 rounded-lg">{selected.description}</p>
              )}
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="bg-gray-50 dark:bg-gray-700/30 p-3 rounded-lg">
                  <p className="text-xs text-gray-500 mb-1">{tt.assigneeLabel}</p>
                  {users.find(u => u.id === selected.assigneeId) ? (
                    <div className="flex items-center gap-2">
                      <Avatar name={users.find(u => u.id === selected.assigneeId)!.name} size="xs" />
                      <span className="text-gray-700 dark:text-gray-200">{users.find(u => u.id === selected.assigneeId)!.name}</span>
                    </div>
                  ) : <span className="text-gray-400">—</span>}
                </div>
                <div className="bg-gray-50 dark:bg-gray-700/30 p-3 rounded-lg">
                  <p className="text-xs text-gray-500 mb-1">{tt.deadlineLabel}</p>
                  <p className="text-gray-700 dark:text-gray-200">{selected.deadline || '—'}</p>
                </div>
              </div>
              {selected.comments.length > 0 && (
                <div>
                  <p className="text-xs text-gray-500 mb-2">{t.requests.commentsLabel}</p>
                  <div className="space-y-2">
                    {selected.comments.map(c => {
                      const u = users.find(u => u.id === c.userId);
                      return (
                        <div key={c.id} className="flex gap-2 bg-gray-50 dark:bg-gray-700/30 p-3 rounded-lg">
                          {u && <Avatar name={u.name} size="xs" />}
                          <div>
                            <p className="text-xs text-gray-400 mb-1">{u?.name} · {c.createdAt}</p>
                            <p className="text-sm text-gray-700 dark:text-gray-300">{c.text}</p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}
        </Modal>
      )}

      {/* ── CREATE MODAL ── */}
      <Modal open={showCreate} onClose={() => setShowCreate(false)} title={tt.newTask} size="lg"
        footer={
          <div className="flex justify-end gap-3">
            <Button onClick={() => setShowCreate(false)}>{tt.cancel}</Button>
            <Button variant="primary" onClick={handleCreate}>{tt.create}</Button>
          </div>
        }>
        <div className="space-y-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1.5">{tt.nameLabel}</label>
            <input value={createForm.title} onChange={e => setCreateForm({ ...createForm, title: e.target.value })} className={fieldCls} autoFocus />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1.5">{tt.descriptionLabel}</label>
            <textarea value={createForm.description} onChange={e => setCreateForm({ ...createForm, description: e.target.value })} rows={3} className={clsx(fieldCls, 'resize-none')} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1.5">{tt.projectLabel}</label>
              <select value={createForm.projectId} onChange={e => setCreateForm({ ...createForm, projectId: e.target.value })} className={fieldCls}>
                <option value="">{tt.notSelected}</option>
                {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1.5">{tt.assigneeLabel}</label>
              <select value={createForm.assigneeId} onChange={e => setCreateForm({ ...createForm, assigneeId: e.target.value })} className={fieldCls}>
                <option value="">{tt.notAssigned}</option>
                {users.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1.5">{tt.deadlineLabel}</label>
              <input type="date" value={createForm.deadline} onChange={e => setCreateForm({ ...createForm, deadline: e.target.value })} className={fieldCls} />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1.5">{tt.priorityLabel}</label>
              <select value={createForm.priority} onChange={e => setCreateForm({ ...createForm, priority: e.target.value })} className={fieldCls}>
                {Object.entries(t.priority).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
          </div>
        </div>
      </Modal>
    </Layout>
  );
}
