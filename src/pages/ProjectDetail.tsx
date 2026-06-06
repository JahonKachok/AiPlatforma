import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Layout } from '../components/layout/Layout';
import { Card, CardHeader, CardContent } from '../components/ui/Card';
import { Badge, getProjectStatusBadge, getPriorityBadge, getTaskStatusBadge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { Avatar } from '../components/ui/Avatar';
import { useStore } from '../store/useStore';
import { ArrowLeft, MapPin, Clock, Users, Layers, CheckSquare, FileText, AlertTriangle, Pencil, Trash2 } from 'lucide-react';
import { translations } from '../i18n/translations';
import type { ProjectStatus, ProjectStage, Project } from '../types';
import { projectService } from '../services/projectService';
import { adaptProject } from '../services/adapters';

const inputCls = "w-full bg-gray-100 border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-700 focus:outline-none focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200";

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
  // The project list endpoint (which populates `projects`) returns a trimmed-down
  // shape with no description/startDate/sections/sub_objects/members. Keep the
  // full record fetched by id in its own state so a background refresh of the
  // list (e.g. initializeData) can't clobber the richer detail data.
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

  useEffect(() => {
    setDetail(null);
    if (!id) return;
    let cancelled = false;
    projectService.getProject(id)
      .then(result => { if (!cancelled) setDetail(adaptProject(result)); })
      .catch(() => { /* keep store data (e.g. offline/mock mode) */ });
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
        // Backend has no "planning" status; closest valid equivalent is "active"
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
    } catch { /* fall through to local removal */ }
    deleteProject(project.id);
    navigate('/projects');
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

        <div className="space-y-6">
          <Card>
            <CardHeader><span className="font-semibold text-gray-900 dark:text-white">{t.finance}</span></CardHeader>
            <CardContent className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-500">{t.budget}</span>
                  <span className="text-gray-900 dark:text-white font-medium">{(project.budget / 1000000).toFixed(1)} mln</span>
                </div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-500">{t.paid}</span>
                  <span className="text-emerald-600 dark:text-emerald-400 font-medium">{(project.paid / 1000000).toFixed(1)} mln</span>
                </div>
                <div className="flex justify-between text-sm mb-3">
                  <span className="text-gray-500">{t.remainder}</span>
                  <span className="text-amber-600 dark:text-amber-400 font-medium">{((project.budget - project.paid) / 1000000).toFixed(1)} mln</span>
                </div>
                <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${progress}%` }} />
                </div>
                <p className="text-xs text-gray-400 text-right mt-1">{progress}%</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><span className="font-semibold text-gray-900 dark:text-white">{t.statistics}</span></CardHeader>
            <CardContent className="space-y-3">
              {[
                { icon: CheckSquare, label: t.tasksCount, value: projectTasks.length, color: 'text-blue-600 dark:text-blue-400' },
                { icon: AlertTriangle, label: t.overdue, value: overdue.length, color: 'text-red-600 dark:text-red-400' },
                { icon: FileText, label: t.docsCount, value: projectDocs.length, color: 'text-purple-600 dark:text-purple-400' },
                { icon: Users, label: t.participantsCount, value: project.participants.length, color: 'text-emerald-600 dark:text-emerald-400' },
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

      {/* Delete confirmation */}
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
    </Layout>
  );
}
