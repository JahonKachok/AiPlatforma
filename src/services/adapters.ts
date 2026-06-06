// Transform API snake_case responses to frontend camelCase types

import type { User, Project, Task, Document, FinancialRecord, Request, Notification } from '../types'
import { BASE_UPLOAD_URL } from './api'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function adaptUser(u: any): User {
  return {
    id: u.id,
    name: u.full_name ?? u.name ?? '',
    email: u.email,
    role: u.role,
    avatar: u.avatar_url ? `${BASE_UPLOAD_URL}${u.avatar_url}` : u.avatar,
    department: u.department,
    phone: u.phone,
    isActive: u.is_active ?? u.isActive ?? true,
    createdAt: u.created_at ?? u.createdAt ?? new Date().toISOString(),
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function adaptProject(p: any): Project {
  return {
    id: p.id,
    name: p.name,
    client: p.client_name ?? p.client ?? '',
    address: p.address ?? '',
    stage: p.stage,
    status: p.status === 'on_hold' ? 'paused' : p.status,
    deadline: p.deadline ?? p.createdAt ?? '',
    startDate: p.start_date ?? p.startDate ?? '',
    gipId: p.gip_id ?? p.gipId ?? '',
    budget: p.budget ?? 0,
    paid: p.paid_amount ?? p.paid ?? 0,
    participants: (p.members ?? []).map((m: { user_id?: string; userId?: string }) => m.user_id ?? m.userId ?? ''),
    description: p.description,
    sections: (p.sections ?? []).map(adaptSection),
    objects: (p.sub_objects ?? p.objects ?? []).map(adaptSubObject),
    priority: p.priority ?? 'medium',
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function adaptSection(s: any) {
  return {
    id: s.id,
    projectId: s.project_id ?? s.projectId ?? '',
    name: s.name,
    code: s.code ?? '',
    gipId: s.gip_id ?? s.gipId,
    deadline: s.deadline,
    status: s.status === 'not_started' ? 'active' : s.status,
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function adaptSubObject(o: any) {
  return {
    id: o.id,
    projectId: o.project_id ?? o.projectId ?? '',
    name: o.name,
    address: o.address,
    gipId: o.gip_id ?? o.gipId,
    status: o.status ?? 'active',
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function adaptTask(t: any): Task {
  return {
    id: t.id,
    title: t.title,
    description: t.description ?? '',
    projectId: t.project_id ?? t.projectId ?? '',
    sectionId: t.section_id ?? t.sectionId,
    assigneeId: t.assignee_id ?? t.assigneeId ?? '',
    creatorId: t.creator_id ?? t.creatorId ?? '',
    status: t.status,
    priority: t.priority,
    deadline: t.deadline ?? '',
    createdAt: t.created_at ?? t.createdAt ?? '',
    updatedAt: t.updated_at ?? t.updatedAt ?? '',
    attachments: (t.attachments ?? []).map((a: {
      id: string; filename?: string; name?: string;
      file_size?: number; size?: number; mime_type?: string; type?: string;
      file_path?: string; url?: string; user_id?: string; uploadedBy?: string;
      created_at?: string; uploadedAt?: string;
    }) => ({
      id: a.id,
      name: a.filename ?? a.name ?? '',
      size: a.file_size ?? a.size ?? 0,
      type: a.mime_type ?? a.type ?? '',
      url: a.file_path ? `${BASE_UPLOAD_URL}/${a.file_path}` : (a.url ?? ''),
      uploadedBy: a.user_id ?? a.uploadedBy ?? '',
      uploadedAt: a.created_at ?? a.uploadedAt ?? '',
    })),
    comments: (t.comments ?? []).map((c: {
      id: string; user_id?: string; userId?: string;
      content?: string; text?: string; created_at?: string; createdAt?: string;
    }) => ({
      id: c.id,
      userId: c.user_id ?? c.userId ?? '',
      text: c.content ?? c.text ?? '',
      createdAt: c.created_at ?? c.createdAt ?? '',
    })),
    tags: t.tags,
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function adaptDocument(d: any): Document {
  const approvals = (d.approval_stages ?? d.approvals ?? []).map((a: {
    id: string; stage_order?: number; stage?: number;
    stage_name?: string; stageName?: string; reviewer_id?: string; userId?: string;
    status: string; comment?: string; reviewed_at?: string; updatedAt?: string;
  }) => ({
    id: a.id,
    stage: a.stage_order ?? a.stage ?? 0,
    stageName: a.stage_name ?? a.stageName ?? '',
    userId: a.reviewer_id ?? a.userId ?? '',
    status: a.status,
    comment: a.comment,
    updatedAt: a.reviewed_at ?? a.updatedAt,
  }));
  // The backend doesn't send a "current stage" number — derive it as the
  // first stage still awaiting review (or the last stage once all are done).
  const pendingStage = approvals.find((a: { status: string }) => a.status === 'pending');
  const approvalStage = d.approval_stage ?? d.approvalStage ??
    pendingStage?.stage ?? approvals[approvals.length - 1]?.stage ?? 1;
  return {
    id: d.id,
    name: d.name,
    projectId: d.project_id ?? d.projectId ?? '',
    sectionId: d.section_id ?? d.sectionId,
    type: d.doc_type ?? d.type ?? '',
    size: d.file_size ?? d.size ?? 0,
    version: d.version ?? '1.0',
    status: d.status,
    uploadedBy: d.uploaded_by ?? d.uploadedBy ?? '',
    uploadedAt: d.created_at ?? d.uploadedAt ?? '',
    approvalStage,
    approvals,
    tags: d.tags,
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function adaptFinancialRecord(r: any): FinancialRecord {
  return {
    id: r.id,
    projectId: r.project_id ?? r.projectId ?? '',
    type: r.type,
    amount: r.amount ?? 0,
    description: r.description ?? '',
    date: r.date ?? r.created_at ?? '',
    category: r.category ?? '',
    userId: r.created_by ?? r.userId,
    status: r.status === 'confirmed' ? 'paid' : r.status === 'cancelled' ? 'overdue' : 'pending',
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function adaptRequest(r: any): Request {
  return {
    id: r.id,
    title: r.title,
    description: r.description ?? '',
    projectId: r.project_id ?? r.projectId,
    creatorId: r.created_by ?? r.creatorId ?? '',
    assigneeId: r.assignee_id ?? r.assigneeId,
    status: r.status === 'open' ? 'discussion' : r.status === 'in_progress' ? 'clarification' : r.status === 'resolved' ? 'completed' : 'discussion',
    priority: r.priority,
    createdAt: r.created_at ?? r.createdAt ?? '',
    comments: (r.comments ?? []).map((c: {
      id: string; user_id?: string; userId?: string;
      content?: string; text?: string; created_at?: string; createdAt?: string;
    }) => ({
      id: c.id,
      userId: c.user_id ?? c.userId ?? '',
      text: c.content ?? c.text ?? '',
      createdAt: c.created_at ?? c.createdAt ?? '',
    })),
  }
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function adaptNotification(n: any): Notification {
  return {
    id: n.id,
    userId: n.user_id ?? n.userId ?? '',
    type: n.type,
    title: n.title,
    message: n.message,
    isRead: n.is_read ?? n.isRead ?? false,
    createdAt: n.created_at ?? n.createdAt ?? '',
    link: n.link,
  }
}
