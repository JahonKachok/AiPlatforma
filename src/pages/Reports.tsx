import { useState } from 'react';
import { Layout } from '../components/layout/Layout';
import { Card, CardHeader, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { useStore } from '../store/useStore';
import { FileSpreadsheet } from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, PieChart, Pie, Cell, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis
} from 'recharts';
import { translations } from '../i18n/translations';
import { reportService } from '../services/reportService';

const COLORS = ['#3b82f6', '#8b5cf6', '#f59e0b', '#10b981', '#ef4444', '#6b7280'];

export default function Reports() {
  const { projects, tasks, documents, users, language, darkMode } = useStore();
  const t = translations[language].reports;
  const tStatus = translations[language].taskStatus;
  const tProjectStatus = translations[language].projectStatus;
  const [exporting, setExporting] = useState<string | null>(null);

  const handleExport = async (kind: 'projects' | 'tasks' | 'finance' | 'employees') => {
    setExporting(kind);
    try {
      await reportService.downloadExport(kind);
    } catch { /* backend unavailable */ }
    setExporting(null);
  };

  const taskByUser = users.map(u => ({
    name: u.name.split(' ')[0],
    total: tasks.filter(task => task.assigneeId === u.id).length,
    completed: tasks.filter(task => task.assigneeId === u.id && task.status === 'completed').length,
    inProgress: tasks.filter(task => task.assigneeId === u.id && task.status === 'in_progress').length,
  })).filter(u => u.total > 0);

  const monthlyFinance = t.months.map((month, i) => {
    const financeMap = [0, 0, 50, 0, 0, 67, 0, 256];
    const expenseMap = [0, 0, 8, 5, 6, 13, 0, 0];
    return { month, income: financeMap[i] || 0, expense: expenseMap[i] || 0 };
  });

  const projectStatusData = Object.entries(
    projects.reduce((acc, p) => ({ ...acc, [p.status]: (acc[p.status] || 0) + 1 }), {} as Record<string, number>)
  ).map(([status, count]) => ({ name: tProjectStatus[status] || status, value: count }));

  const taskStatusData = Object.entries(
    tasks.reduce((acc, task) => ({ ...acc, [task.status]: (acc[task.status] || 0) + 1 }), {} as Record<string, number>)
  ).map(([status, count]) => ({ name: tStatus[status] || status, value: count }));

  const radarData = [
    { subject: t.completedTasks, value: Math.round(Math.min(100, (tasks.filter(task => task.status === 'completed').length / Math.max(tasks.length, 1)) * 100)) },
    { subject: t.approvedDocs, value: Math.round(Math.min(100, (documents.filter(d => d.status === 'approved').length / Math.max(documents.length, 1)) * 100)) },
    { subject: t.paidMln, value: Math.round(Math.min(100, (projects.reduce((a, p) => a + p.paid, 0) / Math.max(projects.reduce((a, p) => a + p.budget, 0), 1)) * 100)) },
    { subject: t.activeEmployees, value: Math.round(Math.min(100, (projects.filter(p => p.status === 'active').length / Math.max(projects.length, 1)) * 100)) },
    { subject: t.metrics, value: Math.round(Math.min(100, (users.filter(u => u.isActive).length / Math.max(users.length, 1)) * 100)) },
  ];

  const summaryStats = [
    { label: t.completedTasks, value: tasks.filter(task => task.status === 'completed').length, total: tasks.length, color: 'text-emerald-600 dark:text-emerald-400' },
    { label: t.approvedDocs, value: documents.filter(d => d.status === 'approved').length, total: documents.length, color: 'text-blue-600 dark:text-blue-400' },
    { label: t.paidMln, value: (projects.reduce((a, p) => a + p.paid, 0) / 1000000).toFixed(0), total: null, color: 'text-purple-600 dark:text-purple-400' },
    { label: t.activeEmployees, value: users.filter(u => u.isActive).length, total: users.length, color: 'text-amber-600 dark:text-amber-400' },
  ];

  const tooltipStyle = {
    backgroundColor: darkMode ? '#1f2937' : '#ffffff',
    border: `1px solid ${darkMode ? '#374151' : '#e5e7eb'}`,
    borderRadius: '8px',
    color: darkMode ? '#f9fafb' : '#111827',
  };
  const tickColor = darkMode ? '#6b7280' : '#9ca3af';
  const gridColor = darkMode ? '#374151' : '#f3f4f6';
  const polarGridColor = darkMode ? '#374151' : '#e5e7eb';
  const angleAxisColor = darkMode ? '#9ca3af' : '#6b7280';

  return (
    <Layout title={t.title} subtitle={t.subtitle}>
      <div className="flex items-center gap-2 flex-wrap mb-6">
        <span className="text-sm text-gray-500 mr-1">{t.exportTitle}:</span>
        {([
          ['projects', t.exportProjects],
          ['tasks', t.exportTasks],
          ['finance', t.exportFinance],
          ['employees', t.exportEmployees],
        ] as const).map(([kind, label]) => (
          <Button
            key={kind}
            size="sm"
            icon={<FileSpreadsheet size={14} />}
            loading={exporting === kind}
            onClick={() => handleExport(kind)}
          >
            {label}
          </Button>
        ))}
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {summaryStats.map(({ label, value, total, color }) => (
          <div key={label} className="bg-white border border-gray-200 rounded-xl p-4 dark:bg-gray-800 dark:border-gray-700">
            <p className={`text-3xl font-bold ${color}`}>
              {value}{total !== null && <span className="text-base font-normal text-gray-400"> / {total}</span>}
            </p>
            <p className="text-xs text-gray-500 mt-1">{label}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-6">
        <Card>
          <CardHeader><span className="font-semibold text-gray-900 dark:text-white">{t.tasksByEmployee}</span></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={taskByUser} barSize={16}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                <XAxis dataKey="name" tick={{ fill: tickColor, fontSize: 11 }} />
                <YAxis tick={{ fill: tickColor, fontSize: 11 }} />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="total" fill="#3b82f6" fillOpacity={0.6} name={t.total} />
                <Bar dataKey="completed" fill="#10b981" name={t.completed} />
                <Bar dataKey="inProgress" fill="#8b5cf6" name={t.inProgress} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><span className="font-semibold text-gray-900 dark:text-white">{t.financeTrend}</span></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={monthlyFinance}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                <XAxis dataKey="month" tick={{ fill: tickColor, fontSize: 11 }} />
                <YAxis tick={{ fill: tickColor, fontSize: 11 }} />
                <Tooltip contentStyle={tooltipStyle} />
                <Line type="monotone" dataKey="income" stroke="#10b981" strokeWidth={2} dot={false} name={t.income} />
                <Line type="monotone" dataKey="expense" stroke="#ef4444" strokeWidth={2} dot={false} name={t.expense} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><span className="font-semibold text-gray-900 dark:text-white">{t.projectStatuses}</span></CardHeader>
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
                    <span className="flex items-center gap-2 text-sm text-gray-500">
                      <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: COLORS[i % COLORS.length] }} />
                      {entry.name}
                    </span>
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-200">{entry.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><span className="font-semibold text-gray-900 dark:text-white">{t.platformHealth}</span></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <RadarChart data={radarData}>
                <PolarGrid stroke={polarGridColor} />
                <PolarAngleAxis dataKey="subject" tick={{ fill: angleAxisColor, fontSize: 11 }} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: tickColor, fontSize: 10 }} />
                <Radar name={t.metrics} dataKey="value" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.25} strokeWidth={2} />
                <Tooltip contentStyle={tooltipStyle} formatter={(v) => [`${v}%`]} />
              </RadarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><span className="font-semibold text-gray-900 dark:text-white">{t.taskStatusDistribution}</span></CardHeader>
        <CardContent>
          <div className="flex gap-4 items-center flex-wrap">
            {taskStatusData.map((item, i) => {
              const pct = tasks.length > 0 ? Math.round((item.value / tasks.length) * 100) : 0;
              return (
                <div key={item.name} className="flex-1 min-w-24">
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-gray-500 truncate">{item.name}</span>
                    <span className="text-gray-700 dark:text-gray-300 ml-2">{item.value}</span>
                  </div>
                  <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
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
