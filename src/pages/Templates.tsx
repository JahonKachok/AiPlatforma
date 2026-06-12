import { useEffect, useState } from 'react';
import { Layout } from '../components/layout/Layout';
import { Card, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Modal } from '../components/ui/Modal';
import { Badge } from '../components/ui/Badge';
import { Plus, FileText, Trash2, Pencil, FileOutput, Download } from 'lucide-react';
import { useStore } from '../store/useStore';
import { translations } from '../i18n/translations';
import { templateService, type TemplateDto, type GenerateResult } from '../services/templateService';

const TYPE_VARIANTS: Record<string, 'info' | 'success' | 'purple' | 'warning' | 'default'> = {
  contract: 'info', act: 'success', appendix: 'purple', invoice: 'warning', other: 'default',
};

type TemplateType = TemplateDto['template_type'];
const emptyForm: { name: string; template_type: TemplateType; description: string; content: string } = {
  name: '', template_type: 'contract', description: '', content: '',
};

export default function Templates() {
  const { projects, users, language, authUser } = useStore();
  const t = translations[language].templates;
  const tCommon = translations[language].common;

  const [templates, setTemplates] = useState<TemplateDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editing, setEditing] = useState<TemplateDto | null>(null);
  const [form, setForm] = useState({ ...emptyForm });
  const [saving, setSaving] = useState(false);

  const [generateFor, setGenerateFor] = useState<TemplateDto | null>(null);
  const [genProjectId, setGenProjectId] = useState('');
  const [genEmployeeId, setGenEmployeeId] = useState('');
  const [generating, setGenerating] = useState(false);
  const [genResult, setGenResult] = useState<GenerateResult | null>(null);

  const canManage = authUser && ['admin', 'manager', 'gip'].includes(authUser.role);

  const loadTemplates = async () => {
    try {
      setTemplates(await templateService.getTemplates());
    } catch { /* backend unavailable */ }
    setLoading(false);
  };

  useEffect(() => {
    templateService.getTemplates()
      .then(data => setTemplates(data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const openCreate = () => {
    setEditing(null);
    setForm({ ...emptyForm });
    setEditorOpen(true);
  };

  const openEdit = (tpl: TemplateDto) => {
    setEditing(tpl);
    setForm({ name: tpl.name, template_type: tpl.template_type, description: tpl.description || '', content: tpl.content });
    setEditorOpen(true);
  };

  const handleSave = async () => {
    if (!form.name.trim() || !form.content.trim()) return;
    setSaving(true);
    try {
      if (editing) {
        await templateService.updateTemplate(editing.id, form);
      } else {
        await templateService.createTemplate(form);
      }
      await loadTemplates();
      setEditorOpen(false);
    } catch { /* ignore */ }
    setSaving(false);
  };

  const handleDelete = async (tpl: TemplateDto) => {
    if (!window.confirm(`${tCommon.delete}: ${tpl.name}?`)) return;
    try {
      await templateService.deleteTemplate(tpl.id);
      setTemplates(prev => prev.filter(x => x.id !== tpl.id));
    } catch { /* ignore */ }
  };

  const openGenerate = (tpl: TemplateDto) => {
    setGenerateFor(tpl);
    setGenProjectId(projects[0]?.id || '');
    setGenEmployeeId('');
    setGenResult(null);
  };

  const handleGenerate = async () => {
    if (!generateFor || !genProjectId) return;
    setGenerating(true);
    try {
      const result = await templateService.generate(generateFor.id, {
        project_id: genProjectId,
        employee_id: genEmployeeId || undefined,
      });
      setGenResult(result);
    } catch { /* ignore */ }
    setGenerating(false);
  };

  return (
    <Layout title={t.title} subtitle={t.subtitle}>
      <div className="flex justify-end mb-4">
        {canManage && (
          <Button variant="primary" icon={<Plus size={16} />} onClick={openCreate}>
            {t.newTemplate}
          </Button>
        )}
      </div>

      {loading ? (
        <p className="text-gray-500 text-sm">{tCommon.loading}</p>
      ) : templates.length === 0 ? (
        <Card><CardContent><p className="text-gray-500 text-sm py-8 text-center">{t.noTemplates}</p></CardContent></Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {templates.map(tpl => (
            <Card key={tpl.id}>
              <CardContent>
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <FileText size={18} className="text-blue-500 flex-shrink-0" />
                    <span className="font-semibold text-gray-900 dark:text-white truncate">{tpl.name}</span>
                  </div>
                  <Badge variant={TYPE_VARIANTS[tpl.template_type] || 'default'}>
                    {t.types[tpl.template_type] || tpl.template_type}
                  </Badge>
                </div>
                {tpl.description && (
                  <p className="text-xs text-gray-500 mb-3 line-clamp-2">{tpl.description}</p>
                )}
                <p className="text-xs text-gray-400 font-mono line-clamp-3 mb-4 whitespace-pre-line">{tpl.content}</p>
                <div className="flex gap-2 flex-wrap">
                  <Button size="sm" variant="primary" icon={<FileOutput size={14} />} onClick={() => openGenerate(tpl)}>
                    {t.generate}
                  </Button>
                  {canManage && (
                    <>
                      <Button size="sm" icon={<Pencil size={14} />} onClick={() => openEdit(tpl)}>{tCommon.edit}</Button>
                      <Button size="sm" variant="danger" icon={<Trash2 size={14} />} onClick={() => handleDelete(tpl)} />
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create / edit template */}
      <Modal
        open={editorOpen}
        onClose={() => setEditorOpen(false)}
        title={editing ? `${tCommon.edit}: ${editing.name}` : t.newTemplate}
        size="lg"
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setEditorOpen(false)}>{tCommon.cancel}</Button>
            <Button variant="primary" loading={saving} onClick={handleSave}>{tCommon.save}</Button>
          </div>
        }
      >
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1">{t.nameLabel} *</label>
              <input
                value={form.name}
                onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">{t.typeLabel}</label>
              <select
                value={form.template_type}
                onChange={e => setForm(f => ({ ...f, template_type: e.target.value as TemplateType }))}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
              >
                {Object.entries(t.types).map(([key, label]) => (
                  <option key={key} value={key}>{label}</option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">{t.descriptionLabel}</label>
            <input
              value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">{t.contentLabel} *</label>
            <textarea
              value={form.content}
              onChange={e => setForm(f => ({ ...f, content: e.target.value }))}
              rows={12}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-blue-500"
            />
            <p className="text-[11px] text-gray-500 mt-1">{t.placeholdersHint}</p>
          </div>
        </div>
      </Modal>

      {/* Generate document */}
      <Modal
        open={!!generateFor}
        onClose={() => setGenerateFor(null)}
        title={t.generateTitle}
        size="lg"
        footer={
          <div className="flex justify-end gap-2">
            <Button onClick={() => setGenerateFor(null)}>{tCommon.close}</Button>
            {genResult ? (
              <a href={templateService.getGeneratedDownloadUrl(genResult.download_url)} download>
                <Button variant="primary" icon={<Download size={14} />}>{t.download}</Button>
              </a>
            ) : (
              <Button variant="primary" loading={generating} onClick={handleGenerate} disabled={!genProjectId}>
                {t.generate}
              </Button>
            )}
          </div>
        }
      >
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-400 mb-1">{t.projectLabel} *</label>
              <select
                value={genProjectId}
                onChange={e => { setGenProjectId(e.target.value); setGenResult(null); }}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
              >
                {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">{t.employeeLabel}</label>
              <select
                value={genEmployeeId}
                onChange={e => { setGenEmployeeId(e.target.value); setGenResult(null); }}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
              >
                <option value="">—</option>
                {users.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}
              </select>
            </div>
          </div>
          {genResult && (
            <div>
              <p className="text-xs text-emerald-400 mb-2">{t.created}</p>
              <pre className="bg-gray-900 border border-gray-700 rounded-lg p-4 text-xs text-gray-300 whitespace-pre-wrap max-h-72 overflow-y-auto">
                {genResult.rendered_text}
              </pre>
            </div>
          )}
        </div>
      </Modal>
    </Layout>
  );
}
