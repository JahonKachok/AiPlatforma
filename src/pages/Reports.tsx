import { Layout } from '../components/layout/Layout';
import { Card, CardHeader, CardContent } from '../components/ui/Card';
import { useStore } from '../store/useStore';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, PieChart, Pie, Cell, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis
} from 'recharts';
import { taskStatusLabels, projectStatusLabels } from '../data/mockData';

const COLORS = ['#3b82f6', '#8b5cf6', '#f59e0b', '#10b981', '#ef4444', '#6b7280'];

export default function Reports() {
  const { projects, tasks, documents, users } = useStore();

  // Task stats per assignee
  const taskByUser = users.map(u => ({
    name: u.name.split(' ')[0],
    total: tasks.filter(t => t.assigneeId === u.id).length,
    completed: tasks.filter(t => t.assigneeId === u.id && t.status === 'completed').length,
    inProgress: tasks.filter(t => t.assigneeId === u.id && t.status === 'in_progress').length,
  })).filter(u => u.total > 0);

  // Monthly finance trend
  const monthlyFinance = [
    { month: 'Янв', income: 0, expense: 0 },
    { month: 'Фев', income: 0, expense: 0 },
    { month: 'Мар', income: 50, expense: 8 },
    { month: 'Апр', income: 0, expense: 5 },
    { month: 'Май', income: 0, expense: 6 },
    { month: 'Июн', income: 67, expense: 13 },
    { month: 'Июл', income: 0, expense: 0 },
    { month: 'Авг', income: 256, expense: 0 },
  ];

  // Project status distribution
  const projectStatusData = Object.entries(
    projects.reduce((acc, p) => ({ ...acc, [p.status]: (acc[p.status] || 0) + 1 }), {} as Record<string, number>)
  ).map(([status, count]) => ({ name: projectStatusLabels[status] || status, value: count }));

  // Task status distribution
  const taskStatusData = Object.entries(
    tasks.reduce((acc, t) => ({ ...acc, [t.status]: (acc[t.status] || 0) + 1 }), {} as Record<string, number>)
  ).map(([status, count]) => ({ name: taskStatusLabels[status], value: count }));

  // Radar for project health
  const radarData = [
    { subject: 'Задачи', value: Math.min(100, (tasks.filter(t => t.status === 'completed').length / tasks.length) * 100) },
    { subject: 'Документы', value: Math.min(100, (documents.filter(d => d.status === 'approved').length / Math.max(documents.length, 1)) * 100) },
    { subject: 'Финансы', value: Math.min(100, (projects.reduce((a, p) => a + p.paid, 0) / Math.max(projects.reduce((a, p) => a + p.budget, 0), 1)) * 100) },
    { subject: 'Проекты', value: Math.min(100, (projects.filter(p => p.status === 'active').length / Math.max(projects.length, 1)) * 100) },
    { subject: 'Команда', value: Math.min(100, (users.filter(u => u.isActive).length / Math.max(users.length, 1)) * 100) },
  ].map(d => ({ ...d, value: Math.round(d.value) }));

  const summaryStats = [
    { label: 'Завершено задач', value: tasks.filter(t => t.status === 'completed').length, total: tasks.length, color: 'text-emerald-400' },
    { label: 'Согл. документов', value: documents.filter(d => d.status === 'approved').length, total: documents.length, color: 'text-blue-400' },
    { label: 'Выплачено (млн)', value: (projects.reduce((a, p) => a + p.paid, 0) / 1000000).toFixed(0), total: null, color: 'text-purple-400' },
    { label: 'Активных сотр.', value: users.filter(u => u.isActive).length, total: users.length, color: 'text-amber-400' },
  ];

  return (
    <Layout title="Аналитика и отчёты" subtitle="Сводная статистика по платформе">
      {/* Summary */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {summaryStats.map(({ label, value, total, color }) => (
          <div key={label} className="bg-gray-800 border border-gray-700 rounded-xl p-4">
            <p className={`text-3xl font-bold ${color}`}>{value}{total !== null && <span className="text-base font-normal text-gray-600"> / {total}</span>}</p>
            <p className="text-xs text-gray-500 mt-1">{label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-6">
        {/* Task by user */}
        <Card>
          <CardHeader><span className="font-semibold text-white">Задачи по сотрудникам</span></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={taskByUser} barSize={16}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="name" tick={{ fill: '#6b7280', fontSize: 11 }} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} />
                <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px', color: '#f9fafb' }} />
                <Bar dataKey="total" fill="#3b82f6" fillOpacity={0.6} name="Всего" />
                <Bar dataKey="completed" fill="#10b981" name="Завершено" />
                <Bar dataKey="inProgress" fill="#8b5cf6" name="В работе" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Finance trend */}
        <Card>
          <CardHeader><span className="font-semibold text-white">Финансовый тренд (млн сум)</span></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={monthlyFinance}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="month" tick={{ fill: '#6b7280', fontSize: 11 }} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} />
                <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px', color: '#f9fafb' }} />
                <Line type="monotone" dataKey="income" stroke="#10b981" strokeWidth={2} dot={false} name="Доходы" />
                <Line type="monotone" dataKey="expense" stroke="#ef4444" strokeWidth={2} dot={false} name="Расходы" />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Project status pie */}
        <Card>
          <CardHeader><span className="font-semibold text-white">Статусы проектов</span></CardHeader>
          <CardContent>
            <div className="flex items-center gap-6">
              <ResponsiveContainer width={160} height={160}>
                <PieChart>
                  <Pie data={projectStatusData} cx="50%" cy="50%" innerRadius={45} outerRadius={70} dataKey="value" paddingAngle={3}>
                    {projectStatusData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-2 flex-1">
                {projectStatusData.map((entry, i) => (
                  <div key={entry.name} className="flex items-center justify-between">
                    <span className="flex items-center gap-2 text-sm text-gray-400">
                      <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: COLORS[i % COLORS.length] }} />
                      {entry.name}
                    </span>
                    <span className="text-sm font-medium text-gray-200">{entry.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Radar */}
        <Card>
          <CardHeader><span className="font-semibold text-white">Общее здоровье платформы</span></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="#374151" />
                <PolarAngleAxis dataKey="subject" tick={{ fill: '#9ca3af', fontSize: 11 }} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: '#6b7280', fontSize: 10 }} />
                <Radar name="Показатели" dataKey="value" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.25} strokeWidth={2} />
                <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }} formatter={(v) => [`${v}%`]} />
              </RadarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Task status distribution */}
      <Card>
        <CardHeader><span className="font-semibold text-white">Распределение задач по статусам</span></CardHeader>
        <CardContent>
          <div className="flex gap-4 items-center">
            {taskStatusData.map((item, i) => {
              const pct = tasks.length > 0 ? Math.round((item.value / tasks.length) * 100) : 0;
              return (
                <div key={item.name} className="flex-1 min-w-0">
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-gray-400 truncate">{item.name}</span>
                    <span className="text-gray-300 ml-2">{item.value}</span>
                  </div>
                  <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${pct}%`, background: COLORS[i % COLORS.length] }} />
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </Layout>
  );
}
