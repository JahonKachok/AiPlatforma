import { create } from 'zustand';
import type { User, Project, Task, Document, FinancialRecord, Request, Notification } from '../types';
import { mockUsers, mockProjects, mockTasks, mockDocuments, mockFinancials, mockRequests, mockNotifications } from '../data/mockData';
import type { Language } from '../i18n/translations';
import { authService } from '../services/authService';
import { projectService } from '../services/projectService';
import { taskService } from '../services/taskService';
import { documentService } from '../services/documentService';
import { financeService } from '../services/financeService';
import { userService } from '../services/userService';
import { requestService } from '../services/requestService';
import { notificationService } from '../services/notificationService';
import { adaptUser, adaptProject, adaptTask, adaptDocument, adaptFinancialRecord, adaptRequest, adaptNotification } from '../services/adapters';

interface AppStore {
  // Auth
  authUser: User | null;
  isAuthenticated: boolean;
  apiAvailable: boolean;
  login: (email: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
  loadUser: () => Promise<void>;
  initializeData: () => Promise<void>;

  // UI
  darkMode: boolean;
  toggleDarkMode: () => void;
  sidebarOpen: boolean;
  toggleSidebar: () => void;
  language: Language;
  setLanguage: (lang: Language) => void;

  // Data
  users: User[];
  projects: Project[];
  tasks: Task[];
  documents: Document[];
  financials: FinancialRecord[];
  requests: Request[];
  notifications: Notification[];

  // Actions
  addProject: (project: Project) => void;
  updateProject: (project: Project) => void;
  deleteProject: (id: string) => void;
  addTask: (task: Task) => void;
  updateTask: (task: Task) => void;
  deleteTask: (id: string) => void;
  addDocument: (doc: Document) => void;
  updateDocument: (doc: Document) => void;
  markNotificationRead: (id: string) => void;
  markAllNotificationsRead: () => void;
  addRequest: (req: Request) => void;
  updateRequest: (req: Request) => void;
  refreshNotifications: () => Promise<void>;
}

const storedToken = localStorage.getItem('access_token');

export const useStore = create<AppStore>((set, get) => ({
  authUser: null,
  isAuthenticated: !!storedToken,
  apiAvailable: false,

  login: async (email: string, password: string) => {
    try {
      const data = await authService.login(email, password);
      localStorage.setItem('access_token', data.access_token);
      if (data.refresh_token) localStorage.setItem('refresh_token', data.refresh_token);
      set({ authUser: adaptUser(data.user), isAuthenticated: true, apiAvailable: true });
      await get().initializeData();
      return true;
    } catch {
      // Fallback to mock data when backend not available
      const user = mockUsers.find(u => u.email === email);
      if (user && email.includes('platform.uz')) {
        set({ authUser: user, isAuthenticated: true, apiAvailable: false });
        return true;
      }
      return false;
    }
  },

  logout: async () => {
    const refreshToken = localStorage.getItem('refresh_token');
    try {
      if (refreshToken) await authService.logout(refreshToken);
    } catch { /* ignore */ }
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    set({ authUser: null, isAuthenticated: false, apiAvailable: false });
  },

  loadUser: async () => {
    if (!localStorage.getItem('access_token')) return;
    try {
      const user = await authService.getMe();
      set({ authUser: adaptUser(user), isAuthenticated: true, apiAvailable: true });
      await get().initializeData();
    } catch {
      localStorage.removeItem('access_token');
      set({ isAuthenticated: false, apiAvailable: false });
    }
  },

  initializeData: async () => {
    try {
      const [projects, tasks, users, documents, financials, requests, notifications] = await Promise.all([
        projectService.getProjects().catch(() => null),
        taskService.getTasks().catch(() => null),
        userService.getUsers().catch(() => null),
        documentService.getDocuments().catch(() => null),
        financeService.getRecords().catch(() => null),
        requestService.getRequests().catch(() => null),
        notificationService.getNotifications().catch(() => null),
      ]);
      set({
        ...(projects && { projects: projects.map(adaptProject) }),
        ...(tasks && { tasks: tasks.map(adaptTask) }),
        ...(users && { users: users.map(adaptUser) }),
        ...(documents && { documents: documents.map(adaptDocument) }),
        ...(financials && { financials: financials.map(adaptFinancialRecord) }),
        ...(requests && { requests: requests.map(adaptRequest) }),
        ...(notifications && { notifications: notifications.map(adaptNotification) }),
      });
    } catch { /* keep mock data */ }
  },

  refreshNotifications: async () => {
    try {
      const notifications = await notificationService.getNotifications();
      set({ notifications: notifications.map(adaptNotification) });
    } catch { /* ignore */ }
  },

  darkMode: true,
  toggleDarkMode: () => set(s => ({ darkMode: !s.darkMode })),
  sidebarOpen: true,
  toggleSidebar: () => set(s => ({ sidebarOpen: !s.sidebarOpen })),
  language: 'ru' as Language,
  setLanguage: (lang) => set({ language: lang }),

  users: mockUsers,
  projects: mockProjects,
  tasks: mockTasks,
  documents: mockDocuments,
  financials: mockFinancials,
  requests: mockRequests,
  notifications: mockNotifications,

  addProject: (project) => set(s => ({ projects: [project, ...s.projects] })),
  updateProject: (project) => set(s => ({ projects: s.projects.map(p => p.id === project.id ? project : p) })),
  deleteProject: (id) => set(s => ({ projects: s.projects.filter(p => p.id !== id) })),

  addTask: (task) => set(s => ({ tasks: [task, ...s.tasks] })),
  updateTask: (task) => set(s => ({ tasks: s.tasks.map(t => t.id === task.id ? task : t) })),
  deleteTask: (id) => set(s => ({ tasks: s.tasks.filter(t => t.id !== id) })),

  addDocument: (doc) => set(s => ({ documents: [doc, ...s.documents] })),
  updateDocument: (doc) => set(s => ({ documents: s.documents.map(d => d.id === doc.id ? doc : d) })),

  markNotificationRead: (id) => set(s => ({
    notifications: s.notifications.map(n => n.id === id ? { ...n, isRead: true } : n)
  })),
  markAllNotificationsRead: () => set(s => ({
    notifications: s.notifications.map(n => ({ ...n, isRead: true }))
  })),

  addRequest: (req) => set(s => ({ requests: [req, ...s.requests] })),
  updateRequest: (req) => set(s => ({ requests: s.requests.map(r => r.id === req.id ? req : r) })),
}));
