import { Layout } from '../components/layout/Layout';
import { Card, CardContent, CardHeader } from '../components/ui/Card';
import { Badge, getProjectStatusBadge, getPriorityBadge, getTaskStatusBadge } from '../components/ui/Badge';
import { Avatar } from '../components/ui/Avatar';
import { useStore } from '../store/useStore';
import { useNavigate } from 'react-router-dom';
import {
  FolderKanban, CheckSquare, AlertTriangle,
  Clock, DollarSign, ArrowRight, GitBranch
} from 'lucide-react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, BarChart, Bar
} from 'recharts';
import { translations } from '../i18n/translations';

const COLORS = ['#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444', '#10b981', '#6b7280'];

export default function Dashboard() {
  const { projects, tasks, documents, users, language, darkMode } = useStore();
  const navigate = useNavigate();
  const t = translations[language];
  const d = t.dashboard;

  const months = language === 'uz'
    ? ['Yan', 'Fev', 'Mar', 'Apr', 'May', 'Iyn', 'Iyl', 'Avg']
    : language === 'en'
    ? ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug']
    : ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг'];

  const areaData = [
    { month: months[0], tasks: 12, docs: 5 }, { month: months[1], tasks: 18, docs: 8 },
    { month: months[2], tasks: 24, docs: 12 }, { month: months[3], tasks: 20, docs: 9 },
    { month: months[4], tasks: 28, docs: 15 }, { month: months[5], tasks: 32, docs: 18 },
    { month: months[6], tasks: 27, docs: 14 }, { month: months[7], tasks: 35, docs: 20 },
  ];

  const activeProjects = projects.filter(p => p.status === 'active');
  const overdueTasks = tasks.filter(t => t.status !== 'completed' && new Date(t.deadline) < new Date());
  const pendingApprovals = documents.filter(doc => doc.status === 'review');
  const totalBudget = projects.reduce((a, p) => a + p.budget, 0);
  const totalPaid = projects.reduce((a, p) => a + p.paid, 0);

  const taskStatusData = Object.entries(
    tasks.reduce((acc, task) => ({ ...acc, [task.status]: (acc[task.status] || 0) + 1 }), {} as Record<string, number>)
  ).map(([status, count]) => ({ name: t.taskStatus[status] ?? status, value: count }));

  const projectFinanceData = projects.slice(0, 5).map(p => ({
    name: p.name.length > 15 ? p.name.slice(0, 15) + '...' : p.name,
    budget: Math.round(p.budget / 1000000),
    paid: Math.round(p.paid / 1000000),
  }));

  const statCards = [
    { label: d.activeProjects, value: activeProjects.length, icon: FolderKanban, color: 'text-blue-500 dark:text-blue-400', bg: 'bg-blue-100 dark:bg-blue-900/30', link: '/projects' },
    { label: d.tasksInProgress, value: tasks.filter(task => task.status === 'in_progress').length, icon: CheckSquare, color: 'text-purple-500 dark:text-purple-400', bg: 'bg-purple-100 dark:bg-purple-900/30', link: '/tasks' },
    { label: d.pendingApprovals, value: pendingApprovals.length, icon: GitBranch, color: 'text-amber-500 dark:text-amber-400', bg: 'bg-amber-100 dark:bg-amber-900/30', link: '/approvals' },
    { label: d.overdueTasks, value: overdueTasks.length, icon: AlertTriangle, color: 'text-red-500 dark:text-red-400', bg: 'bg-red-100 dark:bg-red-900/30', link: '/tasks' },
  ];

  const tooltipStyle = {
    backgroundColor: darkMode ? '#1f2937' : '#ffffff',
    border: `1px solid ${darkMode ? '#374151' : '#e5e7eb'}`,
    borderRadius: '8px',
    color: darkMode ? '#f9fafb' : '#111827',
  };

  const tickColor = darkMode ? '#6b7280' : '#9ca3af';
  const gridColor = darkMode ? '#374151' : '#f3f4f6';

  return (
    <Layout title={d.title} subtitle={d.subtitle}>
      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {statCards.map(({ label, value, icon: Icon, color, bg, link }) => (
          <Card key={label} hover onClick={() => navigate(link)} className="p-4">
            <div className="flex items-center justify-between mb-3">
              <div className={`p-2.5 rounded-xl ${bg}`}>
                <Icon size={20} className={color} />
              </div>
              <ArrowRight size={14} className="text-gray-400" />
            </div>
            <p className="text-3xl font-bold text-gray-900 dark:text-white">{value}</p>
            <p className="text-xs text-gray-500 mt-1">{label}</p>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-6">
        {/* Activity chart */}
        <Card className="xl:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <span className="font-semibold text-gray-900 dark:text-white">{d.activity}</span>
              <div className="flex gap-4 text-xs text-gray-500">
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500 inline-block" /> {d.tasks}</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-purple-500 inline-block" /> {d.documents}</span>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={areaData}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                <XAxis dataKey="month" tick={{ fill: tickColor, fontSize: 12 }} />
                <YAxis tick={{ fill: tickColor, fontSize: 12 }} />
                <Tooltip contentStyle={tooltipStyle} />
                <Area type="monotone" dataKey="tasks" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.15} strokeWidth={2} name={d.tasks} />
                <Area type="monotone" dataKey="docs" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.15} strokeWidth={2} name={d.documents} />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Task status pie */}
        <Card>
          <CardHeader><span className="font-semibold text-gray-900 dark:text-white">{d.taskStatuses}</span></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={160}>
              <PieChart>
                <Pie data={taskStatusData} cx="50%" cy="50%" innerRadius={45} outerRadius={75} dataKey="value" paddingAngle={3}>
                  {taskStatusData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={tooltipStyle} />
              </PieChart>
            </ResponsiveContainer>
            <div className="space-y-1.5 mt-2">
              {taskStatusData.map((entry, i) => (
                <div key={entry.name} className="flex items-center justify-between text-xs">
                  <span className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
                    <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: COLORS[i % COLORS.length] }} />
                    {entry.name}
                  </span>
                  <span className="text-gray-700 dark:text-gray-300 font-medium">{entry.value}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-6">
        {/* Finance chart */}
        <Card className="xl:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <span className="font-semibold text-gray-900 dark:text-white">{d.financeByProjects}</span>
              <div className="flex items-center gap-2">
                <DollarSign size={14} className="text-emerald-500" />
                <span className="text-sm text-gray-500">{(totalPaid / 1000000).toFixed(0)} / {(totalBudget / 1000000).toFixed(0)} {d.mln}</span>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={projectFinanceData} barSize={24}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                <XAxis dataKey="name" tick={{ fill: tickColor, fontSize: 11 }} />
                <YAxis tick={{ fill: tickColor, fontSize: 11 }} />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="budget" fill="#1d4ed8" fillOpacity={0.6} name={d.budget} />
                <Bar dataKey="paid" fill="#10b981" name={d.paid} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Team */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <span className="font-semibold text-gray-900 dark:text-white">{d.team}</span>
              <button onClick={() => navigate('/users')} className="text-xs text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300 flex items-center gap-1">
                {d.all} <ArrowRight size={12} />
              </button>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {users.slice(0, 6).map(u => (
              <div key={u.id} className="flex items-center gap-3">
                <Avatar name={u.name} size="sm" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-700 dark:text-gray-200 truncate">{u.name}</p>
                  <p className="text-xs text-gray-500">{u.department || '—'}</p>
                </div>
                <span className={`w-2 h-2 rounded-full ${u.isActive ? 'bg-emerald-400' : 'bg-gray-400'}`} />
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Active projects */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <span className="font-semibold text-gray-900 dark:text-white">{d.activeProjectsList}</span>
              <button onClick={() => navigate('/projects')} className="text-xs text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300 flex items-center gap-1">
                {d.all} <ArrowRight size={12} />
              </button>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {activeProjects.slice(0, 5).map(p => {
              const progress = p.budget > 0 ? Math.round((p.paid / p.budget) * 100) : 0;
              return (
                <div key={p.id} onClick={() => navigate(`/projects/${p.id}`)} className="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/30 rounded-lg p-2 -mx-2 transition-colors">
                  <div className="flex items-start justify-between gap-2 mb-1.5">
                    <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{p.name}</p>
                    <Badge variant={getProjectStatusBadge(p.status)}>{t.projectStatus[p.status] ?? p.status}</Badge>
                  </div>
                  <div className="flex items-center gap-2 mb-1.5">
                    <Clock size={12} className="text-gray-400" />
                    <span className="text-xs text-gray-500">{d.until} {p.deadline}</span>
                    <Badge variant={getPriorityBadge(p.priority)} size="sm">{t.priority[p.priority] ?? p.priority}</Badge>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                      <div className="h-full bg-blue-500 rounded-full" style={{ width: `${progress}%` }} />
                    </div>
                    <span className="text-xs text-gray-500 w-8">{progress}%</span>
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>

        {/* Recent tasks */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <span className="font-semibold text-gray-900 dark:text-white">{d.recentTasks}</span>
              <button onClick={() => navigate('/tasks')} className="text-xs text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300 flex items-center gap-1">
                {d.all} <ArrowRight size={12} />
              </button>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {tasks.slice(0, 6).map(task => {
              const assignee = useStore.getState().users.find(u => u.id === task.assigneeId);
              const isOverdue = task.status !== 'completed' && new Date(task.deadline) < new Date();
              return (
                <div key={task.id} onClick={() => navigate('/tasks')} className="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/30 rounded-lg p-2 -mx-2 transition-colors">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm text-gray-700 dark:text-gray-200 flex-1 truncate">{task.title}</p>
                    <Badge variant={getTaskStatusBadge(task.status)} size="sm">{t.taskStatus[task.status] ?? task.status}</Badge>
                  </div>
                  <div className="flex items-center gap-3 mt-1.5">
                    {assignee && <Avatar name={assignee.name} size="xs" />}
                    <span className="text-xs text-gray-500">{assignee?.name}</span>
                    <span className={`text-xs ml-auto flex items-center gap-1 ${isOverdue ? 'text-red-500 dark:text-red-400' : 'text-gray-400'}`}>
                      {isOverdue && <AlertTriangle size={10} />} {task.deadline}
                    </span>
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
