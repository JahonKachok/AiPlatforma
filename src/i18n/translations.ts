export type Language = 'uz' | 'ru' | 'en';

export interface AppTranslations {
  nav: {
    dashboard: string; projects: string; tasks: string; documents: string;
    approvals: string; finance: string; analytics: string; requests: string;
    employees: string; settings: string; templates: string;
  };
  header: { search: string; notifications: string; logout: string; };
  login: {
    platformSubtitle: string; title: string; email: string; password: string;
    submit: string; submitting: string; error: string; demoAccounts: string;
  };
  dashboard: {
    title: string; subtitle: string; activeProjects: string; tasksInProgress: string;
    pendingApprovals: string; overdueTasks: string; activity: string; tasks: string;
    documents: string; taskStatuses: string; financeByProjects: string; team: string;
    all: string; activeProjectsList: string; recentTasks: string; until: string;
    budget: string; paid: string; mln: string;
  };
  documents: {
    title: string; subtitle: string; totalDocs: string; all: string; upload: string;
    searchPlaceholder: string; docColumn: string; projectColumn: string; versionColumn: string;
    sizeColumn: string; uploaderColumn: string; dateColumn: string; statusColumn: string;
    notFound: string; approvalRoute: string; download: string; approve: string;
    draft: string; review: string; approved: string; rejected: string; archived: string;
    pending: string; revision: string;
    uploadTitle: string; docNameLabel: string; docTypeLabel: string;
    deadlineLabel: string; journalTitle: string; journalEmpty: string;
  };
  approvals: {
    title: string; subtitle: string; pending: string; approvedDocs: string; rejectedDocs: string;
    waitingApproval: string; approvalStatus: string; comment: string; commentPlaceholder: string;
    close: string; reject: string; approve: string; notStarted: string; waiting: string;
    approvedStatus: string; rejectedStatus: string; revisionBtn: string; revisionStatus: string;
  };
  finance: {
    title: string; subtitle: string; totalBudget: string; received: string; expenses: string;
    expected: string; overview: string; records: string; employees: string;
    budgetVsPayment: string; budgetDistribution: string; financeByProjects: string;
    allProjects: string; description: string; projectColumn: string; typeColumn: string;
    amountColumn: string; dateColumn: string; statusColumn: string;
    contract: string; paid: string; balance: string; paymentProgress: string;
    budget: string; remainder: string;
    income: string; expense: string; advance: string; payment: string;
    pendingStatus: string; paidStatus: string; overdueStatus: string; mln: string;
  };
  projects: {
    title: string; inSystem: string; searchPlaceholder: string; all: string; newProject: string;
    total: string; active: string; planning: string; completed: string; paused: string; notFound: string;
    until: string; participants: string; paymentLabel: string; createTitle: string;
    nameLabel: string; clientLabel: string; addressLabel: string; deadlineLabel: string;
    budgetLabel: string; stageLabel: string; priorityLabel: string; gipLabel: string;
    notAssigned: string; cancel: string; create: string; tasksCount: string;
  };
  tasks: {
    title: string; inSystem: string; allProjects: string; allAssignees: string;
    newTask: string; noTasks: string; assigneeLabel: string; deadlineLabel: string;
    close: string; nameLabel: string; descriptionLabel: string; projectLabel: string;
    priorityLabel: string; notSelected: string; notAssigned: string;
    columns: { new: string; in_progress: string; review: string; revision: string; approved: string; completed: string; };
    tableTask: string; tableProject: string; tableAssignee: string; tableStatus: string;
    tablePriority: string; tableDeadline: string; create: string; cancel: string;
  };
  requests: {
    title: string; subtitle: string; newRequest: string; noRequests: string;
    discussion: string; clarification: string; onApproval: string; completedStatus: string;
    author: string; responsible: string; noComments: string; commentPlaceholder: string;
    send: string; topicLabel: string; descriptionLabel: string; projectLabel: string;
    priorityLabel: string; notSelected: string; notAssigned: string;
    cancel: string; create: string; commentsLabel: string;
  };
  users: {
    title: string; subtitle: string; total: string; active: string; gipCount: string;
    designersCount: string; searchPlaceholder: string; all: string; addButton: string;
    projectsCount: string; tasksCount: string; fullNameLabel: string; emailLabel: string;
    roleLabel: string; departmentLabel: string; phoneLabel: string; accessNote: string;
    newEmployee: string; passwordLabel: string;
  };
  settings: {
    title: string; subtitle: string; profileTitle: string; securityTitle: string;
    twoFactor: string; twoFactorDesc: string; changePassword: string; changePasswordDesc: string;
    changeBtn: string; integrationsTitle: string; connected: string; notConnected: string;
    connectBtn: string; disconnectBtn: string; connectNewService: string; notificationsTitle: string;
    notifNewTasks: string; notifDeadlines: string; notifApprovals: string; notifComments: string;
    notifFinance: string; notifEmail: string; notifPush: string; notifTelegram: string;
    notifNewTasksDesc: string; notifDeadlinesDesc: string; notifApprovalsDesc: string; notifCommentsDesc: string;
    notifFinanceDesc: string; notifEmailDesc: string; notifPushDesc: string; notifTelegramDesc: string;
    interfaceTitle: string; darkTheme: string; darkThemeDesc: string; languageLabel: string; timezoneLabel: string;
    nameLabel: string; emailLabel: string; phoneLabel: string; deptLabel: string; saveChanges: string; saving: string; saved: string;
    googleDriveDesc: string; telegramDesc: string; whatsappDesc: string; outlookDesc: string;
    backupTitle: string; backupDesc: string; backupBtn: string; backupCreating: string; backupList: string;
  };
  reports: {
    title: string; subtitle: string; completedTasks: string; approvedDocs: string;
    paidMln: string; activeEmployees: string; tasksByEmployee: string; financeTrend: string;
    projectStatuses: string; platformHealth: string; taskStatusDistribution: string;
    total: string; completed: string; inProgress: string; income: string; expense: string;
    metrics: string; months: string[];
    exportTitle: string; exportProjects: string; exportTasks: string;
    exportFinance: string; exportEmployees: string;
  };
  templates: {
    title: string; subtitle: string; newTemplate: string; generate: string;
    nameLabel: string; typeLabel: string; descriptionLabel: string; contentLabel: string;
    placeholdersHint: string; projectLabel: string; employeeLabel: string;
    generateTitle: string; download: string; noTemplates: string; created: string;
    types: Record<string, string>;
  };
  projectDetail: {
    notFound: string; backBtn: string; projectInfo: string; address: string; stage: string;
    deadline: string; startDate: string; sections: string; tasks: string; openAll: string;
    noTasks: string; finance: string; budget: string; paid: string; remainder: string;
    statistics: string; tasksCount: string; overdue: string; docsCount: string;
    participantsCount: string; team: string; gipLabel: string;
    editProject: string; confirmDelete: string;
  };
  roles: Record<string, string>;
  taskStatus: Record<string, string>;
  projectStatus: Record<string, string>;
  projectStage: Record<string, string>;
  priority: Record<string, string>;
  common: {
    save: string; cancel: string; delete: string; edit: string; add: string; close: string;
    back: string; loading: string; noData: string; search: string; filter: string;
    export: string; yes: string; no: string;
  };
}

export const translations: Record<Language, AppTranslations> = {
  uz: {
    nav: {
      dashboard: "Bosh sahifa", projects: "Loyihalar", tasks: "Vazifalar",
      documents: "Hujjatlar", approvals: "Kelishuvlar", finance: "Moliya",
      analytics: "Tahlil", requests: "So'rovlar", employees: "Xodimlar", settings: "Sozlamalar",
      templates: "Shablonlar",
    },
    header: { search: "Qidirish...", notifications: "Bildirishnomalar", logout: "Chiqish" },
    login: {
      platformSubtitle: "Loyihalash boshqaruv platformasi", title: "Tizimga kirish",
      email: "Email", password: "Parol", submit: "Kirish", submitting: "Kirilmoqda...",
      error: "Noto'g'ri email yoki parol", demoAccounts: "Demo hisoblar (har qanday parol)",
    },
    dashboard: {
      title: "Bosh sahifa", subtitle: "Platformaning umumiy ko'rinishi",
      activeProjects: "Faol loyihalar", tasksInProgress: "Bajarilayotgan vazifalar",
      pendingApprovals: "Kelishuvda", overdueTasks: "Muddati o'tgan vazifalar",
      activity: "Faollik", tasks: "Vazifalar", documents: "Hujjatlar",
      taskStatuses: "Vazifa holatlari", financeByProjects: "Loyihalar bo'yicha moliya (mln so'm)",
      team: "Jamoa", all: "Barchasi", activeProjectsList: "Faol loyihalar",
      recentTasks: "So'nggi vazifalar", until: "gacha", budget: "Byudjet", paid: "To'langan", mln: "mln",
    },
    documents: {
      title: "Hujjat aylanmasi", subtitle: "Hujjatlar reestri va kelishuvlar",
      totalDocs: "Jami hujjatlar", all: "Barchasi", upload: "Yuklash",
      searchPlaceholder: "Hujjat qidirish...", docColumn: "Hujjat", projectColumn: "Loyiha",
      versionColumn: "Versiya", sizeColumn: "Hajm", uploaderColumn: "Yuklagan",
      dateColumn: "Sana", statusColumn: "Holat", notFound: "Hujjatlar topilmadi",
      approvalRoute: "Kelishuv marshruti", download: "Yuklab olish", approve: "Tasdiqlash",
      draft: "Qoralama", review: "Kelishuvda", approved: "Tasdiqlangan",
      rejected: "Rad etilgan", archived: "Arxiv", pending: "Kutilmoqda", revision: "Qayta ishlash",
      uploadTitle: "Hujjat yuklash", docNameLabel: "Hujjat nomi", docTypeLabel: "Tur",
      deadlineLabel: "Muddat", journalTitle: "Amallar jurnali", journalEmpty: "Jurnal bo'sh",
    },
    approvals: {
      title: "Kelishuvlar", subtitle: "Hujjatlar kelishuv marshrutlari",
      pending: "Kelishuvda", approvedDocs: "Tasdiqlangan", rejectedDocs: "Rad etilgan",
      waitingApproval: "Kelishuv kutilmoqda", approvalStatus: "Kelishuv holati",
      comment: "Izoh", commentPlaceholder: "Majburiy emas...",
      close: "Yopish", reject: "Rad etish", approve: "Tasdiqlash",
      notStarted: "Boshlanmagan", waiting: "Kutilmoqda",
      approvedStatus: "Tasdiqlangan", rejectedStatus: "Rad etilgan",
      revisionBtn: "Qayta ishlashga", revisionStatus: "Qayta ishlashda",
    },
    finance: {
      title: "Moliya bo'limi", subtitle: "Kirim, chiqim va to'lovlar hisobi",
      totalBudget: "Umumiy byudjet", received: "Olingan", expenses: "Xarajatlar",
      expected: "Kutilmoqda", overview: "Ko'rinish", records: "Operatsiyalar", employees: "Xodimlar",
      budgetVsPayment: "Byudjet vs To'lov (mln so'm)", budgetDistribution: "Byudjet taqsimoti",
      financeByProjects: "Loyihalar bo'yicha moliya", allProjects: "Barcha loyihalar",
      description: "Tavsif", projectColumn: "Loyiha", typeColumn: "Turi",
      amountColumn: "Miqdor", dateColumn: "Sana", statusColumn: "Holat",
      contract: "Shartnoma", paid: "To'langan", balance: "Qoldiq",
      paymentProgress: "To'lov jarayoni", budget: "Byudjet", remainder: "Qoldiq",
      income: "Kirim", expense: "Chiqim", advance: "Avans", payment: "To'lov",
      pendingStatus: "Kutilmoqda", paidStatus: "To'langan", overdueStatus: "Muddati o'tgan", mln: "mln",
    },
    projects: {
      title: "Loyihalar", inSystem: "tizimda loyiha", searchPlaceholder: "Loyiha qidirish...",
      all: "Barchasi", newProject: "Yangi loyiha",
      total: "Jami", active: "Faol", planning: "Rejalashtirilmoqda",
      completed: "Tugallangan", paused: "To'xtatilgan", notFound: "Loyihalar topilmadi",
      until: "gacha", participants: "ishtirokchi", paymentLabel: "To'lov",
      createTitle: "Yangi loyiha", nameLabel: "Loyiha nomi *", clientLabel: "Buyurtmachi *",
      addressLabel: "Ob'ekt manzili", deadlineLabel: "Topshirish muddati",
      budgetLabel: "Byudjet (so'm)", stageLabel: "Bosqich", priorityLabel: "Muhimlik darajasi",
      gipLabel: "BLM (Bosh loyiha muhandisi)", notAssigned: "— Tayinlanmagan —",
      cancel: "Bekor qilish", create: "Loyiha yaratish", tasksCount: "vazifa",
    },
    tasks: {
      title: "Vazifalar", inSystem: "tizimda vazifa", allProjects: "Barcha loyihalar",
      allAssignees: "Barcha ijrochilar", newTask: "Yangi vazifa", noTasks: "Vazifalar yo'q",
      assigneeLabel: "Ijrochi", deadlineLabel: "Muddat", close: "Yopish",
      nameLabel: "Nomi *", descriptionLabel: "Tavsif", projectLabel: "Loyiha",
      priorityLabel: "Muhimlik darajasi", notSelected: "— Tanlanmagan —", notAssigned: "— Tayinlanmagan —",
      columns: { new: "Yangi", in_progress: "Bajarilmoqda", review: "Tekshiruvda", revision: "Qayta ishlash", approved: "Tasdiqlangan", completed: "Tugallangan" },
      tableTask: "Vazifa", tableProject: "Loyiha", tableAssignee: "Ijrochi",
      tableStatus: "Holat", tablePriority: "Muhimlik", tableDeadline: "Muddat",
      create: "Yaratish", cancel: "Bekor qilish",
    },
    requests: {
      title: "So'rovlar va muhokamalar", subtitle: "Ichki so'rovlar va yozishmalar",
      newRequest: "Yangi so'rov", noRequests: "So'rovlar yo'q",
      discussion: "Muhokama", clarification: "Aniqlashtirish",
      onApproval: "Kelishuvda", completedStatus: "Bajarildi",
      author: "Muallif", responsible: "Mas'ul", noComments: "Izohlar yo'q",
      commentPlaceholder: "Izoh yozing...", send: "Yuborish",
      topicLabel: "Mavzu *", descriptionLabel: "Tavsif", projectLabel: "Loyiha",
      priorityLabel: "Muhimlik darajasi", notSelected: "— Tanlanmagan —", notAssigned: "— Tayinlanmagan —",
      cancel: "Bekor qilish", create: "Yaratish", commentsLabel: "Izohlar",
    },
    users: {
      title: "Xodimlar", subtitle: "Foydalanuvchilar va ruxsatlarni boshqarish",
      total: "Jami", active: "Faol", gipCount: "BLM", designersCount: "Loyihachilar",
      searchPlaceholder: "Xodim qidirish...", all: "Barchasi", addButton: "Qo'shish",
      projectsCount: "loyiha", tasksCount: "vazifa", fullNameLabel: "F.I.Sh. *",
      emailLabel: "Email *", roleLabel: "Roli", departmentLabel: "Bo'lim", phoneLabel: "Telefon",
      accessNote: "Kirish tanlangan rolga muvofiq sozlanadi", newEmployee: "Yangi xodim",
      passwordLabel: "Parol *",
    },
    settings: {
      title: "Sozlamalar", subtitle: "Profil va tizim sozlamalari",
      profileTitle: "Foydalanuvchi profili", securityTitle: "Xavfsizlik",
      twoFactor: "Ikki faktorli autentifikatsiya", twoFactorDesc: "Qo'shimcha kirish himoyasi",
      changePassword: "Parolni o'zgartirish", changePasswordDesc: "Oxirgi o'zgartirish: 30 kun oldin",
      changeBtn: "O'zgartirish", integrationsTitle: "Integratsiyalar",
      connected: "Ulangan", notConnected: "Ulanmagan", connectBtn: "Ulash", disconnectBtn: "Uzish",
      connectNewService: "Yangi servis ulash",
      notificationsTitle: "Bildirishnomalar", notifNewTasks: "Yangi vazifalar",
      notifDeadlines: "Muddatlar", notifApprovals: "Kelishuvlar", notifComments: "Izohlar",
      notifFinance: "Moliyaviy", notifEmail: "Email bildirishnomalar",
      notifPush: "Push bildirishnomalar", notifTelegram: "Telegram bildirishnomalar",
      notifNewTasksDesc: "Yangi vazifalar haqida bildirishnomalar",
      notifDeadlinesDesc: "Yaqinlashayotgan muddatlar haqida eslatmalar",
      notifApprovalsDesc: "Kelishuvlar haqida bildirishnomalar",
      notifCommentsDesc: "Yangi izohlar haqida bildirishnomalar",
      notifFinanceDesc: "Moliyaviy operatsiyalar haqida bildirishnomalar",
      notifEmailDesc: "Email orqali bildirishnomalar olish",
      notifPushDesc: "Brauzerdagi bildirishnomalar",
      notifTelegramDesc: "Telegramdagi bildirishnomalar",
      interfaceTitle: "Interfeys", darkTheme: "Tungi mavzu", darkThemeDesc: "Yorug' va tungi mavzu o'rtasida almashish", languageLabel: "Til",
      timezoneLabel: "Vaqt zonasi", nameLabel: "Ism", emailLabel: "Email",
      phoneLabel: "Telefon", deptLabel: "Bo'lim", saveChanges: "O'zgarishlarni saqlash", saving: "Saqlanmoqda...", saved: "Saqlandi",
      googleDriveDesc: "Fayllarni sinxronlash", telegramDesc: "Telegram bildirishnomalar",
      whatsappDesc: "WhatsApp bildirishnomalar", outlookDesc: "Email bildirishnomalar",
      backupTitle: "Zaxira nusxa", backupDesc: "Ma'lumotlar bazasi va fayllarning zaxira nusxasini yaratish",
      backupBtn: "Zaxira yaratish", backupCreating: "Yaratilmoqda...", backupList: "Zaxira nusxalar",
    },
    reports: {
      title: "Tahlil va hisobotlar", subtitle: "Platforma bo'yicha yig'ma statistika",
      completedTasks: "Tugallangan vazifalar", approvedDocs: "Tasdiq. hujjatlar",
      paidMln: "To'langan (mln)", activeEmployees: "Faol xodimlar",
      tasksByEmployee: "Xodimlar bo'yicha vazifalar", financeTrend: "Moliyaviy trend (mln so'm)",
      projectStatuses: "Loyiha holatlari", platformHealth: "Platforma salomatligi",
      taskStatusDistribution: "Vazifalar holati bo'yicha taqsimot",
      total: "Jami", completed: "Tugallangan", inProgress: "Bajarilmoqda",
      income: "Kirim", expense: "Chiqim", metrics: "Ko'rsatkichlar",
      months: ["Yan", "Fev", "Mar", "Apr", "May", "Iyn", "Iyl", "Avg"],
      exportTitle: "Excel eksport", exportProjects: "Loyihalar", exportTasks: "Vazifalar",
      exportFinance: "Moliya", exportEmployees: "Xodimlar",
    },
    templates: {
      title: "Hujjat shablonlari", subtitle: "Shartnoma, dalolatnoma va hisoblarni avto-yaratish",
      newTemplate: "Yangi shablon", generate: "Hujjat yaratish",
      nameLabel: "Nomi", typeLabel: "Turi", descriptionLabel: "Tavsif", contentLabel: "Matn",
      placeholdersHint: "O'zgaruvchilar: {{project_name}}, {{client_name}}, {{address}}, {{amount}}, {{deadline}}, {{today}}, {{employee_name}} va h.k.",
      projectLabel: "Loyiha", employeeLabel: "Xodim (ixtiyoriy)",
      generateTitle: "Shablondan hujjat yaratish", download: "Yuklab olish",
      noTemplates: "Shablonlar yo'q", created: "Hujjat yaratildi",
      types: { contract: "Shartnoma", act: "Dalolatnoma", appendix: "Ilova", invoice: "Hisob", other: "Boshqa" },
    },
    projectDetail: {
      notFound: "Loyiha topilmadi", backBtn: "Loyihalar", projectInfo: "Loyiha haqida ma'lumot",
      address: "Manzil", stage: "Bosqich", deadline: "Muddat", startDate: "Boshlanish",
      sections: "Loyiha bo'limlari", tasks: "Vazifalar", openAll: "Barchasini ochish",
      noTasks: "Vazifalar yo'q", finance: "Moliya", budget: "Byudjet", paid: "To'langan",
      remainder: "Qoldiq", statistics: "Statistika", tasksCount: "Vazifalar", overdue: "Muddati o'tgan",
      docsCount: "Hujjatlar", participantsCount: "Ishtirokchilar", team: "Jamoa", gipLabel: "BLM",
      editProject: "Loyihani tahrirlash", confirmDelete: "Bu loyihani o'chirishni tasdiqlaysizmi? Bu amalni qaytarib bo'lmaydi.",
    },
    roles: {
      admin: "Administrator", manager: "Rahbar", gip: "Bosh loyiha muhandisi",
      gip_assistant: "BLM yordamchisi", designer: "Loyihachi", reviewer: "Tekshiruvchi", client: "Buyurtmachi",
    },
    taskStatus: {
      new: "Yangi", in_progress: "Bajarilmoqda", review: "Tekshiruvda",
      revision: "Qayta ishlash", approved: "Tasdiqlangan", completed: "Tugallangan",
    },
    projectStatus: {
      active: "Faol", completed: "Tugallangan", paused: "To'xtatilgan",
      cancelled: "Bekor qilingan", planning: "Rejalashtirilmoqda",
    },
    projectStage: {
      concept: "Konsepsiya", preliminary: "Dastlabki loyiha", working_docs: "Ishchi hujjatlar",
      expertise: "Ekspertiza", construction: "Muallif nazorati",
    },
    priority: { low: "Past", medium: "O'rta", high: "Yuqori", critical: "Kritik" },
    common: {
      save: "Saqlash", cancel: "Bekor qilish", delete: "O'chirish", edit: "Tahrirlash",
      add: "Qo'shish", close: "Yopish", back: "Orqaga", loading: "Yuklanmoqda...",
      noData: "Ma'lumot yo'q", search: "Qidirish", filter: "Filtrlash",
      export: "Eksport", yes: "Ha", no: "Yo'q",
    },
  },

  ru: {
    nav: {
      dashboard: "Дашборд", projects: "Проекты", tasks: "Задачи",
      documents: "Документы", approvals: "Согласования", finance: "Финансы",
      analytics: "Аналитика", requests: "Запросы", employees: "Сотрудники", settings: "Настройки",
      templates: "Шаблоны",
    },
    header: { search: "Поиск...", notifications: "Уведомления", logout: "Выйти" },
    login: {
      platformSubtitle: "Платформа управления проектированием", title: "Вход в систему",
      email: "Email", password: "Пароль", submit: "Войти", submitting: "Вход...",
      error: "Неверный email или пароль", demoAccounts: "Демо-аккаунты (пароль: любой)",
    },
    dashboard: {
      title: "Дашборд", subtitle: "Общий обзор платформы",
      activeProjects: "Активных проектов", tasksInProgress: "Задач в работе",
      pendingApprovals: "На согласовании", overdueTasks: "Просроченных задач",
      activity: "Активность", tasks: "Задачи", documents: "Документы",
      taskStatuses: "Статусы задач", financeByProjects: "Финансы по проектам (млн сум)",
      team: "Команда", all: "Все", activeProjectsList: "Активные проекты",
      recentTasks: "Последние задачи", until: "до", budget: "Бюджет", paid: "Оплачено", mln: "млн",
    },
    documents: {
      title: "Документооборот", subtitle: "Реестр документов и согласования",
      totalDocs: "Всего документов", all: "Все", upload: "Загрузить",
      searchPlaceholder: "Поиск документов...", docColumn: "Документ", projectColumn: "Проект",
      versionColumn: "Версия", sizeColumn: "Размер", uploaderColumn: "Загрузил",
      dateColumn: "Дата", statusColumn: "Статус", notFound: "Документы не найдены",
      approvalRoute: "Маршрут согласования", download: "Скачать", approve: "Согласовать",
      draft: "Черновик", review: "На согласовании", approved: "Согласовано",
      rejected: "Отклонено", archived: "Архив", pending: "Ожидает", revision: "На доработке",
      uploadTitle: "Загрузить документ", docNameLabel: "Название документа", docTypeLabel: "Тип",
      deadlineLabel: "Дедлайн", journalTitle: "Журнал действий", journalEmpty: "Журнал пуст",
    },
    approvals: {
      title: "Согласования", subtitle: "Маршруты согласования документов",
      pending: "На согласовании", approvedDocs: "Согласованные", rejectedDocs: "Отклонённые",
      waitingApproval: "Ожидают согласования", approvalStatus: "Статус согласования",
      comment: "Комментарий", commentPlaceholder: "Необязательно...",
      close: "Закрыть", reject: "Отклонить", approve: "Согласовать",
      notStarted: "Не начато", waiting: "Ожидает",
      approvedStatus: "Согласовано", rejectedStatus: "Отклонено",
      revisionBtn: "На доработку", revisionStatus: "Требует доработки",
    },
    finance: {
      title: "Финансовый блок", subtitle: "Учёт доходов, расходов и выплат",
      totalBudget: "Общий бюджет", received: "Получено", expenses: "Расходы",
      expected: "Ожидается", overview: "Обзор", records: "Операции", employees: "Сотрудники",
      budgetVsPayment: "Бюджет vs Оплата (млн сум)", budgetDistribution: "Распределение бюджета",
      financeByProjects: "Финансы по проектам", allProjects: "Все проекты",
      description: "Описание", projectColumn: "Проект", typeColumn: "Тип",
      amountColumn: "Сумма", dateColumn: "Дата", statusColumn: "Статус",
      contract: "Договор", paid: "Выплачено", balance: "Остаток",
      paymentProgress: "Прогресс выплат", budget: "Бюджет", remainder: "Остаток",
      income: "Доход", expense: "Расход", advance: "Аванс", payment: "Выплата",
      pendingStatus: "Ожидается", paidStatus: "Оплачено", overdueStatus: "Просрочено", mln: "млн",
    },
    projects: {
      title: "Проекты", inSystem: "проектов в системе", searchPlaceholder: "Поиск проектов...",
      all: "Все", newProject: "Новый проект",
      total: "Всего", active: "Активных", planning: "Планирование",
      completed: "Завершено", paused: "Приостановлено", notFound: "Проекты не найдены",
      until: "до", participants: "уч.", paymentLabel: "Оплата",
      createTitle: "Новый проект", nameLabel: "Название проекта *", clientLabel: "Заказчик *",
      addressLabel: "Адрес объекта", deadlineLabel: "Срок сдачи",
      budgetLabel: "Бюджет (сум)", stageLabel: "Стадия", priorityLabel: "Приоритет",
      gipLabel: "ГИП", notAssigned: "— Не назначен —",
      cancel: "Отмена", create: "Создать проект", tasksCount: "задач",
    },
    tasks: {
      title: "Задачи", inSystem: "задач в системе", allProjects: "Все проекты",
      allAssignees: "Все исполнители", newTask: "Новая задача", noTasks: "Нет задач",
      assigneeLabel: "Исполнитель", deadlineLabel: "Дедлайн", close: "Закрыть",
      nameLabel: "Название *", descriptionLabel: "Описание", projectLabel: "Проект",
      priorityLabel: "Приоритет", notSelected: "— Не выбран —", notAssigned: "— Не назначен —",
      columns: { new: "Новые", in_progress: "В работе", review: "На проверке", revision: "Доработка", approved: "Согласовано", completed: "Завершено" },
      tableTask: "Задача", tableProject: "Проект", tableAssignee: "Исполнитель",
      tableStatus: "Статус", tablePriority: "Приоритет", tableDeadline: "Дедлайн",
      create: "Создать", cancel: "Отмена",
    },
    requests: {
      title: "Запросы и обсуждения", subtitle: "Внутренние запросы и переписка",
      newRequest: "Новый запрос", noRequests: "Запросов нет",
      discussion: "Обсуждение", clarification: "Уточнение",
      onApproval: "На согласовании", completedStatus: "Выполнено",
      author: "Автор", responsible: "Ответственный", noComments: "Нет комментариев",
      commentPlaceholder: "Написать комментарий...", send: "Отправить",
      topicLabel: "Тема *", descriptionLabel: "Описание", projectLabel: "Проект",
      priorityLabel: "Приоритет", notSelected: "— Не выбран —", notAssigned: "— Не выбран —",
      cancel: "Отмена", create: "Создать", commentsLabel: "Комментарии",
    },
    users: {
      title: "Сотрудники", subtitle: "Управление пользователями и доступом",
      total: "Всего", active: "Активных", gipCount: "ГИП", designersCount: "Проектировщиков",
      searchPlaceholder: "Поиск сотрудников...", all: "Все", addButton: "Добавить",
      projectsCount: "проектов", tasksCount: "задач", fullNameLabel: "ФИО *",
      emailLabel: "Email *", roleLabel: "Роль", departmentLabel: "Отдел", phoneLabel: "Телефон",
      accessNote: "Доступ будет настроен в соответствии с выбранной ролью", newEmployee: "Новый сотрудник",
      passwordLabel: "Пароль *",
    },
    settings: {
      title: "Настройки", subtitle: "Настройки профиля и системы",
      profileTitle: "Профиль пользователя", securityTitle: "Безопасность",
      twoFactor: "Двухфакторная аутентификация", twoFactorDesc: "Дополнительная защита входа",
      changePassword: "Изменить пароль", changePasswordDesc: "Последнее изменение: 30 дней назад",
      changeBtn: "Изменить", integrationsTitle: "Интеграции",
      connected: "Подключено", notConnected: "Не подключено", connectBtn: "Подключить", disconnectBtn: "Отключить",
      connectNewService: "Подключить новый сервис",
      notificationsTitle: "Уведомления", notifNewTasks: "Новые задачи",
      notifDeadlines: "Дедлайны", notifApprovals: "Согласования", notifComments: "Комментарии",
      notifFinance: "Финансовые", notifEmail: "Email-уведомления",
      notifPush: "Push-уведомления", notifTelegram: "Telegram-уведомления",
      notifNewTasksDesc: "Уведомления о новых задачах",
      notifDeadlinesDesc: "Напоминания о приближающихся сроках",
      notifApprovalsDesc: "Уведомления о согласованиях",
      notifCommentsDesc: "Уведомления о новых комментариях",
      notifFinanceDesc: "Уведомления о финансовых операциях",
      notifEmailDesc: "Получать уведомления на email",
      notifPushDesc: "Уведомления в браузере",
      notifTelegramDesc: "Уведомления в Telegram",
      interfaceTitle: "Интерфейс", darkTheme: "Тёмная тема", darkThemeDesc: "Переключение между светлой и тёмной темой", languageLabel: "Язык",
      timezoneLabel: "Временная зона", nameLabel: "Имя", emailLabel: "Email",
      phoneLabel: "Телефон", deptLabel: "Отдел", saveChanges: "Сохранить изменения", saving: "Сохранение...", saved: "Сохранено",
      googleDriveDesc: "Синхронизация файлов", telegramDesc: "Уведомления в Telegram",
      whatsappDesc: "Уведомления в WhatsApp", outlookDesc: "Email-уведомления",
      backupTitle: "Резервное копирование", backupDesc: "Создание резервной копии базы данных и файлов",
      backupBtn: "Создать копию", backupCreating: "Создание...", backupList: "Резервные копии",
    },
    reports: {
      title: "Аналитика и отчёты", subtitle: "Сводная статистика по платформе",
      completedTasks: "Завершено задач", approvedDocs: "Согл. документов",
      paidMln: "Выплачено (млн)", activeEmployees: "Активных сотр.",
      tasksByEmployee: "Задачи по сотрудникам", financeTrend: "Финансовый тренд (млн сум)",
      projectStatuses: "Статусы проектов", platformHealth: "Общее здоровье платформы",
      taskStatusDistribution: "Распределение задач по статусам",
      total: "Всего", completed: "Завершено", inProgress: "В работе",
      income: "Доходы", expense: "Расходы", metrics: "Показатели",
      months: ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг"],
      exportTitle: "Экспорт в Excel", exportProjects: "Проекты", exportTasks: "Задачи",
      exportFinance: "Финансы", exportEmployees: "Сотрудники",
    },
    templates: {
      title: "Шаблоны документов", subtitle: "Автоформирование договоров, актов и счетов",
      newTemplate: "Новый шаблон", generate: "Сформировать документ",
      nameLabel: "Название", typeLabel: "Тип", descriptionLabel: "Описание", contentLabel: "Текст",
      placeholdersHint: "Переменные: {{project_name}}, {{client_name}}, {{address}}, {{amount}}, {{deadline}}, {{today}}, {{employee_name}} и др.",
      projectLabel: "Проект", employeeLabel: "Сотрудник (необязательно)",
      generateTitle: "Сформировать документ из шаблона", download: "Скачать",
      noTemplates: "Шаблонов нет", created: "Документ сформирован",
      types: { contract: "Договор", act: "Акт", appendix: "Приложение", invoice: "Счёт", other: "Другое" },
    },
    projectDetail: {
      notFound: "Проект не найден", backBtn: "Проекты", projectInfo: "Информация о проекте",
      address: "Адрес", stage: "Стадия", deadline: "Дедлайн", startDate: "Начало",
      sections: "Разделы проекта", tasks: "Задачи", openAll: "Открыть все",
      noTasks: "Нет задач", finance: "Финансы", budget: "Бюджет", paid: "Оплачено",
      remainder: "Остаток", statistics: "Статистика", tasksCount: "Задач", overdue: "Просрочено",
      docsCount: "Документов", participantsCount: "Участников", team: "Команда", gipLabel: "ГИП",
      editProject: "Редактировать проект", confirmDelete: "Вы уверены, что хотите удалить этот проект? Это действие нельзя отменить.",
    },
    roles: {
      admin: "Администратор", manager: "Руководитель", gip: "ГИП",
      gip_assistant: "Пом. ГИПа", designer: "Проектировщик", reviewer: "Проверяющий", client: "Заказчик",
    },
    taskStatus: {
      new: "Новая", in_progress: "В работе", review: "На проверке",
      revision: "На доработке", approved: "Согласовано", completed: "Завершено",
    },
    projectStatus: {
      active: "Активный", completed: "Завершён", paused: "Приостановлен",
      cancelled: "Отменён", planning: "Планирование",
    },
    projectStage: {
      concept: "Концепция", preliminary: "Предпроект", working_docs: "Рабочая документация",
      expertise: "Экспертиза", construction: "Авторский надзор",
    },
    priority: { low: "Низкий", medium: "Средний", high: "Высокий", critical: "Критический" },
    common: {
      save: "Сохранить", cancel: "Отмена", delete: "Удалить", edit: "Редактировать",
      add: "Добавить", close: "Закрыть", back: "Назад", loading: "Загрузка...",
      noData: "Нет данных", search: "Поиск", filter: "Фильтр",
      export: "Экспорт", yes: "Да", no: "Нет",
    },
  },

  en: {
    nav: {
      dashboard: "Dashboard", projects: "Projects", tasks: "Tasks",
      documents: "Documents", approvals: "Approvals", finance: "Finance",
      analytics: "Analytics", requests: "Requests", employees: "Employees", settings: "Settings",
      templates: "Templates",
    },
    header: { search: "Search...", notifications: "Notifications", logout: "Log out" },
    login: {
      platformSubtitle: "Project Design Management Platform", title: "Sign In",
      email: "Email", password: "Password", submit: "Sign In", submitting: "Signing in...",
      error: "Invalid email or password", demoAccounts: "Demo accounts (any password)",
    },
    dashboard: {
      title: "Dashboard", subtitle: "Platform overview",
      activeProjects: "Active projects", tasksInProgress: "Tasks in progress",
      pendingApprovals: "Pending approvals", overdueTasks: "Overdue tasks",
      activity: "Activity", tasks: "Tasks", documents: "Documents",
      taskStatuses: "Task statuses", financeByProjects: "Finance by projects (M UZS)",
      team: "Team", all: "All", activeProjectsList: "Active projects",
      recentTasks: "Recent tasks", until: "until", budget: "Budget", paid: "Paid", mln: "M",
    },
    documents: {
      title: "Document Registry", subtitle: "Document registry and approvals",
      totalDocs: "Total documents", all: "All", upload: "Upload",
      searchPlaceholder: "Search documents...", docColumn: "Document", projectColumn: "Project",
      versionColumn: "Version", sizeColumn: "Size", uploaderColumn: "Uploaded by",
      dateColumn: "Date", statusColumn: "Status", notFound: "No documents found",
      approvalRoute: "Approval route", download: "Download", approve: "Approve",
      draft: "Draft", review: "Under Review", approved: "Approved",
      rejected: "Rejected", archived: "Archived", pending: "Pending", revision: "Revision",
      uploadTitle: "Upload Document", docNameLabel: "Document name", docTypeLabel: "Type",
      deadlineLabel: "Deadline", journalTitle: "Activity log", journalEmpty: "Log is empty",
    },
    approvals: {
      title: "Approvals", subtitle: "Document approval routes",
      pending: "Pending", approvedDocs: "Approved", rejectedDocs: "Rejected",
      waitingApproval: "Awaiting approval", approvalStatus: "Approval status",
      comment: "Comment", commentPlaceholder: "Optional...",
      close: "Close", reject: "Reject", approve: "Approve",
      notStarted: "Not started", waiting: "Waiting",
      approvedStatus: "Approved", rejectedStatus: "Rejected",
      revisionBtn: "Needs revision", revisionStatus: "Needs revision",
    },
    finance: {
      title: "Finance", subtitle: "Income, expense and payment tracking",
      totalBudget: "Total budget", received: "Received", expenses: "Expenses",
      expected: "Expected", overview: "Overview", records: "Transactions", employees: "Employees",
      budgetVsPayment: "Budget vs Payment (M UZS)", budgetDistribution: "Budget distribution",
      financeByProjects: "Finance by projects", allProjects: "All projects",
      description: "Description", projectColumn: "Project", typeColumn: "Type",
      amountColumn: "Amount", dateColumn: "Date", statusColumn: "Status",
      contract: "Contract", paid: "Paid", balance: "Balance",
      paymentProgress: "Payment progress", budget: "Budget", remainder: "Remainder",
      income: "Income", expense: "Expense", advance: "Advance", payment: "Payment",
      pendingStatus: "Pending", paidStatus: "Paid", overdueStatus: "Overdue", mln: "M",
    },
    projects: {
      title: "Projects", inSystem: "projects in system", searchPlaceholder: "Search projects...",
      all: "All", newProject: "New Project",
      total: "Total", active: "Active", planning: "Planning",
      completed: "Completed", paused: "Paused", notFound: "No projects found",
      until: "until", participants: "members", paymentLabel: "Payment",
      createTitle: "New Project", nameLabel: "Project name *", clientLabel: "Client *",
      addressLabel: "Site address", deadlineLabel: "Deadline",
      budgetLabel: "Budget (UZS)", stageLabel: "Stage", priorityLabel: "Priority",
      gipLabel: "Chief Project Engineer", notAssigned: "— Not assigned —",
      cancel: "Cancel", create: "Create project", tasksCount: "tasks",
    },
    tasks: {
      title: "Tasks", inSystem: "tasks in system", allProjects: "All projects",
      allAssignees: "All assignees", newTask: "New Task", noTasks: "No tasks",
      assigneeLabel: "Assignee", deadlineLabel: "Deadline", close: "Close",
      nameLabel: "Name *", descriptionLabel: "Description", projectLabel: "Project",
      priorityLabel: "Priority", notSelected: "— Not selected —", notAssigned: "— Not assigned —",
      columns: { new: "New", in_progress: "In Progress", review: "Under Review", revision: "Revision", approved: "Approved", completed: "Completed" },
      tableTask: "Task", tableProject: "Project", tableAssignee: "Assignee",
      tableStatus: "Status", tablePriority: "Priority", tableDeadline: "Deadline",
      create: "Create", cancel: "Cancel",
    },
    requests: {
      title: "Requests & Discussions", subtitle: "Internal requests and correspondence",
      newRequest: "New Request", noRequests: "No requests",
      discussion: "Discussion", clarification: "Clarification",
      onApproval: "Under Approval", completedStatus: "Completed",
      author: "Author", responsible: "Responsible", noComments: "No comments",
      commentPlaceholder: "Write a comment...", send: "Send",
      topicLabel: "Subject *", descriptionLabel: "Description", projectLabel: "Project",
      priorityLabel: "Priority", notSelected: "— Not selected —", notAssigned: "— Not selected —",
      cancel: "Cancel", create: "Create", commentsLabel: "Comments",
    },
    users: {
      title: "Employees", subtitle: "User and access management",
      total: "Total", active: "Active", gipCount: "CPE", designersCount: "Designers",
      searchPlaceholder: "Search employees...", all: "All", addButton: "Add",
      projectsCount: "projects", tasksCount: "tasks", fullNameLabel: "Full name *",
      emailLabel: "Email *", roleLabel: "Role", departmentLabel: "Department", phoneLabel: "Phone",
      accessNote: "Access will be configured according to the selected role", newEmployee: "New Employee",
      passwordLabel: "Password *",
    },
    settings: {
      title: "Settings", subtitle: "Profile and system settings",
      profileTitle: "User Profile", securityTitle: "Security",
      twoFactor: "Two-factor authentication", twoFactorDesc: "Additional login protection",
      changePassword: "Change password", changePasswordDesc: "Last changed: 30 days ago",
      changeBtn: "Change", integrationsTitle: "Integrations",
      connected: "Connected", notConnected: "Not connected", connectBtn: "Connect", disconnectBtn: "Disconnect",
      connectNewService: "Connect new service",
      notificationsTitle: "Notifications", notifNewTasks: "New tasks",
      notifDeadlines: "Deadlines", notifApprovals: "Approvals", notifComments: "Comments",
      notifFinance: "Financial", notifEmail: "Email notifications",
      notifPush: "Push notifications", notifTelegram: "Telegram notifications",
      notifNewTasksDesc: "Notifications about new tasks",
      notifDeadlinesDesc: "Reminders for upcoming deadlines",
      notifApprovalsDesc: "Notifications about approvals",
      notifCommentsDesc: "Notifications about new comments",
      notifFinanceDesc: "Notifications about financial operations",
      notifEmailDesc: "Receive notifications via email",
      notifPushDesc: "Notifications in the browser",
      notifTelegramDesc: "Notifications in Telegram",
      interfaceTitle: "Interface", darkTheme: "Dark theme", darkThemeDesc: "Switch between light and dark theme", languageLabel: "Language",
      timezoneLabel: "Timezone", nameLabel: "Name", emailLabel: "Email",
      phoneLabel: "Phone", deptLabel: "Department", saveChanges: "Save changes", saving: "Saving...", saved: "Saved",
      googleDriveDesc: "File synchronization", telegramDesc: "Telegram notifications",
      whatsappDesc: "WhatsApp notifications", outlookDesc: "Email notifications",
      backupTitle: "Backup", backupDesc: "Create a backup of the database and files",
      backupBtn: "Create backup", backupCreating: "Creating...", backupList: "Backups",
    },
    reports: {
      title: "Analytics & Reports", subtitle: "Platform summary statistics",
      completedTasks: "Completed tasks", approvedDocs: "Approved docs",
      paidMln: "Paid (M)", activeEmployees: "Active employees",
      tasksByEmployee: "Tasks by employee", financeTrend: "Finance trend (M UZS)",
      projectStatuses: "Project statuses", platformHealth: "Platform health",
      taskStatusDistribution: "Task status distribution",
      total: "Total", completed: "Completed", inProgress: "In Progress",
      income: "Income", expense: "Expense", metrics: "Metrics",
      months: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug"],
      exportTitle: "Export to Excel", exportProjects: "Projects", exportTasks: "Tasks",
      exportFinance: "Finance", exportEmployees: "Employees",
    },
    templates: {
      title: "Document Templates", subtitle: "Auto-generate contracts, acts and invoices",
      newTemplate: "New Template", generate: "Generate document",
      nameLabel: "Name", typeLabel: "Type", descriptionLabel: "Description", contentLabel: "Body",
      placeholdersHint: "Variables: {{project_name}}, {{client_name}}, {{address}}, {{amount}}, {{deadline}}, {{today}}, {{employee_name}} etc.",
      projectLabel: "Project", employeeLabel: "Employee (optional)",
      generateTitle: "Generate document from template", download: "Download",
      noTemplates: "No templates", created: "Document generated",
      types: { contract: "Contract", act: "Act", appendix: "Appendix", invoice: "Invoice", other: "Other" },
    },
    projectDetail: {
      notFound: "Project not found", backBtn: "Projects", projectInfo: "Project information",
      address: "Address", stage: "Stage", deadline: "Deadline", startDate: "Start date",
      sections: "Project sections", tasks: "Tasks", openAll: "Open all",
      noTasks: "No tasks", finance: "Finance", budget: "Budget", paid: "Paid",
      remainder: "Remainder", statistics: "Statistics", tasksCount: "Tasks", overdue: "Overdue",
      docsCount: "Documents", participantsCount: "Participants", team: "Team", gipLabel: "CPE",
      editProject: "Edit Project", confirmDelete: "Are you sure you want to delete this project? This action cannot be undone.",
    },
    roles: {
      admin: "Administrator", manager: "Manager", gip: "Chief Project Engineer",
      gip_assistant: "CPE Assistant", designer: "Designer", reviewer: "Reviewer", client: "Client",
    },
    taskStatus: {
      new: "New", in_progress: "In Progress", review: "Under Review",
      revision: "Needs Revision", approved: "Approved", completed: "Completed",
    },
    projectStatus: {
      active: "Active", completed: "Completed", paused: "Paused",
      cancelled: "Cancelled", planning: "Planning",
    },
    projectStage: {
      concept: "Concept", preliminary: "Preliminary", working_docs: "Working Documentation",
      expertise: "Expert Review", construction: "Construction Supervision",
    },
    priority: { low: "Low", medium: "Medium", high: "High", critical: "Critical" },
    common: {
      save: "Save", cancel: "Cancel", delete: "Delete", edit: "Edit",
      add: "Add", close: "Close", back: "Back", loading: "Loading...",
      noData: "No data", search: "Search", filter: "Filter",
      export: "Export", yes: "Yes", no: "No",
    },
  },
};
