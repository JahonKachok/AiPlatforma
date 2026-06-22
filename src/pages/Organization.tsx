import { useState, useEffect } from 'react';
import { Layout } from '../components/layout/Layout';
import { Card, CardHeader, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Avatar } from '../components/ui/Avatar';
import { Badge } from '../components/ui/Badge';
import { useStore } from '../store/useStore';
import { organizationService } from '../services/organizationService';
import { translations } from '../i18n/translations';
import { Building2, Users, Layers, Plus, Edit2, Trash2, Search } from 'lucide-react';
import { clsx } from 'clsx';

const inputCls = "w-full bg-gray-100 border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-700 focus:outline-none focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200";

interface Department {
  id: string;
  name: string;
  code?: string;
  description?: string;
  head_id?: string;
  status: 'active' | 'inactive' | 'archived';
  units: Unit[];
}

interface Unit {
  id: string;
  department_id: string;
  name: string;
  code?: string;
  manager_id?: string;
  level: number;
  members: Member[];
}

interface Member {
  id: string;
  unit_id: string;
  user_id: string;
  role_in_unit?: string;
  manager_id?: string;
  is_primary: boolean;
}

export default function Organization() {
  const { users, language } = useStore();
  const t = translations[language].organization;
  const tc = translations[language].common;

  const [departments, setDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [activeTab, setActiveTab] = useState<'hierarchy' | 'list'>('hierarchy');
  const [showNewDeptForm, setShowNewDeptForm] = useState(false);
  const [newDept, setNewDept] = useState({ name: '', code: '', description: '' });

  useEffect(() => {
    loadDepartments();
  }, []);

  const loadDepartments = async () => {
    try {
      setLoading(true);
      const data = await organizationService.getDepartments();
      setDepartments(data);
    } catch (error) {
      console.error('Failed to load departments:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateDepartment = async () => {
    if (!newDept.name.trim()) return;
    try {
      await organizationService.createDepartment(newDept);
      setNewDept({ name: '', code: '', description: '' });
      setShowNewDeptForm(false);
      await loadDepartments();
    } catch (error) {
      console.error('Failed to create department:', error);
    }
  };

  const handleDeleteDepartment = async (id: string) => {
    if (!window.confirm(t.deleteSuccess)) return;
    try {
      await organizationService.deleteDepartment(id);
      await loadDepartments();
    } catch (error) {
      console.error('Failed to delete department:', error);
    }
  };

  const filteredDepts = departments.filter(d =>
    d.name.toLowerCase().includes(search.toLowerCase()) ||
    (d.code && d.code.toLowerCase().includes(search.toLowerCase()))
  );

  const statusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-900/50 dark:text-emerald-400 dark:border-emerald-800';
      case 'inactive':
        return 'bg-gray-50 text-gray-700 border border-gray-200 dark:bg-gray-700/50 dark:text-gray-400 dark:border-gray-600';
      case 'archived':
        return 'bg-red-50 text-red-700 border border-red-200 dark:bg-red-900/50 dark:text-red-400 dark:border-red-800';
      default:
        return '';
    }
  };

  return (
    <Layout title={t.title} subtitle={t.subtitle}>
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <div className="relative flex-1 min-w-48">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder={`${t.departments}...`}
            className={clsx(inputCls, 'pl-9')}
          />
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab('hierarchy')}
            className={`px-4 py-2 rounded-lg text-sm transition-colors ${
              activeTab === 'hierarchy'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700'
            }`}
          >
            {t.hierarchy}
          </button>
          <button
            onClick={() => setActiveTab('list')}
            className={`px-4 py-2 rounded-lg text-sm transition-colors ${
              activeTab === 'list'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700'
            }`}
          >
            {t.composition}
          </button>
        </div>
        <Button variant="primary" icon={<Plus size={16} />} onClick={() => setShowNewDeptForm(true)}>
          {t.newDepartment}
        </Button>
      </div>

      {/* Content */}
      {loading ? (
        <div className="text-center py-12">
          <p className="text-gray-500">{tc.loading}</p>
        </div>
      ) : activeTab === 'hierarchy' ? (
        // Hierarchy View
        <div className="space-y-6">
          {filteredDepts.length === 0 ? (
            <Card>
              <CardContent className="py-12">
                <p className="text-center text-gray-400">{t.noDepartments}</p>
              </CardContent>
            </Card>
          ) : (
            filteredDepts.map(dept => {
              const head = dept.head_id ? users.find(u => u.id === dept.head_id) : null;
              return (
                <Card key={dept.id}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <Building2 size={20} className="text-blue-600 dark:text-blue-400" />
                        <div>
                          <h3 className="text-base font-semibold text-gray-900 dark:text-white">{dept.name}</h3>
                          {dept.code && <p className="text-xs text-gray-500">Код: {dept.code}</p>}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary" size="sm">{dept.status}</Badge>
                        <Button size="sm" variant="ghost" icon={<Edit2 size={14} />} />
                        <Button
                          size="sm"
                          variant="danger"
                          icon={<Trash2 size={14} />}
                          onClick={() => handleDeleteDepartment(dept.id)}
                        />
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {dept.description && (
                      <p className="text-sm text-gray-600 dark:text-gray-400">{dept.description}</p>
                    )}

                    {head && (
                      <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800/50">
                        <p className="text-xs text-gray-500 mb-1">{t.head}</p>
                        <div className="flex items-center gap-2">
                          <Avatar name={head.name} size="sm" />
                          <span className="text-sm font-medium text-gray-700 dark:text-gray-200">{head.name}</span>
                        </div>
                      </div>
                    )}

                    {dept.units.length > 0 ? (
                      <div className="space-y-3 mt-4">
                        <p className="text-sm font-semibold text-gray-600 dark:text-gray-400">{t.units}</p>
                        {dept.units.map(unit => {
                          const manager = unit.manager_id ? users.find(u => u.id === unit.manager_id) : null;
                          return (
                            <div key={unit.id} className="p-3 bg-gray-50 dark:bg-gray-700/30 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600">
                              <div className="flex items-start justify-between">
                                <div className="flex-1">
                                  <p className="text-sm font-medium text-gray-700 dark:text-gray-200">{unit.name}</p>
                                  {unit.code && <p className="text-xs text-gray-500 mt-0.5">Код: {unit.code}</p>}
                                  {manager && (
                                    <div className="flex items-center gap-1.5 mt-2">
                                      <Avatar name={manager.name} size="xs" />
                                      <span className="text-xs text-gray-500">{manager.name}</span>
                                    </div>
                                  )}
                                </div>
                                <div className="flex gap-1">
                                  <Button size="sm" variant="ghost" icon={<Edit2 size={12} />} />
                                  <Button size="sm" variant="ghost" icon={<Trash2 size={12} />} />
                                </div>
                              </div>

                              {unit.members.length > 0 && (
                                <div className="mt-3 pt-3 border-t border-gray-200 dark:border-gray-600">
                                  <p className="text-xs font-semibold text-gray-500 mb-2">{t.members} ({unit.members.length})</p>
                                  <div className="flex flex-wrap gap-2">
                                    {unit.members.map(member => {
                                      const member_user = users.find(u => u.id === member.user_id);
                                      return member_user ? (
                                        <div
                                          key={member.id}
                                          className="flex items-center gap-1.5 px-2 py-1 bg-white dark:bg-gray-800 rounded border border-gray-200 dark:border-gray-600"
                                        >
                                          <Avatar name={member_user.name} size="xs" />
                                          <span className="text-xs text-gray-600 dark:text-gray-300">{member_user.name.split(' ')[0]}</span>
                                        </div>
                                      ) : null;
                                    })}
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <p className="text-sm text-gray-400 text-center py-4">{t.noUnits}</p>
                    )}
                  </CardContent>
                </Card>
              );
            })
          )}
        </div>
      ) : (
        // List View
        <Card>
          <CardHeader>
            <span className="font-semibold text-gray-900 dark:text-white">{t.departments}</span>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-gray-700">
                    {[t.name, t.code, t.head, t.status, t.units].map(h => (
                      <th key={h} className="px-4 py-3 text-left text-xs text-gray-500 font-medium">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filteredDepts.map(dept => {
                    const head = dept.head_id ? users.find(u => u.id === dept.head_id) : null;
                    return (
                      <tr key={dept.id} className="border-b border-gray-100 hover:bg-gray-50 transition-colors dark:border-gray-800 dark:hover:bg-gray-800/50">
                        <td className="px-4 py-3">
                          <p className="text-sm font-medium text-gray-700 dark:text-gray-200">{dept.name}</p>
                        </td>
                        <td className="px-4 py-3">
                          <p className="text-sm text-gray-500">{dept.code || '—'}</p>
                        </td>
                        <td className="px-4 py-3">
                          {head ? (
                            <div className="flex items-center gap-1.5">
                              <Avatar name={head.name} size="xs" />
                              <span className="text-xs text-gray-600 dark:text-gray-400">{head.name}</span>
                            </div>
                          ) : (
                            <p className="text-sm text-gray-400">—</p>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <span className={clsx('inline-flex px-2 py-1 rounded-full text-xs font-medium', statusColor(dept.status))}>
                            {dept.status}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className="text-sm text-gray-600 dark:text-gray-400">{dept.units.length}</span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* New Department Modal */}
      {showNewDeptForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60" onClick={() => setShowNewDeptForm(false)} />
          <div className="relative w-full max-w-md bg-white border border-gray-200 rounded-2xl shadow-2xl dark:bg-gray-800 dark:border-gray-700">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-base font-semibold text-gray-900 dark:text-white">{t.newDepartment}</h2>
              <button
                onClick={() => setShowNewDeptForm(false)}
                className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-700 transition-colors dark:hover:bg-gray-700 dark:hover:text-white"
              >
                ✕
              </button>
            </div>
            <div className="px-6 py-4 space-y-4">
              <div>
                <label className="block text-xs text-gray-500 mb-1.5">{t.deptName}</label>
                <input
                  value={newDept.name}
                  onChange={e => setNewDept(d => ({ ...d, name: e.target.value }))}
                  className={inputCls}
                  placeholder={t.deptName}
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1.5">{t.deptCode}</label>
                <input
                  value={newDept.code}
                  onChange={e => setNewDept(d => ({ ...d, code: e.target.value }))}
                  className={inputCls}
                  placeholder={t.deptCode}
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1.5">{t.description}</label>
                <textarea
                  value={newDept.description}
                  onChange={e => setNewDept(d => ({ ...d, description: e.target.value }))}
                  className={clsx(inputCls, 'resize-none')}
                  rows={3}
                  placeholder={t.description}
                />
              </div>
            </div>
            <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
              <Button onClick={() => setShowNewDeptForm(false)}>{tc.cancel}</Button>
              <Button variant="primary" onClick={handleCreateDepartment}>
                {tc.save}
              </Button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
