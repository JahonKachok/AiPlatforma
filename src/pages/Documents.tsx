import { useState } from 'react';
import { Layout } from '../components/layout/Layout';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Avatar } from '../components/ui/Avatar';
import { useStore } from '../store/useStore';
import { FileText, Upload, Search, CheckCircle, Clock, AlertCircle, Download, Eye } from 'lucide-react';
import { clsx } from 'clsx';
import { translations } from '../i18n/translations';

function formatSize(bytes: number) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes / 1024).toFixed(0) + ' KB';
  return (bytes / 1048576).toFixed(1) + ' MB';
}

function getFileIcon(type: string) {
  const icons: Record<string, string> = { PDF: '📕', DWG: '📐', DOCX: '📄', XLSX: '📊', default: '📎' };
  return icons[type] || icons.default;
}

const inputCls = "w-full bg-gray-100 border border-gray-200 rounded-lg pl-9 pr-4 py-2 text-sm text-gray-700 placeholder-gray-400 focus:outline-none focus:border-blue-500 dark:bg-gray-800 dark:border-gray-700 dark:text-gray-300 dark:placeholder-gray-600";

export default function Documents() {
  const { documents, projects, users, language } = useStore();
  const t = translations[language].documents;
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedDoc, setSelectedDoc] = useState<typeof documents[0] | null>(null);

  const statusConfig = {
    draft: { label: t.draft, color: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300', icon: FileText },
    review: { label: t.review, color: 'bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-900/50 dark:text-amber-400 dark:border-amber-800', icon: Clock },
    approved: { label: t.approved, color: 'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-900/50 dark:text-emerald-400 dark:border-emerald-800', icon: CheckCircle },
    rejected: { label: t.rejected, color: 'bg-red-50 text-red-700 border border-red-200 dark:bg-red-900/50 dark:text-red-400 dark:border-red-800', icon: AlertCircle },
    archived: { label: t.archived, color: 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-500', icon: FileText },
  };

  const approvalStatusConfig = {
    pending: { label: t.pending, color: 'text-gray-500' },
    approved: { label: t.approved, color: 'text-emerald-600 dark:text-emerald-400' },
    rejected: { label: t.rejected, color: 'text-red-600 dark:text-red-400' },
    revision: { label: t.revision, color: 'text-amber-600 dark:text-amber-400' },
  };

  const filtered = documents.filter(d => {
    const ms = search === '' || d.name.toLowerCase().includes(search.toLowerCase());
    const mst = statusFilter === 'all' || d.status === statusFilter;
    return ms && mst;
  });

  const stats = Object.entries(statusConfig).map(([key, cfg]) => ({
    key, label: cfg.label, count: documents.filter(d => d.status === key).length,
  }));

  const thCls = "px-4 py-3 text-left text-xs text-gray-500 font-medium";
  const rowCls = "border-b border-gray-100 hover:bg-gray-50 transition-colors dark:border-gray-800 dark:hover:bg-gray-800/50";

  return (
    <Layout title={t.title} subtitle={t.subtitle}>
      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-3 mb-6">
        <div className="bg-white border border-gray-200 rounded-xl p-4 dark:bg-gray-800 dark:border-gray-700">
          <p className="text-2xl font-bold text-gray-900 dark:text-white">{documents.length}</p>
          <p className="text-xs text-gray-500 mt-1">{t.totalDocs}</p>
        </div>
        {stats.map(({ key, label, count }) => (
          <div key={key} className="bg-white border border-gray-200 rounded-xl p-4 dark:bg-gray-800 dark:border-gray-700">
            <p className="text-2xl font-bold text-gray-900 dark:text-white">{count}</p>
            <p className="text-xs text-gray-500 mt-1">{label}</p>
          </div>
        ))}
      </div>

      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <div className="relative flex-1 min-w-48">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500" />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder={t.searchPlaceholder} className={inputCls} />
        </div>
        <div className="flex gap-2 flex-wrap">
          {['all', ...Object.keys(statusConfig)].map(s => (
            <button key={s} onClick={() => setStatusFilter(s)}
              className={`px-3 py-2 text-sm rounded-lg transition-colors ${statusFilter === s ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700'}`}>
              {s === 'all' ? t.all : statusConfig[s as keyof typeof statusConfig].label}
            </button>
          ))}
        </div>
        <Button variant="primary" icon={<Upload size={16} />}>{t.upload}</Button>
      </div>

      {/* Table */}
      <Card>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700">
                {[t.docColumn, t.projectColumn, t.versionColumn, t.sizeColumn, t.uploaderColumn, t.dateColumn, t.statusColumn, ''].map(h => (
                  <th key={h} className={thCls}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(doc => {
                const project = projects.find(p => p.id === doc.projectId);
                const uploader = users.find(u => u.id === doc.uploadedBy);
                const StatusIcon = statusConfig[doc.status].icon;
                return (
                  <tr key={doc.id} className={rowCls}>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className="text-lg">{getFileIcon(doc.type)}</span>
                        <div>
                          <p className="text-sm text-gray-800 dark:text-gray-200 max-w-xs truncate">{doc.name}</p>
                          <p className="text-xs text-gray-400">{doc.type}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500 max-w-32 truncate">{project?.name}</td>
                    <td className="px-4 py-3 text-xs text-gray-500">v{doc.version}</td>
                    <td className="px-4 py-3 text-xs text-gray-500">{formatSize(doc.size)}</td>
                    <td className="px-4 py-3">
                      {uploader && <div className="flex items-center gap-1.5"><Avatar name={uploader.name} size="xs" /><span className="text-xs text-gray-500 hidden lg:inline">{uploader.name.split(' ')[0]}</span></div>}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">{doc.uploadedAt}</td>
                    <td className="px-4 py-3">
                      <span className={clsx('inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium', statusConfig[doc.status].color)}>
                        <StatusIcon size={10} /> {statusConfig[doc.status].label}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <button onClick={() => setSelectedDoc(doc)} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-700 transition-colors dark:hover:bg-gray-700 dark:hover:text-gray-300" title={t.download}>
                          <Eye size={14} />
                        </button>
                        <button className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-700 transition-colors dark:hover:bg-gray-700 dark:hover:text-gray-300" title={t.download}>
                          <Download size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {filtered.length === 0 && (
            <div className="text-center py-16 text-gray-400">
              <FileText size={40} className="mx-auto mb-3 opacity-30" />
              <p>{t.notFound}</p>
            </div>
          )}
        </div>
      </Card>

      {/* Document detail modal */}
      {selectedDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60" onClick={() => setSelectedDoc(null)} />
          <div className="relative w-full max-w-2xl bg-white border border-gray-200 rounded-2xl shadow-2xl overflow-hidden dark:bg-gray-800 dark:border-gray-700">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-2">
                <span className="text-2xl">{getFileIcon(selectedDoc.type)}</span>
                <div>
                  <h2 className="text-base font-semibold text-gray-900 dark:text-white">{selectedDoc.name}</h2>
                  <p className="text-xs text-gray-500">v{selectedDoc.version} · {formatSize(selectedDoc.size)}</p>
                </div>
              </div>
              <button onClick={() => setSelectedDoc(null)} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-700 transition-colors dark:hover:bg-gray-700 dark:hover:text-white">✕</button>
            </div>
            <div className="px-6 py-4">
              <h3 className="text-sm font-semibold text-gray-500 mb-3">{t.approvalRoute}</h3>
              <div className="space-y-2">
                {selectedDoc.approvals.map((ap, i) => {
                  const approver = users.find(u => u.id === ap.userId);
                  const cfg = approvalStatusConfig[ap.status];
                  return (
                    <div key={ap.id} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg dark:bg-gray-700/30">
                      <div className="w-6 h-6 rounded-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center text-xs text-gray-600 dark:text-gray-400 flex-shrink-0">{i + 1}</div>
                      <div className="flex-1">
                        <p className="text-sm text-gray-700 dark:text-gray-300">{ap.stageName}</p>
                        {approver && <p className="text-xs text-gray-500">{approver.name}</p>}
                      </div>
                      <div className="text-right">
                        <p className={clsx('text-xs font-medium', cfg.color)}>{cfg.label}</p>
                        {ap.updatedAt && <p className="text-xs text-gray-400">{ap.updatedAt}</p>}
                      </div>
                      {ap.status === 'approved' && <CheckCircle size={16} className="text-emerald-500 flex-shrink-0" />}
                      {ap.status === 'pending' && ap.stage === selectedDoc.approvalStage && <Clock size={16} className="text-amber-500 flex-shrink-0" />}
                    </div>
                  );
                })}
              </div>
            </div>
            <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
              <Button icon={<Download size={16} />}>{t.download}</Button>
              <Button variant="primary" icon={<CheckCircle size={16} />}>{t.approve}</Button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
