import { useParams, useNavigate } from 'react-router-dom';
import { Layout } from '../components/layout/Layout';
import { Card, CardHeader, CardContent } from '../components/ui/Card';
import { Badge, getProjectStatusBadge, getPriorityBadge, getTaskStatusBadge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Avatar } from '../components/ui/Avatar';
import { useStore } from '../store/useStore';
import { ArrowLeft, MapPin, Clock, Users, Layers, CheckSquare, FileText, AlertTriangle } from 'lucide-react';
import { translations } from '../i18n/translations';

export default function ProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { projects, tasks, documents, users, language } = useStore();
  const t = translations[language].projectDetail;
  const tStatus = translations[language].projectStatus;
  const tStage = translations[language].projectStage;
  const tPriority = translations[language].priority;
  const tTaskStatus = translations[language].taskStatus;

  const project = projects.find(p => p.id === id);
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

  return (
    <Layout title={project.name} subtitle={project.client}>
      <div className="flex items-center gap-3 mb-6">
        <Button variant="ghost" icon={<ArrowLeft size={16} />} onClick={() => navigate('/projects')}>{t.backBtn}</Button>
        <Badge variant={getProjectStatusBadge(project.status)} size="md">{tStatus[project.status] ?? project.status}</Badge>
        <Badge variant={getPriorityBadge(project.priority)} size="md">{tPriority[project.priority] ?? project.priority}</Badge>
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
    </Layout>
  );
}
