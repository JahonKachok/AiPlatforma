import { useState } from 'react';
import { Layout } from '../components/layout/Layout';
import { Card, CardHeader, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Avatar } from '../components/ui/Avatar';
import { useStore } from '../store/useStore';
import { CheckCircle, XCircle, Clock, AlertCircle, ChevronRight, RotateCcw } from 'lucide-react';
import { clsx } from 'clsx';
import { translations } from '../i18n/translations';
import { approvalService } from '../services/approvalService';
import { documentService } from '../services/documentService';
import { adaptDocument } from '../services/adapters';

function getFileIcon(type: string) {
  const icons: Record<string, string> = { PDF: '📕', DWG: '📐', DOCX: '📄', XLSX: '📊' };
  return icons[type] || '📎';
}

export default function Approvals() {
  const { documents, projects, users, updateDocument, language } = useStore();
  const t = translations[language].approvals;
  const [selected, setSelected] = useState<typeof documents[0] | null>(null);
  const [comment, setComment] = useState('');

  const STAGES = [
    translations[language].roles.designer,
    translations[language].roles.reviewer,
    translations[language].roles.gip,
    translations[language].roles.manager,
    translations[language].roles.client,
  ];

  const pending = documents.filter(d => d.status === 'review');
  const approved = documents.filter(d => d.status === 'approved');
  const rejected = documents.filter(d => d.status === 'rejected');

  const reviewCurrentStage = async (status: 'approved' | 'rejected' | 'revision') => {
    if (!selected) return;
    const stage = selected.approvals.find(ap => ap.stage === selected.approvalStage);
    try {
      if (!stage) throw new Error('no active stage');
      await approvalService.reviewStage(stage.id, { status, comment: comment || undefined });
      const fresh = await documentService.getDocument(selected.id);
      updateDocument(adaptDocument(fresh));
    } catch {
      // Revision sends the document back to draft for rework
      const docStatus = status === 'revision' ? 'draft' : status;
      updateDocument({
        ...selected, status: docStatus,
        approvals: selected.approvals.map(ap =>
          ap.stage === selected.approvalStage ? { ...ap, status, updatedAt: new Date().toISOString().split('T')[0], comment } : ap
        ),
      });
    }
    setSelected(null);
    setComment('');
  };

  const handleApprove = () => reviewCurrentStage('approved');
  const handleReject = () => reviewCurrentStage('rejected');
  const handleRevision = () => reviewCurrentStage('revision');

  const renderDoc = (doc: typeof documents[0]) => {
    const project = projects.find(p => p.id === doc.projectId);
    const stage = doc.approvalStage || 1;
    return (
      <div key={doc.id} onClick={() => setSelected(doc)} className="flex items-center gap-4 p-4 bg-gray-50 hover:bg-gray-100 rounded-xl cursor-pointer transition-colors border border-transparent hover:border-gray-200 dark:bg-gray-700/30 dark:hover:bg-gray-700/50 dark:hover:border-gray-600">
        <span className="text-2xl flex-shrink-0">{getFileIcon(doc.type)}</span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-800 dark:text-gray-200 truncate">{doc.name}</p>
          <p className="text-xs text-gray-500 mt-0.5">{project?.name} · v{doc.version}</p>
        </div>
        <div className="hidden md:flex items-center gap-1">
          {STAGES.map((s, i) => {
            const ap = doc.approvals[i];
            const isCurrent = i + 1 === stage;
            const isDone = ap?.status === 'approved';
            const isRejected = ap?.status === 'rejected';
            return (
              <div key={s} className="flex items-center gap-1">
                <div className={clsx(
                  'w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold border',
                  isDone ? 'bg-emerald-50 border-emerald-400 text-emerald-600 dark:bg-emerald-900/50 dark:border-emerald-600 dark:text-emerald-400' :
                  isRejected ? 'bg-red-50 border-red-400 text-red-600 dark:bg-red-900/50 dark:border-red-600 dark:text-red-400' :
                  isCurrent ? 'bg-amber-50 border-amber-400 text-amber-600 dark:bg-amber-900/50 dark:border-amber-600 dark:text-amber-400' :
                  'bg-gray-100 border-gray-300 text-gray-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-500'
                )}>
                  {isDone ? '✓' : isRejected ? '✕' : i + 1}
                </div>
                {i < STAGES.length - 1 && <div className={clsx('w-4 h-0.5', isDone ? 'bg-emerald-400' : 'bg-gray-200 dark:bg-gray-700')} />}
              </div>
            );
          })}
        </div>
        <ChevronRight size={16} className="text-gray-400 flex-shrink-0" />
      </div>
    );
  };

  return (
    <Layout title={t.title} subtitle={t.subtitle}>
      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {[
          { label: t.pending, count: pending.length, icon: Clock, color: 'text-amber-500 dark:text-amber-400', bg: 'bg-amber-100 dark:bg-amber-900/30' },
          { label: t.approvedDocs, count: approved.length, icon: CheckCircle, color: 'text-emerald-500 dark:text-emerald-400', bg: 'bg-emerald-100 dark:bg-emerald-900/30' },
          { label: t.rejectedDocs, count: rejected.length, icon: XCircle, color: 'text-red-500 dark:text-red-400', bg: 'bg-red-100 dark:bg-red-900/30' },
        ].map(({ label, count, icon: Icon, color, bg }) => (
          <Card key={label} className="p-4">
            <div className={clsx('p-2 rounded-xl w-fit mb-3', bg)}><Icon size={20} className={color} /></div>
            <p className={clsx('text-3xl font-bold', color)}>{count}</p>
            <p className="text-xs text-gray-500 mt-1">{label}</p>
          </Card>
        ))}
      </div>

      {pending.length > 0 && (
        <Card className="mb-6">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Clock size={16} className="text-amber-500" />
              <span className="font-semibold text-gray-900 dark:text-white">{t.waitingApproval}</span>
              <span className="bg-amber-50 text-amber-700 border border-amber-200 text-xs rounded-full px-2 py-0.5 dark:bg-amber-900/50 dark:text-amber-400 dark:border-amber-800">{pending.length}</span>
            </div>
          </CardHeader>
          <CardContent className="space-y-2">{pending.map(renderDoc)}</CardContent>
        </Card>
      )}

      {approved.length > 0 && (
        <Card className="mb-6">
          <CardHeader>
            <div className="flex items-center gap-2">
              <CheckCircle size={16} className="text-emerald-500" />
              <span className="font-semibold text-gray-900 dark:text-white">{t.approvedDocs}</span>
            </div>
          </CardHeader>
          <CardContent className="space-y-2">{approved.map(renderDoc)}</CardContent>
        </Card>
      )}

      {rejected.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <AlertCircle size={16} className="text-red-500" />
              <span className="font-semibold text-gray-900 dark:text-white">{t.rejectedDocs}</span>
            </div>
          </CardHeader>
          <CardContent className="space-y-2">{rejected.map(renderDoc)}</CardContent>
        </Card>
      )}

      {/* Detail modal */}
      {selected && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/60" onClick={() => setSelected(null)} />
          <div className="relative w-full max-w-2xl bg-white border border-gray-200 rounded-2xl shadow-2xl overflow-hidden dark:bg-gray-800 dark:border-gray-700">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center gap-2">
                <span className="text-2xl">{getFileIcon(selected.type)}</span>
                <div>
                  <h2 className="text-base font-semibold text-gray-900 dark:text-white">{selected.name}</h2>
                  <p className="text-xs text-gray-500">{projects.find(p => p.id === selected.projectId)?.name} · v{selected.version}</p>
                </div>
              </div>
              <button onClick={() => setSelected(null)} className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-700 transition-colors dark:hover:bg-gray-700 dark:hover:text-white">✕</button>
            </div>
            <div className="px-6 py-4">
              <h3 className="text-sm font-semibold text-gray-500 mb-3">{t.approvalStatus}</h3>
              <div className="space-y-2">
                {selected.approvals.map((ap, i) => {
                  const approver = users.find(u => u.id === ap.userId);
                  const isCurrent = i + 1 === selected.approvalStage;
                  return (
                    <div key={ap.id} className={clsx(
                      'flex items-center gap-3 p-3 rounded-xl border transition-all',
                      isCurrent ? 'bg-amber-50 border-amber-200 dark:bg-amber-900/20 dark:border-amber-800' :
                      ap.status === 'approved' ? 'bg-emerald-50 border-emerald-100 dark:bg-emerald-900/10 dark:border-emerald-900' :
                      ap.status === 'rejected' ? 'bg-red-50 border-red-100 dark:bg-red-900/10 dark:border-red-900' :
                      'bg-gray-50 border-gray-100 dark:bg-gray-700/20 dark:border-gray-700'
                    )}>
                      <div className={clsx('w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm border',
                        ap.status === 'approved' ? 'bg-emerald-100 border-emerald-400 text-emerald-600 dark:bg-emerald-900 dark:border-emerald-600 dark:text-emerald-400' :
                        ap.status === 'rejected' ? 'bg-red-100 border-red-400 text-red-600 dark:bg-red-900 dark:border-red-600 dark:text-red-400' :
                        isCurrent ? 'bg-amber-100 border-amber-400 text-amber-600 dark:bg-amber-900 dark:border-amber-600 dark:text-amber-400' :
                        'bg-gray-100 border-gray-300 text-gray-500 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-500'
                      )}>
                        {ap.status === 'approved' ? <CheckCircle size={14} /> : ap.status === 'rejected' ? <XCircle size={14} /> : i + 1}
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-gray-700 dark:text-gray-200">{ap.stageName}</p>
                        {approver && <div className="flex items-center gap-1.5 mt-0.5"><Avatar name={approver.name} size="xs" /><span className="text-xs text-gray-500">{approver.name}</span></div>}
                        {ap.comment && <p className="text-xs text-gray-400 mt-1 italic">{ap.comment}</p>}
                      </div>
                      <div className="text-right">
                        <span className={clsx('text-xs font-medium',
                          ap.status === 'approved' ? 'text-emerald-600 dark:text-emerald-400' :
                          ap.status === 'rejected' ? 'text-red-600 dark:text-red-400' :
                          isCurrent ? 'text-amber-600 dark:text-amber-400' : 'text-gray-400'
                        )}>
                          {ap.status === 'approved' ? t.approvedStatus : ap.status === 'rejected' ? t.rejectedStatus : isCurrent ? t.waiting : t.notStarted}
                        </span>
                        {ap.updatedAt && <p className="text-xs text-gray-400">{ap.updatedAt}</p>}
                      </div>
                    </div>
                  );
                })}
              </div>
              {selected.status === 'review' && (
                <div className="mt-4">
                  <label className="block text-xs text-gray-500 mb-1.5">{t.comment}</label>
                  <textarea value={comment} onChange={e => setComment(e.target.value)} rows={2} placeholder={t.commentPlaceholder}
                    className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700 focus:outline-none focus:border-blue-500 resize-none dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200" />
                </div>
              )}
            </div>
            <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
              <Button onClick={() => setSelected(null)}>{t.close}</Button>
              {selected.status === 'review' && (
                <>
                  <Button variant="danger" icon={<XCircle size={16} />} onClick={handleReject}>{t.reject}</Button>
                  <Button variant="secondary" icon={<RotateCcw size={16} />} onClick={handleRevision}>{t.revisionBtn}</Button>
                  <Button variant="primary" icon={<CheckCircle size={16} />} onClick={handleApprove}>{t.approve}</Button>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
