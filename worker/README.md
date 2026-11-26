# Ishchi kompyuter (Local Worker)

Doim yoniq Windows kompyuter AutoCAD, Word va Excel ishlarini bajaradi. U serverga o'zi
ulanadi (faqat chiquvchi HTTPS), shuning uchun router/port sozlash kerak emas.
Claude kaliti kompyuterda saqlanmaydi: AI kerak bo'lsa server proksisi ishlatiladi.

| Ish (`kind`) | Nima qiladi | Kerak |
|---|---|---|
| `dwg_print` | Pechatnik + Shtampovshik: bo'sh shtamp atributlarini Sostav ma'lumoti bilan to'ldiradi, har varaqni o'z page setup'i bilan PDF qiladi (ramka, format, masshtab o'zgarmaydi) | AutoCAD |
| `dwg_translate` | Perevodchik: TEXT/MTEXT/atributlarni zh/ru/en tarjima qiladi, fayl nomi o'zgarmaydi, sig'masa kengligini siqadi, ustma-ust tushishlarni sanaydi | AutoCAD |
| `xlsx_translate` | Excel kataklari tarjimasi (formula, raqam, varaq nomlari o'zgarmaydi) | — |
| `docx_to_pdf` | Sekretar xatlarini PDF qiladi (keyin direktorga imzoga ketadi) | Word yoki LibreOffice |
| `norm_control` | Norma Kontrol: format, ramkadan chiqqan va ustma-ust matnlar → zamechaniyalar ro'yxati | (DWG uchun AutoCAD) |

Natijalar platformaga hujjat reviziyasi bo'lib qaytadi va Google Drive'ga tushadi.
Telegram'da: «Zavod AR chizmalarini PDF qil», «KJ ni xitoy tiliga tarjima qil»,
«Zavod komplektini normokontroldan o'tkaz», «Zakazchikka xat tayyorla: ...».

## O'rnatish

1. Python 3.12 (python.org, «Add to PATH»).
2. Repodagi `worker/` papkasini kompyuterga ko'chiring, masalan `C:\GaztekWorker\worker`.
3. `cd C:\GaztekWorker` va `pip install -r worker\requirements.txt`
4. Platforma admin panelida: **Интеграции → Рабочий компьютер** — uzun tasodifiy token kiriting.
5. `worker\worker.ini.example` → `worker\worker.ini`, `server` va `token` ni yozing.
6. Sinov: `python -m worker.gaztek_worker` — admin panelda holat «Online» bo'ladi.
7. Avtomatik ishga tushirish: Task Scheduler → «At log on» (AutoCAD COM foydalanuvchi
   sessiyasida ishlaydi, Windows xizmati sifatida emas), Action:
   `pythonw.exe -m worker.gaztek_worker`, Start in: `C:\GaztekWorker`.
   Kompyuter o'zi tizimga kirishi uchun avtologinni yoqing va uyqu rejimini o'chiring.

## Eslatmalar

- AutoCAD bir vaqtda bitta ish bajaradi; agent ishlarni navbat bilan oladi.
- Ish 30 daqiqadan ko'p osilib qolsa, server uni qayta navbatga qo'yadi (3 urinish).
- Tarjima va shtamp birinchi marta sinov loyihasida tekshirilsin: shtamp atribut
  teglari kompaniya shabloniga qarab AI tomonidan moslanadi.
- «Eslab qol: …» bilan berilgan tuzatishlar (masalan, «matn ustma-ust tushmasin»)
  tarjimon va normokontrol promptlariga avtomatik qo'shiladi.
