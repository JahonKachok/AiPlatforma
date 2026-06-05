import { useState } from 'react';
import { Layout } from '../components/layout/Layout';
import { Card, CardHeader, CardContent } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { useStore } from '../store/useStore';
import { DollarSign, TrendingUp, TrendingDown, Clock, CheckCircle } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { clsx } from 'clsx';
import { mockEmployeeFinances } from '../data/mockData';
import { translations } from '../i18n/translations';

const COLORS = ['#3b82f6', '#8b5cf6', '#f59e0b', '#10b981', '#ef4444'];

export default function Finance() {
  const { financials, projects, users, language, darkMode } = useStore();
  const t = translations[language].finance;
  const [tab, setTab] = useState<'overview' | 'records' | 'employees'>('overview');
  const [filterProject, setFilterProject] = useState('all');

  const typeConfig = {
    income: { label: t.income, color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-100 dark:bg-emerald-900/30', icon: TrendingUp },
    expense: { label: t.expense, color: 'text-red-600 dark:text-red-400', bg: 'bg-red-100 dark:bg-red-900/30', icon: TrendingDown },
    advance: { label: t.advance, color: 'text-blue-600 dark:text-blue-400', bg: 'bg-blue-100 dark:bg-blue-900/30', icon: DollarSign },
    payment: { label: t.payment, color: 'text-purple-600 dark:text-purple-400', bg: 'bg-purple-100 dark:bg-purple-900/30', icon: DollarSign },
  };

  const paymentStatusConfig = {
    pending: { label: t.pendingStatus, variant: 'warning' as const },
    paid: { label: t.paidStatus, variant: 'success' as const },
    overdue: { label: t.overdueStatus, variant: 'danger' as const },
  };

  const filtered = financials.filter(f => filterProject === 'all' || f.projectId === filterProject);
  const totalIncome = financials.filter(f => f.type === 'income' && f.status === 'paid').reduce((a, f) => a + f.amount, 0);
  const totalExpense = financials.filter(f => f.type === 'expense' && f.status === 'paid').reduce((a, f) => a + f.amount, 0);
  const pending = financials.filter(f => f.status === 'pending').reduce((a, f) => a + f.amount, 0);
  const totalBudget = projects.reduce((a, p) => a + p.budget, 0);

  const projectFinanceData = projects.slice(0, 5).map(p => ({
    name: p.name.length > 12 ? p.name.slice(0, 12) + '...' : p.name,
    budget: Math.round(p.budget / 1000000),
    paid: Math.round(p.paid / 1000000),
    remainder: Math.round((p.budget - p.paid) / 1000000),
  }));

  const tooltipStyle = {
    backgroundColor: darkMode ? '#1f2937' : '#ffffff',
    border: `1px solid ${darkMode ? '#374151' : '#e5e7eb'}`,
    borderRadius: '8px',
    color: darkMode ? '#f9fafb' : '#111827',
  };
  const tickColor = darkMode ? '#6b7280' : '#9ca3af';
  const gridColor = darkMode ? '#374151' : '#f3f4f6';

  const tabCls = (key: string) => clsx(
    'px-4 py-2 text-sm rounded-lg transition-colors',
    tab === key
      ? 'bg-white text-gray-900 shadow-sm dark:bg-gray-700 dark:text-white'
      : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
  );

  const selectCls = "bg-gray-100 border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700 focus:outline-none focus:border-blue-500 dark:bg-gray-800 dark:border-gray-700 dark:text-gray-300";

  return (
    <Layout title={t.title} subtitle={t.subtitle}>
      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[
          { label: t.totalBudget, value: totalBudget, icon: DollarSign, color: 'text-blue-600 dark:text-blue-400', bg: 'bg-blue-100 dark:bg-blue-900/30' },
          { label: t.received, value: totalIncome, icon: TrendingUp, color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-100 dark:bg-emerald-900/30' },
          { label: t.expenses, value: totalExpense, icon: TrendingDown, color: 'text-red-600 dark:text-red-400', bg: 'bg-red-100 dark:bg-red-900/30' },
          { label: t.expected, value: pending, icon: Clock, color: 'text-amber-600 dark:text-amber-400', bg: 'bg-amber-100 dark:bg-amber-900/30' },
        ].map(({ label, value, icon: Icon, color, bg }) => (
          <Card key={label} className="p-4">
            <div className="flex items-center gap-3 mb-2">
              <div className={clsx('p-2 rounded-xl', bg)}><Icon size={18} className={color} /></div>
            </div>
            <p className={clsx('text-2xl font-bold', color)}>{(value / 1000000).toFixed(1)} <span className="text-sm font-normal text-gray-500">{t.mln}</span></p>
            <p className="text-xs text-gray-500 mt-1">{label}</p>
          </Card>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-gray-100 p-1 rounded-xl w-fit dark:bg-gray-800">
        {[{ key: 'overview', label: t.overview }, { key: 'records', label: t.records }, { key: 'employees', label: t.employees }].map(tab => (
          <button key={tab.key} onClick={() => setTab(tab.key as any)} className={tabCls(tab.key)}>{tab.label}</button>
        ))}
      </div>

      {tab === 'overview' && (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <Card>
            <CardHeader><span className="font-semibold text-gray-900 dark:text-white">{t.budgetVsPayment}</span></CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={projectFinanceData} barSize={20}>
                  <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                  <XAxis dataKey="name" tick={{ fill: tickColor, fontSize: 11 }} />
                  <YAxis tick={{ fill: tickColor, fontSize: 11 }} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Bar dataKey="budget" fill="#1d4ed8" fillOpacity={0.6} name={t.budget} />
                  <Bar dataKey="paid" fill="#10b981" name={t.paid} />
                  <Bar dataKey="remainder" fill="#f59e0b" fillOpacity={0.6} name={t.remainder} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><span className="font-semibold text-gray-900 dark:text-white">{t.budgetDistribution}</span></CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={projectFinanceData} cx="50%" cy="50%" outerRadius={85} dataKey="budget" nameKey="name" paddingAngle={3}>
                    {projectFinanceData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip contentStyle={tooltipStyle} />
                </PieChart>
              </ResponsiveContainer>
              <div className="grid grid-cols-2 gap-2 mt-2">
                {projectFinanceData.map((p, i) => (
                  <div key={p.name} className="flex items-center gap-2 text-xs">
                    <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: COLORS[i % COLORS.length] }} />
                    <span className="text-gray-500 truncate">{p.name}</span>
                    <span className="text-gray-700 dark:text-gray-300 ml-auto">{p.budget}{t.mln}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="xl:col-span-2">
            <CardHeader><span className="font-semibold text-gray-900 dark:text-white">{t.financeByProjects}</span></CardHeader>
            <CardContent>
              <div className="space-y-4">
                {projects.map(p => {
                  const progress = p.budget > 0 ? Math.round((p.paid / p.budget) * 100) : 0;
                  return (
                    <div key={p.id}>
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-sm text-gray-700 dark:text-gray-300">{p.name}</span>
                        <div className="flex items-center gap-4 text-sm">
                          <span className="text-gray-500">{(p.budget / 1000000).toFixed(0)} {t.mln}</span>
                          <span className="text-emerald-600 dark:text-emerald-400">{(p.paid / 1000000).toFixed(0)} {t.mln}</span>
                          <span className="text-amber-600 dark:text-amber-400">{((p.budget - p.paid) / 1000000).toFixed(0)} {t.mln}</span>
                          <span className="text-xs text-gray-400 w-8 text-right">{progress}%</span>
                        </div>
                      </div>
                      <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                        <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${progress}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {tab === 'records' && (
        <div>
          <div className="flex items-center gap-3 mb-4">
            <select value={filterProject} onChange={e => setFilterProject(e.target.value)} className={selectCls}>
              <option value="all">{t.allProjects}</option>
              {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>
          <Card>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-gray-700">
                    {[t.description, t.projectColumn, t.typeColumn, t.amountColumn, t.dateColumn, t.statusColumn].map(h => (
                      <th key={h} className="px-4 py-3 text-left text-xs text-gray-500 font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.map(f => {
                    const project = projects.find(p => p.id === f.projectId);
                    const cfg = typeConfig[f.type as keyof typeof typeConfig] || typeConfig.income;
                    const statusCfg = paymentStatusConfig[f.status];
                    const Icon = cfg.icon;
                    return (
                      <tr key={f.id} className="border-b border-gray-100 hover:bg-gray-50 transition-colors dark:border-gray-800 dark:hover:bg-gray-800/50">
                        <td className="px-4 py-3 text-sm text-gray-700 dark:text-gray-200">{f.description}</td>
                        <td className="px-4 py-3 text-xs text-gray-500">{project?.name}</td>
                        <td className="px-4 py-3">
                          <span className={clsx('inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full', cfg.bg, cfg.color)}>
                            <Icon size={10} /> {cfg.label}
                          </span>
                        </td>
                        <td className={clsx('px-4 py-3 text-sm font-semibold', cfg.color)}>
                          {f.type === 'expense' || f.type === 'payment' ? '−' : '+'}{(f.amount / 1000000).toFixed(1)} {t.mln}
                        </td>
                        <td className="px-4 py-3 text-xs text-gray-500">{f.date}</td>
                        <td className="px-4 py-3"><Badge variant={statusCfg.variant}>{statusCfg.label}</Badge></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}

      {tab === 'employees' && (
        <div className="space-y-4">
          {mockEmployeeFinances.map(ef => {
            const user = users.find(u => u.id === ef.userId);
            const project = projects.find(p => p.id === ef.projectId);
            const progress = ef.contractAmount > 0 ? Math.round((ef.paid / ef.contractAmount) * 100) : 0;
            return (
              <Card key={ef.userId + ef.projectId}>
                <CardContent>
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <p className="font-medium text-gray-900 dark:text-white">{user?.name}</p>
                      <p className="text-xs text-gray-500">{project?.name}</p>
                    </div>
                    <div className="flex gap-6 text-sm">
                      <div className="text-right"><p className="text-gray-500 text-xs">{t.contract}</p><p className="text-gray-900 dark:text-white font-medium">{(ef.contractAmount / 1000000).toFixed(1)} {t.mln}</p></div>
                      <div className="text-right"><p className="text-gray-500 text-xs">{t.paid}</p><p className="text-emerald-600 dark:text-emerald-400 font-medium">{(ef.paid / 1000000).toFixed(1)} {t.mln}</p></div>
                      <div className="text-right"><p className="text-gray-500 text-xs">{t.balance}</p><p className="text-amber-600 dark:text-amber-400 font-medium">{(ef.balance / 1000000).toFixed(1)} {t.mln}</p></div>
                    </div>
                  </div>
                  <div className="mb-4">
                    <div className="flex justify-between text-xs text-gray-500 mb-1"><span>{t.paymentProgress}</span><span>{progress}%</span></div>
                    <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                      <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${progress}%` }} />
                    </div>
                  </div>
                  <div className="space-y-1.5">
                    {ef.payments.map(pay => (
                      <div key={pay.id} className="flex items-center justify-between text-sm p-2 bg-gray-50 dark:bg-gray-700/30 rounded-lg">
                        <span className="text-gray-600 dark:text-gray-400">{pay.description}</span>
                        <div className="flex items-center gap-4">
                          <span className="text-gray-400 text-xs">{pay.date}</span>
                          <span className="text-emerald-600 dark:text-emerald-400 font-medium">{(pay.amount / 1000000).toFixed(1)} {t.mln}</span>
                          <CheckCircle size={14} className="text-emerald-500" />
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </Layout>
  );
}
