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
import { useChartTheme, ChartTooltip, ChartLegend } from '../components/ui/chart';

export default function Reports() {
  const { projects, tasks, documents, users, language, darkMode } = useStore();
  const t = translations[language].reports;
  const tStatus = translations[language].taskStatus;
  const tProjectStatus = translations[language].projectStatus;
  const [exporting, setExporting] = useState<string | null>(null);
  const chart = useChartTheme();

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

  const tick = { fill: chart.tick, fontSize: 11 };
  const totalProjects = projectStatusData.reduce((a, e) => a + e.value, 0);

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
          <Card key={label} className="p-4">
            <p className={`text-3xl font-bold [font-variant-numeric:tabular-nums] ${color}`}>
              {value}{total !== null && <span className="text-base font-normal text-gray-400"> / {total}</span>}
            </p>
            <p className="text-xs text-gray-500 mt-1">{label}</p>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-6">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <span className="font-semibold text-gray-900 dark:text-white">{t.tasksByEmployee}</span>
              <ChartLegend items={[
                { label: t.total, color: chart.colors[0] },
                { label: t.completed, color: chart.colors[1] },
                { label: t.inProgress, color: chart.colors[4] },
              ]} />
            </div>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={taskByUser} barSize={14} barGap={2}>
                <CartesianGrid strokeDasharray="3 3" stroke={chart.grid} vertical={false} />
                <XAxis dataKey="name" tick={tick} axisLine={{ stroke: chart.axisLine }} tickLine={false} />
                <YAxis tick={tick} axisLine={false} tickLine={false} width={28} />
                <Tooltip content={<ChartTooltip />} cursor={{ fill: chart.cursorFill }} />
                <Bar dataKey="total" fill={chart.colors[0]} fillOpacity={0.55} name={t.total} radius={[4, 4, 0, 0]} />
                <Bar dataKey="completed" fill={chart.colors[1]} name={t.completed} radius={[4, 4, 0, 0]} />
                <Bar dataKey="inProgress" fill={chart.colors[4]} name={t.inProgress} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <span className="font-semibold text-gray-900 dark:text-white">{t.financeTrend}</span>
              <ChartLegend items={[
                { label: t.income, color: chart.colors[1] },
                { label: t.expense, color: chart.colors[5] },
              ]} />
            </div>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={monthlyFinance}>
                <CartesianGrid strokeDasharray="3 3" stroke={chart.grid} vertical={false} />
                <XAxis dataKey="month" tick={tick} axisLine={{ stroke: chart.axisLine }} tickLine={false} />
                <YAxis tick={tick} axisLine={false} tickLine={false} width={36} />
                <Tooltip content={<ChartTooltip />} cursor={{ stroke: chart.axisLine, strokeDasharray: '4 4' }} />
                <Line type="monotone" dataKey="income" stroke={chart.colors[1]} strokeWidth={2} dot={false} name={t.income}
                  activeDot={{ r: 4, strokeWidth: 2, stroke: darkMode ? '#1f2937' : '#ffffff' }} />
                <Line type="monotone" dataKey="expense" stroke={chart.colors[5]} strokeWidth={2} dot={false} name={t.expense}
                  activeDot={{ r: 4, strokeWidth: 2, stroke: darkMode ? '#1f2937' : '#ffffff' }} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><span className="font-semibold text-gray-900 dark:text-white">{t.projectStatuses}</span></CardHeader>
          <CardContent>
            <div className="flex items-center gap-6">
              <div className="relative flex-shrink-0">
                <ResponsiveContainer width={160} height={160}>
                  <PieChart>
                    <Pie
                      data={projectStatusData} cx="50%" cy="50%"
                      innerRadius={48} outerRadius={70}
                      dataKey="value" paddingAngle={3} cornerRadius={4} stroke="none"
                    >
                      {projectStatusData.map((_, i) => <Cell key={i} fill={chart.colors[i % chart.colors.length]} />)}
                    </Pie>
                    <Tooltip content={<ChartTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
                <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
                  <span className="text-xl font-bold text-gray-900 dark:text-white [font-variant-numeric:tabular-nums]">{totalProjects}</span>
                </div>
              </div>
              <div className="space-y-2 flex-1">
                {projectStatusData.map((entry, i) => (
                  <div key={entry.name} className="flex items-center justify-between">
                    <span className="flex items-center gap-2 text-sm text-gray-500">
                      <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: chart.colors[i % chart.colors.length] }} />
                      {entry.name}
                    </span>
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-200 [font-variant-numeric:tabular-nums]">{entry.value}</span>
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
                <PolarGrid stroke={chart.grid} />
                <PolarAngleAxis dataKey="subject" tick={{ fill: chart.tick, fontSize: 11 }} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: chart.tick, fontSize: 10 }} axisLine={false} />
                <Radar name={t.metrics} dataKey="value" stroke={chart.colors[0]} fill={chart.colors[0]} fillOpacity={0.2} strokeWidth={2} />
                <Tooltip content={<ChartTooltip formatter={v => `${v}%`} />} />
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
                    <span className="text-gray-700 dark:text-gray-300 ml-2 [font-variant-numeric:tabular-nums]">{item.value}</span>
                  </div>
                  <div className="h-2 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, background: chart.colors[i % chart.colors.length] }} />
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
