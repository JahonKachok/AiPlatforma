import type { User, Project, Task, Document, FinancialRecord, Request, Notification, EmployeeFinance } from '../types';

export const mockUsers: User[] = [
  { id: 'u1', name: 'Алишер Каримов', email: 'admin@platform.uz', role: 'admin', department: 'Управление', phone: '+998 90 123 45 67', isActive: true, createdAt: '2024-01-01' },
  { id: 'u2', name: 'Бобур Рашидов', email: 'manager@platform.uz', role: 'manager', department: 'Управление', phone: '+998 91 234 56 78', isActive: true, createdAt: '2024-01-05' },
  { id: 'u3', name: 'Фаррух Усманов', email: 'gip1@platform.uz', role: 'gip', department: 'Проектирование', phone: '+998 93 345 67 89', isActive: true, createdAt: '2024-01-10' },
  { id: 'u4', name: 'Зафар Назаров', email: 'gip2@platform.uz', role: 'gip', department: 'Проектирование', phone: '+998 94 456 78 90', isActive: true, createdAt: '2024-01-12' },
  { id: 'u5', name: 'Малика Юсупова', email: 'designer1@platform.uz', role: 'designer', department: 'Архитектура', phone: '+998 95 567 89 01', isActive: true, createdAt: '2024-01-15' },
  { id: 'u6', name: 'Санжар Ахмедов', email: 'designer2@platform.uz', role: 'designer', department: 'Конструкции', phone: '+998 97 678 90 12', isActive: true, createdAt: '2024-01-20' },
  { id: 'u7', name: 'Нилуфар Хасанова', email: 'reviewer@platform.uz', role: 'reviewer', department: 'Контроль', phone: '+998 98 789 01 23', isActive: true, createdAt: '2024-02-01' },
  { id: 'u8', name: 'Камол Ишматов', email: 'client1@platform.uz', role: 'client', isActive: true, createdAt: '2024-02-10' },
];

export const currentUser: User = mockUsers[0];

export const mockProjects: Project[] = [
  {
    id: 'p1', name: 'ЖК "Новый горизонт"', client: 'ООО Горизонт Строй',
    address: 'Ташкент, Юнусабадский район', stage: 'working_docs', status: 'active',
    deadline: '2024-12-31', startDate: '2024-03-01', gipId: 'u3',
    budget: 150000000, paid: 75000000, priority: 'high',
    participants: ['u3', 'u4', 'u5', 'u6', 'u7'],
    description: 'Жилой комплекс на 320 квартир, 5 корпусов',
    sections: [
      { id: 's1', projectId: 'p1', name: 'Архитектурные решения', code: 'АР', gipId: 'u5', deadline: '2024-10-01', status: 'active' },
      { id: 's2', projectId: 'p1', name: 'Конструктивные решения', code: 'КР', gipId: 'u6', deadline: '2024-10-15', status: 'active' },
      { id: 's3', projectId: 'p1', name: 'Инженерные сети', code: 'ИС', deadline: '2024-11-01', status: 'active' },
      { id: 's4', projectId: 'p1', name: 'Электроснабжение', code: 'ЭС', deadline: '2024-11-15', status: 'active' },
    ],
    objects: [
      { id: 'o1', projectId: 'p1', name: 'Корпус А', gipId: 'u3', status: 'active' },
      { id: 'o2', projectId: 'p1', name: 'Корпус Б', gipId: 'u4', status: 'active' },
      { id: 'o3', projectId: 'p1', name: 'Подземная парковка', status: 'planning' },
    ]
  },
  {
    id: 'p2', name: 'БЦ "Silk Tower"', client: 'Silk Group LLC',
    address: 'Ташкент, Мирабадский район', stage: 'preliminary', status: 'active',
    deadline: '2025-03-31', startDate: '2024-06-01', gipId: 'u4',
    budget: 280000000, paid: 42000000, priority: 'critical',
    participants: ['u4', 'u5', 'u6', 'u7'],
    description: 'Бизнес-центр класса А, 22 этажа',
    sections: [
      { id: 's5', projectId: 'p2', name: 'Архитектурные решения', code: 'АР', gipId: 'u5', status: 'active' },
      { id: 's6', projectId: 'p2', name: 'Конструктивные решения', code: 'КР', gipId: 'u6', status: 'active' },
    ],
    objects: [
      { id: 'o4', projectId: 'p2', name: 'Основное здание', gipId: 'u4', status: 'active' },
    ]
  },
  {
    id: 'p3', name: 'Торговый центр "Mega Mall"', client: 'Mega Invest',
    address: 'Самарканд, Сиёб тумани', stage: 'concept', status: 'planning',
    deadline: '2025-06-30', startDate: '2024-09-01', gipId: 'u3',
    budget: 450000000, paid: 0, priority: 'medium',
    participants: ['u3', 'u5'],
    sections: [],
    objects: []
  },
  {
    id: 'p4', name: 'Завод "TechPark"', client: 'TechPark Invest',
    address: 'Навои, Техническая зона', stage: 'expertise', status: 'active',
    deadline: '2024-09-30', startDate: '2024-01-15', gipId: 'u4',
    budget: 320000000, paid: 256000000, priority: 'high',
    participants: ['u4', 'u6', 'u7'],
    sections: [
      { id: 's7', projectId: 'p4', name: 'Технологические решения', code: 'ТР', status: 'active' },
    ],
    objects: []
  },
  {
    id: 'p5', name: 'Школа №45', client: 'Министерство народного образования',
    address: 'Фергана, Ёрмозор МФЙ', stage: 'working_docs', status: 'completed',
    deadline: '2024-05-30', startDate: '2023-09-01', gipId: 'u3',
    budget: 85000000, paid: 85000000, priority: 'medium',
    participants: ['u3', 'u5', 'u6'],
    sections: [],
    objects: []
  },
];

export const mockTasks: Task[] = [
  {
    id: 't1', title: 'Разработка фасадных решений корпуса А', description: 'Разработать архитектурные чертежи фасадов корпуса А ЖК "Новый горизонт" в соответствии с концепцией',
    projectId: 'p1', sectionId: 's1', assigneeId: 'u5', creatorId: 'u3',
    status: 'in_progress', priority: 'high', deadline: '2024-09-15',
    createdAt: '2024-08-01', updatedAt: '2024-08-20',
    attachments: [{ id: 'a1', name: 'facade_draft.pdf', size: 2048000, type: 'application/pdf', url: '#', uploadedBy: 'u5', uploadedAt: '2024-08-15' }],
    comments: [{ id: 'c1', userId: 'u3', text: 'Учтите требования к остеклению', createdAt: '2024-08-10' }]
  },
  {
    id: 't2', title: 'Расчёт фундамента корпуса Б', description: 'Выполнить расчёт и проектирование фундамента на основе данных геологии',
    projectId: 'p1', sectionId: 's2', assigneeId: 'u6', creatorId: 'u4',
    status: 'review', priority: 'critical', deadline: '2024-09-10',
    createdAt: '2024-08-05', updatedAt: '2024-08-22',
    attachments: [], comments: []
  },
  {
    id: 't3', title: 'Концептуальный дизайн Silk Tower', description: 'Разработка концепции экстерьера и интерьера бизнес-центра',
    projectId: 'p2', sectionId: 's5', assigneeId: 'u5', creatorId: 'u4',
    status: 'new', priority: 'critical', deadline: '2024-10-01',
    createdAt: '2024-08-25', updatedAt: '2024-08-25',
    attachments: [], comments: []
  },
  {
    id: 't4', title: 'Схема электроснабжения ЖК', description: 'Разработать принципиальную схему электроснабжения всего комплекса',
    projectId: 'p1', sectionId: 's4', assigneeId: 'u6', creatorId: 'u3',
    status: 'revision', priority: 'medium', deadline: '2024-10-20',
    createdAt: '2024-08-10', updatedAt: '2024-08-23',
    attachments: [], comments: [{ id: 'c2', userId: 'u7', text: 'Нужно пересмотреть расчёт нагрузок', createdAt: '2024-08-23' }]
  },
  {
    id: 't5', title: 'Проект инженерных сетей', description: 'Водоснабжение, канализация, отопление',
    projectId: 'p1', sectionId: 's3', assigneeId: 'u5', creatorId: 'u3',
    status: 'approved', priority: 'high', deadline: '2024-11-01',
    createdAt: '2024-07-15', updatedAt: '2024-08-20',
    attachments: [], comments: []
  },
  {
    id: 't6', title: 'Технологические расчёты TechPark', description: 'Расчёт производственных мощностей и технологических линий',
    projectId: 'p4', sectionId: 's7', assigneeId: 'u6', creatorId: 'u4',
    status: 'completed', priority: 'high', deadline: '2024-08-30',
    createdAt: '2024-06-01', updatedAt: '2024-08-30',
    attachments: [], comments: []
  },
  {
    id: 't7', title: 'Генплан Silk Tower', description: 'Разработка генерального плана участка с благоустройством',
    projectId: 'p2', sectionId: 's5', assigneeId: 'u5', creatorId: 'u4',
    status: 'in_progress', priority: 'high', deadline: '2024-09-25',
    createdAt: '2024-08-15', updatedAt: '2024-08-24',
    attachments: [], comments: []
  },
  {
    id: 't8', title: 'Пожарная безопасность ЖК', description: 'Раздел пожарной безопасности и эвакуации',
    projectId: 'p1', assigneeId: 'u7', creatorId: 'u3',
    status: 'new', priority: 'medium', deadline: '2024-10-30',
    createdAt: '2024-08-26', updatedAt: '2024-08-26',
    attachments: [], comments: []
  },
];

export const mockDocuments: Document[] = [
  {
    id: 'd1', name: 'АР-001_Фасады_КорпусА_v2.pdf', projectId: 'p1', sectionId: 's1',
    type: 'PDF', size: 15728640, version: '2.0', status: 'review',
    uploadedBy: 'u5', uploadedAt: '2024-08-20', deadline: '2024-09-01',
    approvalStage: 2,
    approvals: [
      { id: 'ap1', stage: 1, stageName: 'Исполнитель', userId: 'u5', status: 'approved', updatedAt: '2024-08-20' },
      { id: 'ap2', stage: 2, stageName: 'Проверяющий', userId: 'u7', status: 'pending' },
      { id: 'ap3', stage: 3, stageName: 'ГИП', userId: 'u3', status: 'pending' },
      { id: 'ap4', stage: 4, stageName: 'Руководитель', userId: 'u2', status: 'pending' },
      { id: 'ap5', stage: 5, stageName: 'Заказчик', userId: 'u8', status: 'pending' },
    ]
  },
  {
    id: 'd2', name: 'КР-001_Фундамент_КорпусБ_v1.dwg', projectId: 'p1', sectionId: 's2',
    type: 'DWG', size: 8388608, version: '1.0', status: 'draft',
    uploadedBy: 'u6', uploadedAt: '2024-08-22',
    approvals: [
      { id: 'ap6', stage: 1, stageName: 'Исполнитель', userId: 'u6', status: 'pending' },
    ]
  },
  {
    id: 'd3', name: 'ТЗ_Silk_Tower_v3.docx', projectId: 'p2',
    type: 'DOCX', size: 1048576, version: '3.0', status: 'approved',
    uploadedBy: 'u4', uploadedAt: '2024-08-10',
    approvals: [
      { id: 'ap7', stage: 1, stageName: 'Исполнитель', userId: 'u4', status: 'approved', updatedAt: '2024-08-10' },
      { id: 'ap8', stage: 2, stageName: 'Проверяющий', userId: 'u7', status: 'approved', updatedAt: '2024-08-12' },
      { id: 'ap9', stage: 3, stageName: 'ГИП', userId: 'u4', status: 'approved', updatedAt: '2024-08-14' },
      { id: 'ap10', stage: 4, stageName: 'Руководитель', userId: 'u2', status: 'approved', updatedAt: '2024-08-15' },
      { id: 'ap11', stage: 5, stageName: 'Заказчик', userId: 'u8', status: 'approved', updatedAt: '2024-08-16' },
    ]
  },
  {
    id: 'd4', name: 'Смета_ЖК_НовыйГоризонт.xlsx', projectId: 'p1',
    type: 'XLSX', size: 524288, version: '4.1', status: 'review',
    uploadedBy: 'u3', uploadedAt: '2024-08-18',
    approvals: []
  },
];

export const mockFinancials: FinancialRecord[] = [
  { id: 'f1', projectId: 'p1', type: 'income', amount: 50000000, description: 'Аванс по договору №123', date: '2024-03-15', category: 'Аванс', status: 'paid' },
  { id: 'f2', projectId: 'p1', type: 'income', amount: 25000000, description: 'Оплата за 1 этап', date: '2024-06-01', category: 'Оплата по этапу', status: 'paid' },
  { id: 'f3', projectId: 'p1', type: 'expense', amount: 8000000, description: 'Зарплата Усманов Ф.', date: '2024-06-30', category: 'Зарплата', userId: 'u3', status: 'paid' },
  { id: 'f4', projectId: 'p1', type: 'expense', amount: 5000000, description: 'Зарплата Юсупова М.', date: '2024-06-30', category: 'Зарплата', userId: 'u5', status: 'paid' },
  { id: 'f5', projectId: 'p2', type: 'income', amount: 42000000, description: 'Аванс Silk Tower', date: '2024-06-15', category: 'Аванс', status: 'paid' },
  { id: 'f6', projectId: 'p1', type: 'income', amount: 25000000, description: 'Оплата за 2 этап', date: '2024-09-01', category: 'Оплата по этапу', status: 'pending' },
  { id: 'f7', projectId: 'p4', type: 'income', amount: 256000000, description: 'Полная оплата TechPark', date: '2024-08-01', category: 'Полная оплата', status: 'paid' },
];

export const mockEmployeeFinances: EmployeeFinance[] = [
  { userId: 'u3', projectId: 'p1', contractAmount: 25000000, paid: 16000000, balance: 9000000, payments: [{ id: 'ep1', amount: 8000000, date: '2024-06-30', description: 'За июнь' }, { id: 'ep2', amount: 8000000, date: '2024-07-31', description: 'За июль' }] },
  { userId: 'u5', projectId: 'p1', contractAmount: 18000000, paid: 10000000, balance: 8000000, payments: [{ id: 'ep3', amount: 5000000, date: '2024-06-30', description: 'За июнь' }, { id: 'ep4', amount: 5000000, date: '2024-07-31', description: 'За июль' }] },
];

export const mockRequests: Request[] = [
  { id: 'r1', title: 'Уточнение по фасадным материалам', description: 'Нужно уточнить тип облицовочного материала для корпуса А', projectId: 'p1', creatorId: 'u5', assigneeId: 'u3', status: 'discussion', priority: 'medium', createdAt: '2024-08-20', comments: [{ id: 'rc1', userId: 'u3', text: 'Рассматриваем керамогранит или вентфасад', createdAt: '2024-08-21' }] },
  { id: 'r2', title: 'Изменение в техзадании Silk Tower', description: 'Заказчик просит добавить вертолётную площадку', projectId: 'p2', creatorId: 'u8', assigneeId: 'u4', status: 'clarification', priority: 'high', createdAt: '2024-08-22', comments: [] },
];

export const mockNotifications: Notification[] = [
  { id: 'n1', userId: 'u1', type: 'deadline', title: 'Приближается дедлайн', message: 'Задача "Расчёт фундамента корпуса Б" истекает через 3 дня', isRead: false, createdAt: '2024-08-27', link: '/tasks' },
  { id: 'n2', userId: 'u1', type: 'approval', title: 'Новый документ на согласование', message: 'АР-001_Фасады_КорпусА_v2.pdf ожидает вашего согласования', isRead: false, createdAt: '2024-08-26', link: '/approvals' },
  { id: 'n3', userId: 'u1', type: 'comment', title: 'Новый комментарий', message: 'Нилуфар Хасанова оставила комментарий к задаче', isRead: true, createdAt: '2024-08-23' },
  { id: 'n4', userId: 'u1', type: 'finance', title: 'Ожидается оплата', message: 'Оплата за 2 этап ЖК "Новый горизонт" ожидается 01.09.2024', isRead: false, createdAt: '2024-08-25', link: '/finance' },
  { id: 'n5', userId: 'u1', type: 'task', title: 'Новая задача назначена', message: 'Вам назначена задача "Пожарная безопасность ЖК"', isRead: true, createdAt: '2024-08-26', link: '/tasks' },
];

export const roleLabels: Record<string, string> = {
  admin: 'Администратор',
  manager: 'Руководитель',
  gip: 'ГИП',
  gip_assistant: 'Пом. ГИПа',
  designer: 'Проектировщик',
  reviewer: 'Проверяющий',
  client: 'Заказчик',
};

export const taskStatusLabels: Record<string, string> = {
  new: 'Новая',
  in_progress: 'В работе',
  review: 'На проверке',
  revision: 'На доработке',
  approved: 'Согласовано',
  completed: 'Завершено',
};

export const projectStatusLabels: Record<string, string> = {
  active: 'Активный',
  completed: 'Завершён',
  paused: 'Приостановлен',
  cancelled: 'Отменён',
  planning: 'Планирование',
};

export const projectStageLabels: Record<string, string> = {
  concept: 'Концепция',
  preliminary: 'Предпроект',
  working_docs: 'Рабочая документация',
  expertise: 'Экспертиза',
  construction: 'Авторский надзор',
};

export const priorityLabels: Record<string, string> = {
  low: 'Низкий',
  medium: 'Средний',
  high: 'Высокий',
  critical: 'Критический',
};
