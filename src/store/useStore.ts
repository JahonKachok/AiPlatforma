import { create } from 'zustand';
import type { User, Project, Task, Document, FinancialRecord, Request, Notification } from '../types';
import { mockUsers, mockProjects, mockTasks, mockDocuments, mockFinancials, mockRequests, mockNotifications, currentUser } from '../data/mockData';
import type { Language } from '../i18n/translations';

interface AppStore {
  // Auth
  authUser: User | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => boolean;
  logout: () => void;

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
  addTask: (task: Task) => void;
  updateTask: (task: Task) => void;
  addDocument: (doc: Document) => void;
  updateDocument: (doc: Document) => void;
  markNotificationRead: (id: string) => void;
  markAllNotificationsRead: () => void;
  addRequest: (req: Request) => void;
  updateRequest: (req: Request) => void;
}

export const useStore = create<AppStore>((set, _get) => ({
  authUser: currentUser,
  isAuthenticated: true,
  login: (email: string, _password: string) => {
    const user = mockUsers.find(u => u.email === email);
    if (user) {
      set({ authUser: user, isAuthenticated: true });
      return true;
    }
    return false;
  },
  logout: () => set({ authUser: null, isAuthenticated: false }),

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

  addProject: (project) => set(s => ({ projects: [...s.projects, project] })),
  updateProject: (project) => set(s => ({ projects: s.projects.map(p => p.id === project.id ? project : p) })),

  addTask: (task) => set(s => ({ tasks: [...s.tasks, task] })),
  updateTask: (task) => set(s => ({ tasks: s.tasks.map(t => t.id === task.id ? task : t) })),

  addDocument: (doc) => set(s => ({ documents: [...s.documents, doc] })),
  updateDocument: (doc) => set(s => ({ documents: s.documents.map(d => d.id === doc.id ? doc : d) })),

  markNotificationRead: (id) => set(s => ({ notifications: s.notifications.map(n => n.id === id ? { ...n, isRead: true } : n) })),
  markAllNotificationsRead: () => set(s => ({ notifications: s.notifications.map(n => ({ ...n, isRead: true })) })),

  addRequest: (req) => set(s => ({ requests: [...s.requests, req] })),
  updateRequest: (req) => set(s => ({ requests: s.requests.map(r => r.id === req.id ? req : r) })),
}));
