import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Layout } from '../components/layout/Layout';
import { Card, CardHeader, CardContent } from '../components/ui/Card';
import { Badge, getProjectStatusBadge, getPriorityBadge, getTaskStatusBadge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { Avatar } from '../components/ui/Avatar';
import { useStore } from '../store/useStore';
import {
  ArrowLeft, MapPin, Clock, Users, Layers, CheckSquare, FileText, AlertTriangle,
  Pencil, Trash2, Plus, TrendingUp, TrendingDown, DollarSign, CreditCard,
} from 'lucide-react';
import { clsx } from 'clsx';
import { translations } from '../i18n/translations';
import type { ProjectStatus, ProjectStage, Project } from '../types';
import { projectService } from '../services/projectService';
import { adaptProject } from '../services/adapters';
import { financeService } from '../services/financeService';

const inputCls = "w-full bg-gray-100 border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-700 focus:outline-none focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200";

type RecordType = 'income' | 'expense' | 'advance' | 'payment';
type RecordStatus = 'pending' | 'confirmed' | 'cancelled';

interface FinRecord {
  id: string;
  type: RecordType;
  amount: number;
  description?: string;
  category?: string;
  date: string;
  status: RecordStatus;
}

const emptyForm = {
  type: 'income' as RecordType,
  amount: '',
  description: '',
  category: '',
  date: new Date().toISOString().slice(0, 10),
  status: 'pending' as RecordStatus,
};

export default function ProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { projects, tasks, documents, users, language, updateProject, deleteProject } = useStore();
  const t = translations[language].projectDetail;
  const pt = translations[language].projects;
  const tStatus = translations[language].projectStatus;
  const tStage = translations[language].projectStage;
  const tPriority = translations[language].priority;
  const tTaskStatus = translations[language].taskStatus;
  const tc = translations[language].common;

  const storeProject = projects.find(p => p.id === id);
  const [detail, setDetail] = useState<Project | null>(null);
  const project = detail ?? storeProject;

  const [showEdit, setShowEdit] = useState(false);
  const [showConfirmDelete, setShowConfirmDelete] = useState(false);
  const [editForm, setEditForm] = useState({
    name: project?.name ?? '',
    client: project?.client ?? '',
    address: project?.address ?? '',
    deadline: project?.deadline ?? '',
    startDate: project?.startDate ?? '',
    stage: (project?.stage ?? 'concept') as ProjectStage,
    status: (project?.status ?? 'active') as ProjectStatus,
    priority: project?.priority ?? 'medium',
    gipId: project?.gipId ?? '',
    budget: String(project?.budget ?? 0),
    description: project?.description ?? '',
  });

  // Finance state
  const [records, setRecords] = useState<FinRecord[]>([]);
  const [showAddRecord, setShowAddRecord] = useState(false);
  const [addRecordForm, setAddRecordForm] = useState(emptyForm);
  const [savingRecord, setSavingRecord] = useState(false);
  const [deletingRecordId, setDeletingRecordId] = useState<string | null>(null);
  const [confirmDeleteRecord, setConfirmDeleteRecord] = useState<string | null>(null);

  useEffect(() => {
    setDetail(null);
    if (!id) return;
    let cancelled = false;
    projectService.getProject(id)
      .then(result => { if (!cancelled) setDetail(adaptProject(result)); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [id]);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    financeService.getRecords({ project_id: id })
      .then((data: FinRecord[]) => { if (!cancelled) setRecords(data); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [id]);

  if (!project) return (
    <Layout title={t.notFound}>
      <Button icon={<ArrowLeft size={16} />} onClick={() => navigate('/projects')}>{t.backBtn}</Button>
    </Layout>
  );

  const gip = users.find(u => u.id === project.gipId);
  const projectTasks = tasks.filter(task => task.projectId === id);
  const projectDocs = documents.filter(d => d.projectId === id);
  const progress = project.budget > 0 ? Math.round((project.paid / project.budget) * 100) : 0;
  const overdue = projectTasks.filter(task => task.status !== 'completed' && new Date(task.deadline) < new Date());

  // Computed finance aggregates from records
  const totalIncome = records
    .filter(r => r.type === 'income' && r.status === 'confirmed')
    .reduce((s, r) => s + r.amount, 0);
  const totalExpense = records
    .filter(r => r.type === 'expense' && r.status === 'confirmed')
    .reduce((s, r) => s + r.amount, 0);
  const totalAdvance = records
    .filter(r => r.type === 'advance')
    .reduce((s, r) => s + r.amount, 0);
  const pendingTotal = records
    .filter(r => r.status === 'pending')
    .reduce((s, r) => s + r.amount, 0);

  const fmt = (n: number) => (n / 1_000_000).toFixed(1);

  const typeConfig: Record<RecordType, { label: string; color: string; bg: string; icon: typeof TrendingUp }> = {
    income:  { label: t.income,  color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-100 dark:bg-emerald-900/30', icon: TrendingUp },
    expense: { label: t.expense, color: 'text-red-600 dark:text-red-400',         bg: 'bg-red-100 dark:bg-red-900/30',         icon: TrendingDown },
    advance: { label: t.advance, color: 'text-blue-600 dark:text-blue-400',       bg: 'bg-blue-100 dark:bg-blue-900/30',       icon: DollarSign },
    payment: { label: t.payment, color: 'text-purple-600 dark:text-purple-400',   bg: 'bg-purple-100 dark:bg-purple-900/30',   icon: CreditCard },
  };

  const statusConfig: Record<RecordStatus, { label: string; variant: 'success' | 'warning' | 'danger' }> = {
    confirmed: { label: t.confirmed,       variant: 'success' },
    pending:   { label: t.pendingRecord,   variant: 'warning' },
    cancelled: { label: t.cancelledRecord, variant: 'danger' },
  };

  const openEdit = () => {
    setEditForm({
      name: project.name,
      client: project.client,
      address: project.address,
      deadline: project.deadline,
      startDate: project.startDate,
      stage: project.stage,
      status: project.status,
      priority: project.priority,
      gipId: project.gipId,
      budget: String(project.budget),
      description: project.description ?? '',
    });
    setShowEdit(true);
  };

  const handleSave = async () => {
    const updated: Project = {
      ...project,
      name: editForm.name,
      client: editForm.client,
      address: editForm.address,
      deadline: editForm.deadline,
      startDate: editForm.startDate,
      stage: editForm.stage,
      status: editForm.status,
      priority: editForm.priority as 'low' | 'medium' | 'high' | 'critical',
      gipId: editForm.gipId,
      budget: parseFloat(editForm.budget) || 0,
      description: editForm.description,
    };
    try {
      const result = await projectService.updateProject(project.id, {
        name: editForm.name,
        client_name: editForm.client,
        address: editForm.address || undefined,
        deadline: editForm.deadline || undefined,
        start_date: editForm.startDate || undefined,
        stage: editForm.stage,
        status: editForm.status === 'paused' ? 'on_hold' : editForm.status === 'planning' ? 'active' : editForm.status,
        budget: parseFloat(editForm.budget) || 0,
        description: editForm.description || undefined,
      });
      const adapted = adaptProject(result);
      updateProject(adapted);
      setDetail(adapted);
    } catch {
      updateProject(updated);
      setDetail(updated);
    }
    setShowEdit(false);
  };

  const handleDelete = async () => {
    try {
      await projectService.deleteProject(project.id);
    } catch {}
    deleteProject(project.id);
    navigate('/projects');
  };

  const handleAddRecord = async () => {
    if (!id || !addRecordForm.amount) return;
    setSavingRecord(true);
    try {
      const record = await financeService.createRecord({
        project_id: id,
        type: addRecordForm.type,
        amount: parseFloat(addRecordForm.amount),
        description: addRecordForm.description || undefined,
        category: addRecordForm.category || undefined,
        date: addRecordForm.date,
        status: addRecordForm.status,
      });
      setRecords(prev => [record, ...prev]);
      setShowAddRecord(false);
      setAddRecordForm(emptyForm);
    } catch {}
    setSavingRecord(false);
  };

  const handleDeleteRecord = async (recordId: string) => {
    setDeletingRecordId(recordId);
    try {
      await financeService.deleteRecord(recordId);
      setRecords(prev => prev.filter(r => r.id !== recordId));
    } catch {}
    setDeletingRecordId(null);
    setConfirmDeleteRecord(null);
  };

  const stages: ProjectStage[] = ['concept', 'preliminary', 'working_docs', 'expertise', 'construction'];
  const statuses: ProjectStatus[] = ['active', 'planning', 'paused', 'completed', 'cancelled'];
  const gipUsers = users.filter(u => u.role === 'gip' || u.role === 'manager');

  return (
    <Layout title={project.name} subtitle={project.client}>
      <div className="flex items-center gap-3 mb-6">
        <Button variant="ghost" icon={<ArrowLeft size={16} />} onClick={() => navigate('/projects')}>{t.backBtn}</Button>
        <Badge variant={getProjectStatusBadge(project.status)} size="md">{tStatus[project.status] ?? project.status}</Badge>
        <Badge variant={getPriorityBadge(project.priority)} size="md">{tPriority[project.priority] ?? project.priority}</Badge>
        <div className="ml-auto flex gap-2">
          <Button size="sm" icon={<Pencil size={14} />} onClick={openEdit}>{tc.edit}</Button>
          <Button size="sm" variant="danger" icon={<Trash2 size={14} />} onClick={() => setShowConfirmDelete(true)}>{tc.delete}</Button>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Left column */}
        <div className="xl:col-span-2 space-y-6">
          <Card>
            <CardHeader><span className="font-semibold text-gray-900 dark:text-white">{t.projectInfo}</span></CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                {[
                  { icon: MapPin, label: t.address, value: project.address },
                  { icon: Layers, label: t.stage, value: tStage[project.stage] ?? project.stage },
                  { icon: Clock, label: t.deadline, value: project.deadline },
                  { icon: Clock, label: t.startDate, value: project.startDate },
                ].map(({ icon: Icon, label, value }) => (
                  <div key={label} className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-700/30 rounded-lg">
                    <Icon size={16} className="text-gray-400 flex-shrink-0" />
                    <div>
                      <p className="text-xs text-gray-500">{label}</p>
                      <p className="text-sm text-gray-700 dark:text-gray-200">{value || '—'}</p>
                    </div>
                  </div>
                ))}
              </div>
              {project.description && (
                <p className="text-sm text-gray-500 mt-4 p-3 bg-gray-50 dark:bg-gray-700/20 rounded-lg">{project.description}</p>
              )}
            </CardContent>
          </Card>

          {project.objects.length > 0 && (
            <Card>
              <CardHeader><span className="font-semibold text-gray-900 dark:text-white">{t.objects} ({project.objects.length})</span></CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {project.objects.map(obj => {
                    const objGip = users.find(u => u.id === obj.gipId);
                    return (
                      <div key={obj.id} className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-700/30 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700/50 transition-colors">
                        <div className="w-8 h-8 bg-amber-50 dark:bg-amber-900/50 border border-amber-200 dark:border-amber-700 rounded-lg flex items-center justify-center text-xs font-bold text-amber-600 dark:text-amber-400">🏢</div>
                        <div className="flex-1">
                          <p className="text-sm font-medium text-gray-700 dark:text-gray-200">{obj.name}</p>
                          {obj.address && <p className="text-xs text-gray-500 mt-0.5">{obj.address}</p>}
                        </div>
                        {objGip && (
                          <div className="flex items-center gap-2">
                            <Avatar name={objGip.name} size="xs" />
                            <span className="text-xs text-gray-500 hidden md:inline">{objGip.name}</span>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          )}

          {project.sections.length > 0 && (
            <Card>
              <CardHeader><span className="font-semibold text-gray-900 dark:text-white">{t.sections} ({project.sections.length})</span></CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {project.sections.map(sec => {
                    const secGip = users.find(u => u.id === sec.gipId);
                    return (
                      <div key={sec.id} className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-700/30 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700/50 transition-colors">
                        <div className="w-8 h-8 bg-blue-50 dark:bg-blue-900/50 border border-blue-200 dark:border-blue-700 rounded-lg flex items-center justify-center text-xs font-bold text-blue-600 dark:text-blue-400">{sec.code}</div>
                        <div className="flex-1">
                          <p className="text-sm text-gray-700 dark:text-gray-200">{sec.name}</p>
                          {sec.deadline && <p className="text-xs text-gray-500">до {sec.deadline}</p>}
                        </div>
                        {secGip && (
                          <div className="flex items-center gap-2">
                            <Avatar name={secGip.name} size="xs" />
                            <span className="text-xs text-gray-500 hidden md:inline">{secGip.name}</span>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <span className="font-semibold text-gray-900 dark:text-white">{t.tasks} ({projectTasks.length})</span>
                <Button size="sm" onClick={() => navigate('/tasks')}>{t.openAll}</Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {projectTasks.slice(0, 6).map(task => {
                  const assignee = users.find(u => u.id === task.assigneeId);
                  const isOverdue = task.status !== 'completed' && new Date(task.deadline) < new Date();
                  return (
                    <div key={task.id} className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-700/30 rounded-lg">
                      <CheckSquare size={14} className="text-gray-400 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-gray-700 dark:text-gray-200 truncate">{task.title}</p>
                        <div className="flex items-center gap-2 mt-0.5">
                          {assignee && <span className="text-xs text-gray-500">{assignee.name}</span>}
                          <span className={`text-xs flex items-center gap-1 ${isOverdue ? 'text-red-500 dark:text-red-400' : 'text-gray-400'}`}>
                            {isOverdue && <AlertTriangle size={10} />} {task.deadline}
                          </span>
                        </div>
                      </div>
                      <Badge variant={getTaskStatusBadge(task.status)} size="sm">{tTaskStatus[task.status] ?? task.status}</Badge>
                    </div>
                  );
                })}
                {projectTasks.length === 0 && <p className="text-sm text-gray-400 text-center py-4">{t.noTasks}</p>}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right sidebar */}
        <div className="space-y-6">
          {/* Enhanced Finance Card */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <span className="font-semibold text-gray-900 dark:text-white">{t.finance}</span>
                <Button size="sm" icon={<Plus size={12} />} onClick={() => setShowAddRecord(true)}>{t.addRecord}</Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Budget progress */}
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-500">{t.budget}</span>
                  <span className="text-gray-900 dark:text-white font-medium">{fmt(project.budget)} mln</span>
                </div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-500">{t.paid}</span>
                  <span className="text-emerald-600 dark:text-emerald-400 font-medium">{fmt(project.paid)} mln</span>
                </div>
                <div className="flex justify-between text-sm mb-3">
                  <span className="text-gray-500">{t.remainder}</span>
                  <span className="text-amber-600 dark:text-amber-400 font-medium">{fmt(project.budget - project.paid)} mln</span>
                </div>
                <div className="h-2.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${Math.min(progress, 100)}%`,
                      background: progress >= 100 ? '#10b981' : progress >= 70 ? '#f59e0b' : '#3b82f6',
                    }}
                  />
                </div>
                <p className="text-xs text-gray-400 text-right mt-1">{progress}%</p>
              </div>

              {/* Records breakdown */}
              {records.length > 0 && (
                <div className="pt-3 border-t border-gray-100 dark:border-gray-700 space-y-2.5">
                  {[
                    { label: t.income,  value: totalIncome,  color: 'text-emerald-600 dark:text-emerald-400', icon: TrendingUp  },
                    { label: t.expense, value: totalExpense, color: 'text-red-600 dark:text-red-400',         icon: TrendingDown },
                    { label: t.advance, value: totalAdvance, color: 'text-blue-600 dark:text-blue-400',       icon: DollarSign  },
                    { label: t.pendingRecord, value: pendingTotal, color: 'text-amber-600 dark:text-amber-400', icon: Clock      },
                  ].filter(item => item.value > 0).map(({ label, value, color, icon: Icon }) => (
                    <div key={label} className="flex items-center justify-between text-sm">
                      <div className={clsx('flex items-center gap-1.5', color)}>
                        <Icon size={13} /><span className="text-gray-600 dark:text-gray-400">{label}</span>
                      </div>
                      <span className={clsx('font-medium', color)}>{fmt(value)} mln</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Record count badge */}
              {records.length > 0 && (
                <div className="flex items-center justify-between pt-2 border-t border-gray-100 dark:border-gray-700">
                  <span className="text-xs text-gray-500">{t.financeRecords}</span>
                  <span className="text-xs font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded-full">{records.length}</span>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><span className="font-semibold text-gray-900 dark:text-white">{t.statistics}</span></CardHeader>
            <CardContent className="space-y-3">
              {[
                { icon: CheckSquare, label: t.tasksCount,        value: projectTasks.length,       color: 'text-blue-600 dark:text-blue-400' },
                { icon: AlertTriangle, label: t.overdue,         value: overdue.length,            color: 'text-red-600 dark:text-red-400' },
                { icon: FileText, label: t.docsCount,            value: projectDocs.length,        color: 'text-purple-600 dark:text-purple-400' },
                { icon: Users, label: t.participantsCount,       value: project.participants.length, color: 'text-emerald-600 dark:text-emerald-400' },
              ].map(({ icon: Icon, label, value, color }) => (
                <div key={label} className="flex items-center justify-between p-2.5 bg-gray-50 dark:bg-gray-700/30 rounded-lg">
                  <div className="flex items-center gap-2">
                    <Icon size={14} className={color} />
                    <span className="text-sm text-gray-600 dark:text-gray-400">{label}</span>
                  </div>
                  <span className={`font-bold ${color}`}>{value}</span>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><span className="font-semibold text-gray-900 dark:text-white">{t.team}</span></CardHeader>
            <CardContent className="space-y-2">
              {gip && (
                <div className="flex items-center gap-3 p-2 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800/50 rounded-lg">
                  <Avatar name={gip.name} size="sm" />
                  <div>
                    <p className="text-sm text-gray-700 dark:text-gray-200">{gip.name}</p>
                    <p className="text-xs text-blue-600 dark:text-blue-400">{t.gipLabel}</p>
                  </div>
                </div>
              )}
              {project.participants.filter(pid => pid !== project.gipId).map(pid => {
                const member = users.find(u => u.id === pid);
                return member ? (
                  <div key={pid} className="flex items-center gap-3 p-2">
                    <Avatar name={member.name} size="sm" />
                    <div>
                      <p className="text-sm text-gray-700 dark:text-gray-200">{member.name}</p>
                      <p className="text-xs text-gray-500">{member.department || '—'}</p>
                    </div>
                  </div>
                ) : null;
              })}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Finance Records — full-width section */}
      <div className="mt-6">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <span className="font-semibold text-gray-900 dark:text-white">{t.financeRecords}</span>
              <Button size="sm" icon={<Plus size={14} />} variant="primary" onClick={() => setShowAddRecord(true)}>
                {t.addRecord}
              </Button>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {records.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
                <div className="w-12 h-12 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center mb-3">
                  <DollarSign size={22} className="text-gray-400" />
                </div>
                <p className="text-sm text-gray-400">{t.noRecords}</p>
                <Button size="sm" variant="primary" icon={<Plus size={12} />} className="mt-4" onClick={() => setShowAddRecord(true)}>
                  {t.addRecord}
                </Button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
                      {[t.typeLabel, t.amountLabel, 'Tavsif', t.categoryLabel, 'Sana', 'Holat', ''].map((h, i) => (
                        <th key={i} className="px-4 py-3 text-left text-xs text-gray-500 font-medium">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {records.map(r => {
                      const tc2 = typeConfig[r.type] ?? typeConfig.income;
                      const sc = statusConfig[r.status] ?? statusConfig.pending;
                      const TypeIcon = tc2.icon;
                      const isNeg = r.type === 'expense' || r.type === 'payment';
                      return (
                        <tr key={r.id} className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/40 transition-colors">
                          <td className="px-4 py-3">
                            <span className={clsx('inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full', tc2.bg, tc2.color)}>
                              <TypeIcon size={10} /> {tc2.label}
                            </span>
                          </td>
                          <td className={clsx('px-4 py-3 text-sm font-semibold', tc2.color)}>
                            {isNeg ? '−' : '+'}{fmt(r.amount)} mln
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300 max-w-[180px] truncate">
                            {r.description || '—'}
                          </td>
                          <td className="px-4 py-3 text-xs text-gray-500">{r.category || '—'}</td>
                          <td className="px-4 py-3 text-xs text-gray-500">
                            {r.date ? new Date(r.date).toLocaleDateString('uz-UZ') : '—'}
                          </td>
                          <td className="px-4 py-3">
                            <Badge variant={sc.variant} size="sm">{sc.label}</Badge>
                          </td>
                          <td className="px-4 py-3">
                            <button
                              onClick={() => setConfirmDeleteRecord(r.id)}
                              disabled={deletingRecordId === r.id}
                              className="text-gray-400 hover:text-red-500 dark:hover:text-red-400 transition-colors disabled:opacity-50"
                            >
                              <Trash2 size={14} />
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                  <tfoot>
                    <tr className="bg-gray-50 dark:bg-gray-800/50 border-t-2 border-gray-200 dark:border-gray-700">
                      <td className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Jami</td>
                      <td className="px-4 py-3 text-sm font-bold text-gray-900 dark:text-white">
                        <span className="text-emerald-600 dark:text-emerald-400">+{fmt(totalIncome)} mln</span>
                        {totalExpense > 0 && <span className="ml-2 text-red-500 dark:text-red-400">−{fmt(totalExpense)} mln</span>}
                      </td>
                      <td colSpan={5} />
                    </tr>
                  </tfoot>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Add Record Modal */}
      <Modal
        open={showAddRecord}
        onClose={() => { setShowAddRecord(false); setAddRecordForm(emptyForm); }}
        title={t.addRecordTitle}
        footer={
          <div className="flex justify-end gap-3">
            <Button onClick={() => { setShowAddRecord(false); setAddRecordForm(emptyForm); }}>{tc.cancel}</Button>
            <Button
              variant="primary"
              loading={savingRecord}
              disabled={!addRecordForm.amount || parseFloat(addRecordForm.amount) <= 0}
              onClick={handleAddRecord}
            >
              {tc.save}
            </Button>
          </div>
        }
      >
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1.5">{t.typeLabel}</label>
              <select
                value={addRecordForm.type}
                onChange={e => setAddRecordForm(f => ({ ...f, type: e.target.value as RecordType }))}
                className={inputCls}
              >
                <option value="income">{t.income}</option>
                <option value="expense">{t.expense}</option>
                <option value="advance">{t.advance}</option>
                <option value="payment">{t.payment}</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1.5">{t.amountLabel}</label>
              <input
                type="number"
                min="0"
                step="1000000"
                placeholder="e.g. 50000000"
                value={addRecordForm.amount}
                onChange={e => setAddRecordForm(f => ({ ...f, amount: e.target.value }))}
                className={inputCls}
              />
            </div>
          </div>

          <div>
            <label className="block text-xs text-gray-500 mb-1.5">Tavsif</label>
            <input
              type="text"
              placeholder="Qisqacha tavsif..."
              value={addRecordForm.description}
              onChange={e => setAddRecordForm(f => ({ ...f, description: e.target.value }))}
              className={inputCls}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1.5">{t.categoryLabel}</label>
              <input
                type="text"
                placeholder="Loyiha, ish haqi..."
                value={addRecordForm.category}
                onChange={e => setAddRecordForm(f => ({ ...f, category: e.target.value }))}
                className={inputCls}
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1.5">Sana</label>
              <input
                type="date"
                value={addRecordForm.date}
                onChange={e => setAddRecordForm(f => ({ ...f, date: e.target.value }))}
                className={inputCls}
              />
            </div>
          </div>

          <div>
            <label className="block text-xs text-gray-500 mb-1.5">Holat</label>
            <select
              value={addRecordForm.status}
              onChange={e => setAddRecordForm(f => ({ ...f, status: e.target.value as RecordStatus }))}
              className={inputCls}
            >
              <option value="pending">{t.pendingRecord}</option>
              <option value="confirmed">{t.confirmed}</option>
              <option value="cancelled">{t.cancelledRecord}</option>
            </select>
          </div>

          {/* Preview */}
          {addRecordForm.amount && parseFloat(addRecordForm.amount) > 0 && (
            <div className={clsx(
              'flex items-center gap-3 p-3 rounded-lg border',
              addRecordForm.type === 'income' || addRecordForm.type === 'advance'
                ? 'bg-emerald-50 border-emerald-200 dark:bg-emerald-900/20 dark:border-emerald-800'
                : 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800'
            )}>
              <DollarSign size={16} className={typeConfig[addRecordForm.type].color} />
              <div>
                <p className={clsx('text-sm font-semibold', typeConfig[addRecordForm.type].color)}>
                  {addRecordForm.type === 'expense' || addRecordForm.type === 'payment' ? '−' : '+'}
                  {fmt(parseFloat(addRecordForm.amount))} mln so'm
                </p>
                <p className="text-xs text-gray-500">{typeConfig[addRecordForm.type].label} · {t.pendingRecord}</p>
              </div>
            </div>
          )}
        </div>
      </Modal>

      {/* Edit modal */}
      <Modal open={showEdit} onClose={() => setShowEdit(false)} title={t.editProject}
        footer={
          <div className="flex justify-end gap-3">
            <Button onClick={() => setShowEdit(false)}>{tc.cancel}</Button>
            <Button variant="primary" onClick={handleSave} disabled={!editForm.name.trim()}>{tc.save}</Button>
          </div>
        }>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1.5">{pt.nameLabel}</label>
              <input value={editForm.name} onChange={e => setEditForm(f => ({ ...f, name: e.target.value }))} className={inputCls} />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1.5">{pt.clientLabel}</label>
              <input value={editForm.client} onChange={e => setEditForm(f => ({ ...f, client: e.target.value }))} className={inputCls} />
            </div>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1.5">{pt.addressLabel}</label>
            <input value={editForm.address} onChange={e => setEditForm(f => ({ ...f, address: e.target.value }))} className={inputCls} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1.5">{t.startDate}</label>
              <input type="date" value={editForm.startDate} onChange={e => setEditForm(f => ({ ...f, startDate: e.target.value }))} className={inputCls} />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1.5">{pt.deadlineLabel}</label>
              <input type="date" value={editForm.deadline} onChange={e => setEditForm(f => ({ ...f, deadline: e.target.value }))} className={inputCls} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1.5">{pt.stageLabel}</label>
              <select value={editForm.stage} onChange={e => setEditForm(f => ({ ...f, stage: e.target.value as ProjectStage }))} className={inputCls}>
                {stages.map(s => <option key={s} value={s}>{tStage[s]}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1.5">{pt.priorityLabel}</label>
              <select value={editForm.priority} onChange={e => setEditForm(f => ({ ...f, priority: e.target.value as Project['priority'] }))} className={inputCls}>
                {(['low', 'medium', 'high', 'critical'] as const).map(p => <option key={p} value={p}>{tPriority[p]}</option>)}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1.5">{pt.gipLabel}</label>
              <select value={editForm.gipId} onChange={e => setEditForm(f => ({ ...f, gipId: e.target.value }))} className={inputCls}>
                <option value="">{pt.notAssigned}</option>
                {gipUsers.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1.5">{pt.budgetLabel}</label>
              <input type="number" value={editForm.budget} onChange={e => setEditForm(f => ({ ...f, budget: e.target.value }))} className={inputCls} />
            </div>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1.5">{tStatus[editForm.status]}</label>
            <select value={editForm.status} onChange={e => setEditForm(f => ({ ...f, status: e.target.value as ProjectStatus }))} className={inputCls}>
              {statuses.map(s => <option key={s} value={s}>{tStatus[s]}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1.5">Описание</label>
            <textarea value={editForm.description} onChange={e => setEditForm(f => ({ ...f, description: e.target.value }))}
              rows={3} className={inputCls + ' resize-none'} />
          </div>
        </div>
      </Modal>

      {/* Delete project confirmation */}
      {showConfirmDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60" onClick={() => setShowConfirmDelete(false)} />
          <div className="relative w-full max-w-sm bg-white border border-gray-200 rounded-2xl shadow-2xl p-6 dark:bg-gray-800 dark:border-gray-700">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center flex-shrink-0">
                <Trash2 size={18} className="text-red-600 dark:text-red-400" />
              </div>
              <h2 className="text-base font-semibold text-gray-900 dark:text-white">{tc.delete}</h2>
            </div>
            <p className="text-sm text-gray-500 mb-6">{t.confirmDelete}</p>
            <div className="flex justify-end gap-3">
              <Button onClick={() => setShowConfirmDelete(false)}>{tc.cancel}</Button>
              <Button variant="danger" icon={<Trash2 size={14} />} onClick={handleDelete}>{tc.delete}</Button>
            </div>
          </div>
        </div>
      )}

      {/* Delete record confirmation */}
      {confirmDeleteRecord && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60" onClick={() => setConfirmDeleteRecord(null)} />
          <div className="relative w-full max-w-sm bg-white border border-gray-200 rounded-2xl shadow-2xl p-6 dark:bg-gray-800 dark:border-gray-700">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center flex-shrink-0">
                <Trash2 size={18} className="text-red-600 dark:text-red-400" />
              </div>
              <h2 className="text-base font-semibold text-gray-900 dark:text-white">{tc.delete}</h2>
            </div>
            <p className="text-sm text-gray-500 mb-6">{t.deleteRecordConfirm}</p>
            <div className="flex justify-end gap-3">
              <Button onClick={() => setConfirmDeleteRecord(null)}>{tc.cancel}</Button>
              <Button
                variant="danger"
                loading={deletingRecordId === confirmDeleteRecord}
                icon={<Trash2 size={14} />}
                onClick={() => handleDeleteRecord(confirmDeleteRecord)}
              >
                {tc.delete}
              </Button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
