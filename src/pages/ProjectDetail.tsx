import { useParams, useNavigate } from 'react-router-dom';
import { Layout } from '../components/layout/Layout';
import { Card, CardHeader, CardContent } from '../components/ui/Card';
import { Badge, getProjectStatusBadge, getPriorityBadge, getTaskStatusBadge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Avatar } from '../components/ui/Avatar';
import { useStore } from '../store/useStore';
import { ArrowLeft, MapPin, Clock, Users, Layers, CheckSquare, FileText, AlertTriangle } from 'lucide-react';
import { projectStatusLabels, projectStageLabels, priorityLabels, taskStatusLabels } from '../data/mockData';

export default function ProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { projects, tasks, documents, users } = useStore();

  const project = projects.find(p => p.id === id);
  if (!project) return <Layout title="Проект не найден"><Button icon={<ArrowLeft size={16} />} onClick={() => navigate('/projects')}>Назад</Button></Layout>;

  const gip = users.find(u => u.id === project.gipId);
  const projectTasks = tasks.filter(t => t.projectId === id);
  const projectDocs = documents.filter(d => d.projectId === id);
  const progress = project.budget > 0 ? Math.round((project.paid / project.budget) * 100) : 0;
  const overdue = projectTasks.filter(t => t.status !== 'completed' && new Date(t.deadline) < new Date());

  return (
    <Layout title={project.name} subtitle={project.client}>
      <div className="flex items-center gap-3 mb-6">
        <Button variant="ghost" icon={<ArrowLeft size={16} />} onClick={() => navigate('/projects')}>Проекты</Button>
        <Badge variant={getProjectStatusBadge(project.status)} size="md">{projectStatusLabels[project.status]}</Badge>
        <Badge variant={getPriorityBadge(project.priority)} size="md">{priorityLabels[project.priority]}</Badge>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Main info */}
        <div className="xl:col-span-2 space-y-6">
          {/* Overview */}
          <Card>
            <CardHeader><span className="font-semibold text-white">Информация о проекте</span></CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                {[
                  { icon: MapPin, label: 'Адрес', value: project.address },
                  { icon: Layers, label: 'Стадия', value: projectStageLabels[project.stage] },
                  { icon: Clock, label: 'Дедлайн', value: project.deadline },
                  { icon: Clock, label: 'Начало', value: project.startDate },
                ].map(({ icon: Icon, label, value }) => (
                  <div key={label} className="flex items-center gap-3 p-3 bg-gray-700/30 rounded-lg">
                    <Icon size={16} className="text-gray-500 flex-shrink-0" />
                    <div>
                      <p className="text-xs text-gray-500">{label}</p>
                      <p className="text-sm text-gray-200">{value || '—'}</p>
                    </div>
                  </div>
                ))}
              </div>
              {project.description && (
                <p className="text-sm text-gray-400 mt-4 p-3 bg-gray-700/20 rounded-lg">{project.description}</p>
              )}
            </CardContent>
          </Card>

          {/* Sections */}
          {project.sections.length > 0 && (
            <Card>
              <CardHeader><span className="font-semibold text-white">Разделы проекта ({project.sections.length})</span></CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {project.sections.map(sec => {
                    const secGip = users.find(u => u.id === sec.gipId);
                    return (
                      <div key={sec.id} className="flex items-center gap-3 p-3 bg-gray-700/30 rounded-lg hover:bg-gray-700/50 transition-colors">
                        <div className="w-8 h-8 bg-blue-900/50 border border-blue-700 rounded-lg flex items-center justify-center text-xs font-bold text-blue-400">{sec.code}</div>
                        <div className="flex-1">
                          <p className="text-sm text-gray-200">{sec.name}</p>
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

          {/* Tasks */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <span className="font-semibold text-white">Задачи ({projectTasks.length})</span>
                <Button size="sm" onClick={() => navigate('/tasks')}>Открыть все</Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {projectTasks.slice(0, 6).map(t => {
                  const assignee = users.find(u => u.id === t.assigneeId);
                  const isOverdue = t.status !== 'completed' && new Date(t.deadline) < new Date();
                  return (
                    <div key={t.id} className="flex items-center gap-3 p-3 bg-gray-700/30 rounded-lg">
                      <CheckSquare size={14} className="text-gray-500 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-gray-200 truncate">{t.title}</p>
                        <div className="flex items-center gap-2 mt-0.5">
                          {assignee && <span className="text-xs text-gray-500">{assignee.name}</span>}
                          <span className={`text-xs ${isOverdue ? 'text-red-400' : 'text-gray-600'} flex items-center gap-1`}>
                            {isOverdue && <AlertTriangle size={10} />} {t.deadline}
                          </span>
                        </div>
                      </div>
                      <Badge variant={getTaskStatusBadge(t.status)} size="sm">{taskStatusLabels[t.status]}</Badge>
                    </div>
                  );
                })}
                {projectTasks.length === 0 && <p className="text-sm text-gray-600 text-center py-4">Нет задач</p>}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Finance */}
          <Card>
            <CardHeader><span className="font-semibold text-white">Финансы</span></CardHeader>
            <CardContent className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-500">Бюджет</span>
                  <span className="text-white font-medium">{(project.budget / 1000000).toFixed(1)} млн</span>
                </div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-500">Оплачено</span>
                  <span className="text-emerald-400 font-medium">{(project.paid / 1000000).toFixed(1)} млн</span>
                </div>
                <div className="flex justify-between text-sm mb-3">
                  <span className="text-gray-500">Остаток</span>
                  <span className="text-amber-400 font-medium">{((project.budget - project.paid) / 1000000).toFixed(1)} млн</span>
                </div>
                <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                  <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${progress}%` }} />
                </div>
                <p className="text-xs text-gray-600 text-right mt-1">{progress}%</p>
              </div>
            </CardContent>
          </Card>

          {/* Stats */}
          <Card>
            <CardHeader><span className="font-semibold text-white">Статистика</span></CardHeader>
            <CardContent className="space-y-3">
              {[
                { icon: CheckSquare, label: 'Задач', value: projectTasks.length, color: 'text-blue-400' },
                { icon: AlertTriangle, label: 'Просрочено', value: overdue.length, color: 'text-red-400' },
                { icon: FileText, label: 'Документов', value: projectDocs.length, color: 'text-purple-400' },
                { icon: Users, label: 'Участников', value: project.participants.length, color: 'text-emerald-400' },
              ].map(({ icon: Icon, label, value, color }) => (
                <div key={label} className="flex items-center justify-between p-2.5 bg-gray-700/30 rounded-lg">
                  <div className="flex items-center gap-2">
                    <Icon size={14} className={color} />
                    <span className="text-sm text-gray-400">{label}</span>
                  </div>
                  <span className={`font-bold ${color}`}>{value}</span>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Team */}
          <Card>
            <CardHeader><span className="font-semibold text-white">Команда</span></CardHeader>
            <CardContent className="space-y-2">
              {gip && (
                <div className="flex items-center gap-3 p-2 bg-blue-900/20 border border-blue-800/50 rounded-lg">
                  <Avatar name={gip.name} size="sm" />
                  <div>
                    <p className="text-sm text-gray-200">{gip.name}</p>
                    <p className="text-xs text-blue-400">ГИП</p>
                  </div>
                </div>
              )}
              {project.participants.filter(pid => pid !== project.gipId).map(pid => {
                const member = users.find(u => u.id === pid);
                return member ? (
                  <div key={pid} className="flex items-center gap-3 p-2">
                    <Avatar name={member.name} size="sm" />
                    <div>
                      <p className="text-sm text-gray-200">{member.name}</p>
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
