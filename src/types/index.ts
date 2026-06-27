export type UserRole = 'admin' | 'manager' | 'gip' | 'gip_assistant' | 'designer' | 'reviewer' | 'client';

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  avatar?: string;
  department?: string;
  phone?: string;
  telegram_chat_id?: string | null;
  isActive: boolean;
  createdAt: string;
}

export type ProjectStatus = 'active' | 'completed' | 'paused' | 'cancelled' | 'planning';

export type ProjectStage = 'concept' | 'preliminary' | 'working_docs' | 'expertise' | 'construction';

export interface Project {
  id: string;
  name: string;
  client: string;
  address: string;
  stage: ProjectStage;
  status: ProjectStatus;
  deadline: string;
  startDate: string;
  gipId: string;
  budget: number;
  paid: number;
  participants: string[];
  description?: string;
  sections: Section[];
  objects: SubObject[];
  priority: 'low' | 'medium' | 'high' | 'critical';
}

export interface Section {
  id: string;
  projectId: string;
  name: string;
  code: string;
  gipId?: string;
  deadline?: string;
  status: 'active' | 'completed' | 'paused';
}

export interface SubObject {
  id: string;
  projectId: string;
  name: string;
  address?: string;
  gipId?: string;
  status: ProjectStatus;
}

export type TaskStatus = 'new' | 'in_progress' | 'review' | 'revision' | 'approved' | 'completed';
export type TaskPriority = 'low' | 'medium' | 'high' | 'critical';

export interface Task {
  id: string;
  title: string;
  description: string;
  projectId: string;
  sectionId?: string;
  assigneeId: string;
  creatorId: string;
  status: TaskStatus;
  priority: TaskPriority;
  deadline: string;
  createdAt: string;
  updatedAt: string;
  attachments: Attachment[];
  comments: Comment[];
  tags?: string[];
}

export interface Comment {
  id: string;
  userId: string;
  text: string;
  createdAt: string;
}

export interface Attachment {
  id: string;
  name: string;
  size: number;
  type: string;
  url: string;
  uploadedBy: string;
  uploadedAt: string;
}

export type DocumentStatus = 'draft' | 'review' | 'approved' | 'rejected' | 'archived';

export interface Document {
  id: string;
  name: string;
  projectId: string;
  sectionId?: string;
  type: string;
  size: number;
  version: string;
  status: DocumentStatus;
  uploadedBy: string;
  uploadedAt: string;
  deadline?: string;
  approvalStage?: number;
  approvals: ApprovalStep[];
  tags?: string[];
}

export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'revision';

export interface ApprovalStep {
  id: string;
  stage: number;
  stageName: string;
  userId: string;
  status: ApprovalStatus;
  comment?: string;
  updatedAt?: string;
}

export interface FinancialRecord {
  id: string;
  projectId: string;
  type: 'income' | 'expense' | 'advance' | 'payment';
  amount: number;
  description: string;
  date: string;
  category: string;
  userId?: string;
  status: 'pending' | 'paid' | 'overdue';
}

export interface EmployeeFinance {
  userId: string;
  projectId: string;
  contractAmount: number;
  paid: number;
  balance: number;
  payments: Payment[];
}

export interface Payment {
  id: string;
  amount: number;
  date: string;
  description: string;
}

export interface Request {
  id: string;
  title: string;
  description: string;
  projectId?: string;
  creatorId: string;
  assigneeId?: string;
  status: 'discussion' | 'clarification' | 'approval' | 'completed';
  priority: TaskPriority;
  createdAt: string;
  comments: Comment[];
}

export interface Notification {
  id: string;
  userId: string;
  type: 'task' | 'deadline' | 'approval' | 'comment' | 'finance' | 'document';
  title: string;
  message: string;
  isRead: boolean;
  createdAt: string;
  link?: string;
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
}
