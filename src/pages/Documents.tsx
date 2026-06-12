import { useState, useRef, useEffect } from 'react';
import { Layout } from '../components/layout/Layout';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Avatar } from '../components/ui/Avatar';
import { useStore } from '../store/useStore';
import { documentService } from '../services/documentService';
import { adaptDocument } from '../services/adapters';
import { FileText, Upload, Search, CheckCircle, Clock, AlertCircle, Download, Eye, History } from 'lucide-react';
import { clsx } from 'clsx';
import { translations } from '../i18n/translations';
import type { Document } from '../types';

function formatSize(bytes: number) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes / 1024).toFixed(0) + ' KB';
  return (bytes / 1048576).toFixed(1) + ' MB';
}

function getFileIcon(type: string) {
  const icons: Record<string, string> = { PDF: '📕', DWG: '📐', DOCX: '📄', XLSX: '📊', default: '📎' };
  return icons[type] || icons.default;
}

const inputCls = "w-full bg-gray-100 border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-700 focus:outline-none focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200";
const searchCls = "w-full bg-gray-100 border border-gray-200 rounded-lg pl-9 pr-4 py-2 text-sm text-gray-700 placeholder-gray-400 focus:outline-none focus:border-blue-500 dark:bg-gray-800 dark:border-gray-700 dark:text-gray-300 dark:placeholder-gray-600";

const DOC_TYPES = ['PDF', 'DWG', 'DOCX', 'XLSX', 'OTHER'];

export default function Documents() {
  const { documents, projects, users, language, addDocument, authUser } = useStore();
  const t = translations[language].documents;
  const tc = translations[language].common;

  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null);

  const [showUpload, setShowUpload] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadForm, setUploadForm] = useState({
    name: '', docType: 'PDF', projectId: '', version: '1.0', deadline: '', file: null as File | null,
  });
  const fileInputRef = useRef<HTMLInputElement>(null);

  interface AuditEntry { id: string; action: string; user_id?: string; details?: Record<string, unknown>; created_at: string }
  const [auditLog, setAuditLog] = useState<AuditEntry[]>([]);
  const [showJournal, setShowJournal] = useState(false);

  useEffect(() => {
    if (selectedDoc && showJournal) {
      documentService.getAudit(selectedDoc.id).then(setAuditLog).catch(() => setAuditLog([]));
    }
  }, [selectedDoc, showJournal]);

  const resetUpload = () => {
    setUploadForm({ name: '', docType: 'PDF', projectId: '', version: '1.0', deadline: '', file: null });
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const ext = file.name.split('.').pop()?.toUpperCase() || 'OTHER';
    const docType = DOC_TYPES.includes(ext) ? ext : 'OTHER';
    setUploadForm(f => ({ ...f, file, name: file.name.replace(/\.[^.]+$/, ''), docType }));
  };

  const handleUpload = async () => {
    if (!uploadForm.name || !uploadForm.file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', uploadForm.file);
      fd.append('name', uploadForm.name);
      fd.append('doc_type', uploadForm.docType);
      if (uploadForm.projectId) fd.append('project_id', uploadForm.projectId);
      fd.append('version', uploadForm.version);
      if (uploadForm.deadline) fd.append('deadline', uploadForm.deadline);
      const result = await documentService.uploadDocument(fd);
      addDocument(adaptDocument(result));
    } catch {
      const newDoc: Document = {
        id: `doc-${Date.now()}`,
        name: uploadForm.name,
        projectId: uploadForm.projectId,
        type: uploadForm.docType,
        size: uploadForm.file!.size,
        version: uploadForm.version,
        status: 'draft',
        uploadedBy: authUser?.id || 'local',
        uploadedAt: new Date().toISOString().split('T')[0],
        deadline: uploadForm.deadline || undefined,
        approvals: [],
      };
      addDocument(newDoc);
    } finally {
      setUploading(false);
      setShowUpload(false);
      resetUpload();
    }
  };

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
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder={t.searchPlaceholder} className={searchCls} />
        </div>
        <div className="flex gap-2 flex-wrap">
          {['all', ...Object.keys(statusConfig)].map(s => (
            <button key={s} onClick={() => setStatusFilter(s)}
              className={`px-3 py-2 text-sm rounded-lg transition-colors ${statusFilter === s ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700'}`}>
              {s === 'all' ? t.all : statusConfig[s as keyof typeof statusConfig].label}
            </button>
          ))}
        </div>
        <Button variant="primary" icon={<Upload size={16} />} onClick={() => setShowUpload(true)}>{t.upload}</Button>
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
                        <button onClick={() => window.open(documentService.getDownloadUrl(doc.id), '_blank')} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-700 transition-colors dark:hover:bg-gray-700 dark:hover:text-gray-300" title={t.download}>
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

      {/* Upload modal */}
      {showUpload && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60" onClick={() => { setShowUpload(false); resetUpload(); }} />
          <div className="relative w-full max-w-lg bg-white border border-gray-200 rounded-2xl shadow-2xl dark:bg-gray-800 dark:border-gray-700">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-base font-semibold text-gray-900 dark:text-white">{t.uploadTitle}</h2>
              <button onClick={() => { setShowUpload(false); resetUpload(); }} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-700 dark:hover:bg-gray-700 dark:hover:text-white">✕</button>
            </div>
            <div className="px-6 py-4 space-y-4">
              <div>
                <input ref={fileInputRef} type="file" id="doc-file-input"
                  accept=".pdf,.dwg,.docx,.xlsx,.doc,.xls,.zip"
                  onChange={handleFileChange} className="hidden" />
                <label htmlFor="doc-file-input"
                  className="block w-full border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-xl p-6 text-center cursor-pointer hover:border-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/10 transition-colors">
                  {uploadForm.file ? (
                    <div>
                      <p className="text-sm font-medium text-gray-700 dark:text-gray-200">{uploadForm.file.name}</p>
                      <p className="text-xs text-gray-500 mt-1">{formatSize(uploadForm.file.size)}</p>
                    </div>
                  ) : (
                    <div>
                      <Upload size={24} className="mx-auto mb-2 text-gray-400" />
                      <p className="text-sm text-gray-500">{t.upload}</p>
                    </div>
                  )}
                </label>
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1.5">{t.docNameLabel}</label>
                <input value={uploadForm.name} onChange={e => setUploadForm(f => ({ ...f, name: e.target.value }))} className={inputCls} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-gray-500 mb-1.5">{t.docTypeLabel}</label>
                  <select value={uploadForm.docType} onChange={e => setUploadForm(f => ({ ...f, docType: e.target.value }))} className={inputCls}>
                    {DOC_TYPES.map(type => <option key={type} value={type}>{type}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1.5">{t.versionColumn}</label>
                  <input value={uploadForm.version} onChange={e => setUploadForm(f => ({ ...f, version: e.target.value }))} placeholder="1.0" className={inputCls} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-gray-500 mb-1.5">{t.projectColumn}</label>
                  <select value={uploadForm.projectId} onChange={e => setUploadForm(f => ({ ...f, projectId: e.target.value }))} className={inputCls}>
                    <option value="">— {t.all} —</option>
                    {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1.5">{t.deadlineLabel}</label>
                  <input type="date" value={uploadForm.deadline} onChange={e => setUploadForm(f => ({ ...f, deadline: e.target.value }))} className={inputCls} />
                </div>
              </div>
            </div>
            <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
              <Button onClick={() => { setShowUpload(false); resetUpload(); }}>{tc.cancel}</Button>
              <Button variant="primary" icon={<Upload size={16} />}
                onClick={handleUpload}
                disabled={!uploadForm.file || !uploadForm.name || uploading}
                loading={uploading}>
                {t.upload}
              </Button>
            </div>
          </div>
        </div>
      )}

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
                  <p className="text-xs text-gray-500">
                    v{selectedDoc.version} · {formatSize(selectedDoc.size)}
                    {selectedDoc.deadline && <> · {t.deadlineLabel}: {String(selectedDoc.deadline).split('T')[0]}</>}
                  </p>
                </div>
              </div>
              <button onClick={() => { setSelectedDoc(null); setShowJournal(false); }} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-700 transition-colors dark:hover:bg-gray-700 dark:hover:text-white">✕</button>
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

              {showJournal && (
                <div className="mt-4">
                  <h3 className="text-sm font-semibold text-gray-500 mb-3">{t.journalTitle}</h3>
                  {auditLog.length === 0 ? (
                    <p className="text-xs text-gray-400">{t.journalEmpty}</p>
                  ) : (
                    <div className="space-y-1.5 max-h-48 overflow-y-auto">
                      {auditLog.map(entry => {
                        const actor = users.find(u => u.id === entry.user_id);
                        return (
                          <div key={entry.id} className="flex items-center gap-3 px-3 py-2 bg-gray-50 dark:bg-gray-700/30 rounded-lg">
                            <History size={12} className="text-gray-400 flex-shrink-0" />
                            <div className="flex-1 min-w-0">
                              <p className="text-xs text-gray-700 dark:text-gray-300">
                                <span className="font-medium">{entry.action}</span>
                                {actor && <span className="text-gray-500"> · {actor.name}</span>}
                              </p>
                            </div>
                            <span className="text-[11px] text-gray-400 flex-shrink-0">{new Date(entry.created_at).toLocaleString()}</span>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>
            <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
              <Button icon={<History size={16} />} onClick={() => setShowJournal(v => !v)}>{t.journalTitle}</Button>
              <Button icon={<Download size={16} />} onClick={() => window.open(documentService.getDownloadUrl(selectedDoc.id), '_blank')}>{t.download}</Button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
