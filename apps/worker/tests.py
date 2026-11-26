import base64
import io
import json
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Discipline, User
from apps.core.runtime_config import encrypt
from apps.documents.models import AuditLog, Document, DocumentVersion
from apps.projects.models import Project, Section, SubObject
from worker import textfit
from worker.localarchive import place

from .models import JobKind, JobStatus, WorkerJob
from .services import claim, create_job

TOKEN = "t" * 40
_MEDIA = tempfile.mkdtemp(prefix="worker-test-")
SEND = "apps.telegram_bot.services.send_message"
SEND_DOC = "apps.telegram_bot.services.send_document"


def pdf_with(*lines):
    """Kirill matnli PDF (reportlab + Tinos)."""
    from django.conf import settings
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

    pdfmetrics.registerFont(TTFont("Tinos", str(settings.BASE_DIR / "static/pult/fonts/Tinos-Regular.ttf")))
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.setFont("Tinos", 12)
    for x, y, text in lines:
        c.drawString(x, y, text)
    c.save()
    return buf.getvalue()


def png(color=(0, 0, 255, 120)):
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGBA", (60, 40), color).save(buf, "PNG")
    return buf.getvalue()


class TextFitTests(SimpleTestCase):
    def test_gost_profile_uses_named_setup_and_preserves_completed_stamp(self):
        from types import SimpleNamespace
        from worker.handlers.gost import apply_profile

        project = SimpleNamespace(TagString="PROJECT", TextString="Existing client")
        sheet = SimpleNamespace(TagString="SHEET", TextString="")
        stamp = SimpleNamespace(ObjectName="AcDbBlockReference", EffectiveName="A3 title", HasAttributes=True,
                                GetAttributes=lambda: [project, sheet])
        layout = SimpleNamespace(Name="Лист 1", CanonicalMediaName="A3", ModelType=False, TabOrder=1,
                                 Block=[stamp], CopyFrom=mock.Mock())
        doc = mock.Mock()
        doc.Layouts.Count, doc.Layouts.Item.return_value = 1, layout
        rule = {"page_setup": "A3 approved", "stamp_block": "A3 title", "attributes": {"PROJECT": "project", "SHEET": "sheet"}}
        profile = {"media": {"A3": rule}, "fonts": {"Notes": "test.shx"}}
        self.assertEqual(apply_profile(doc, profile, {"project": "Zavod", "file_name": "План этажа.dwg"}), 1)
        layout.CopyFrom.assert_called_once_with(doc.PlotConfigurations.Item.return_value)
        self.assertEqual(doc.TextStyles.Item.return_value.FontFile, "test.shx")
        self.assertEqual((sheet.TextString, project.TextString), ("Лист 1", "Existing client"))
        layout.CanonicalMediaName = "A0"
        with self.assertRaisesRegex(ValueError, "No approved format"):
            apply_profile(doc, profile, {"file_name": "Файл.dwg"})

    def test_codes_and_numbers_are_not_translated(self):
        for text in ("A-1", "Ø20", "М1:100", "+0.000", "КЖ-01", "2-2", "12", ""):
            self.assertFalse(textfit.needs_translation(text), text)
        for text in ("План 1 этажа", "Фасад в осях 1-5", "平面图", "Section A-A"):
            self.assertTrue(textfit.needs_translation(text), text)

    def test_max_len_keeps_translation_inside_the_frame(self):
        self.assertEqual(textfit.max_len("План этажа", "ru", "en"), 11)
        self.assertLess(textfit.max_len("План этажа", "ru", "zh"), 8)  # ieroglif ikki barobar keng

    def test_mtext_codes_survive(self):
        value = r"{\fArial|b1;План}\PЭтаж 1"
        parts = textfit.split_mtext(value)
        self.assertEqual([t for c, t in parts if not c], ["План", "Этаж 1"])
        swapped = [(c, {"План": "Plan", "Этаж 1": "Floor 1"}.get(t, t) if not c else t) for c, t in parts]
        self.assertEqual(textfit.join_mtext(swapped), r"{\fArial|b1;Plan}\PFloor 1")

    def test_overlaps_and_shrink(self):
        boxes = [("a", 0, 0, 10, 2), ("b", 5, 0.5, 15, 2.5), ("c", 20, 0, 30, 2)]
        self.assertEqual(textfit.overlaps(boxes), [("a", "b")])
        self.assertEqual(textfit.shrink_factor(10, 12.5), 0.8)
        self.assertIsNone(textfit.shrink_factor(10, 20))  # 0.5 — o'qib bo'lmaydi, sig'maydi
        self.assertEqual(textfit.shrink_factor(10, 9), 1.0)

    def test_sheet_formats(self):
        self.assertEqual(textfit.sheet_format(297, 210), "A4")
        self.assertEqual(textfit.sheet_format(891, 420), "A3x3")
        self.assertIsNone(textfit.sheet_format(300, 300))

    def test_local_old_keeps_file_name(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        src = root / "plan.dwg"
        src.write_bytes(b"v1")
        place(src, root / "out", ["Zavod", "Bino 1", "AR"], now=datetime(2026, 1, 1))
        src.write_bytes(b"v2")
        target = place(src, root / "out", ["Zavod", "Bino 1", "AR"], now=datetime(2026, 1, 2))
        self.assertEqual(target.read_bytes(), b"v2")
        self.assertEqual((root / "out/Zavod/Bino 1/AR/Old/20260102-000000/plan.dwg").read_bytes(), b"v1")

    def test_norm_control_facts_from_pdf(self):
        from worker.handlers.normcontrol import pdf_facts

        path = Path(tempfile.mkdtemp()) / "a.pdf"
        self.addCleanup(shutil.rmtree, path.parent, True)
        path.write_bytes(pdf_with((100, 500, "Наложенный текст"), (110, 502, "Второй текст"), (5, 300, "За рамкой")))
        facts = pdf_facts(path)[0]
        self.assertEqual(facts["format"], "A4")  # reportlab standart sahifasi
        joined = " ".join(facts["facts"])
        self.assertIn("overlapping text", joined)
        self.assertIn("outside the drawing frame", joined)
        self.assertNotIn("non-standard sheet size", joined)
        from openpyxl import load_workbook
        from worker.handlers.normcontrol import norm_control
        ctx = mock.Mock()
        ctx.ai.return_value = {"remarks": [{"sheet": "1", "severity": "minor", "issue": "За рамкой", "issue_en": "Outside frame"}]}
        out = norm_control({"file_name": path.name}, path, ctx)
        book = load_workbook(out.file, read_only=True)
        self.assertEqual(tuple(book.active.values)[1], (path.name, "1", "minor", "За рамкой", "Outside frame"))
        book.close()


class SigningTests(SimpleTestCase):
    def test_signature_goes_next_to_director(self):
        from pypdf import PdfReader

        from apps.documents.signing import find_label, sign_pdf

        pdf = pdf_with((72, 700, "Письмо"), (72, 150, "Директор ООО «GASTEC PROJECT»"))
        self.assertEqual(len(find_label(PdfReader(io.BytesIO(pdf)))), 1)
        signed = PdfReader(io.BytesIO(sign_pdf(pdf, png(), png((200, 0, 0, 90)))))
        self.assertEqual(len(signed.pages[0]["/Resources"]["/XObject"]), 2)

    def test_no_label(self):
        from apps.documents.signing import LabelNotFound, sign_pdf

        with self.assertRaises(LabelNotFound):
            sign_pdf(pdf_with((72, 700, "Без подписи")), png())


@override_settings(MEDIA_ROOT=_MEDIA, WORKER_TOKEN=TOKEN)
class WorkerApiTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_MEDIA, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user(email="u@example.com", password="x", full_name="Ali", role=User.Role.MANAGER,
                                             telegram_chat_id="500")
        self.project = Project.objects.create(name="Zavod", created_by=self.user)
        ar, _ = Discipline.objects.get_or_create(code="AR", defaults={"name": "Arxitektura"})
        self.section = Section.objects.create(project=self.project, discipline=ar, name="AR",
                                              sub_object=SubObject.objects.create(project=self.project, name="Bino 1"))
        self.doc = Document.objects.create(name="Plan", project=self.project, section=self.section, uploaded_by=self.user,
                                           file=SimpleUploadedFile("plan 1.dwg", b"DWG"), file_size=3)
        DocumentVersion.objects.create(document=self.doc, version_number="1.0", file=self.doc.file.name, file_size=3,
                                       uploaded_by=self.user)
        self.auth = {"HTTP_AUTHORIZATION": f"Bearer {TOKEN}"}
        for target in (SEND, SEND_DOC):
            patcher = mock.patch(target, return_value=True)
            setattr(self, "send" if target == SEND else "send_doc", patcher.start())
            self.addCleanup(patcher.stop)

    def post(self, name, body=None, **kw):
        return self.client.post(reverse(f"worker:{name}", kwargs=kw), json.dumps(body or {}),
                                content_type="application/json", **self.auth)

    def test_token_is_required(self):
        self.assertEqual(self.client.post(reverse("worker:claim")).status_code, 401)
        self.assertEqual(self.client.post(reverse("worker:claim"), HTTP_AUTHORIZATION="Bearer wrong").status_code, 401)

    def test_full_cycle_pdf_and_stamped_source(self):
        job = create_job(JobKind.DWG_PRINT, self.doc, self.user)
        data = self.post("claim", {"worker": "pc1", "kinds": ["dwg_print"]}).json()["job"]
        self.assertEqual((data["id"], data["file_name"], data["discipline"], data["object"]),
                         (str(job.pk), "plan 1.dwg", "AR", "Bino 1"))
        self.assertIsNone(self.post("claim", {"worker": "pc1"}).json()["job"])  # ikkinchi marta berilmaydi
        response = self.client.get(reverse("worker:input", args=[job.pk]), **self.auth)
        self.assertEqual(b"".join(response.streaming_content), b"DWG")
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("worker:result", args=[job.pk]), {
                "ok": "1", "result": json.dumps({"summary": "Штамп: 3"}),
                "file": SimpleUploadedFile("plan 1.pdf", b"%PDF"), "source": SimpleUploadedFile("plan 1.dwg", b"DWG2"),
            }, **self.auth)
        job.refresh_from_db()
        self.assertEqual(job.status, JobStatus.DONE)
        pdf = job.result_document
        self.assertEqual((pdf.original_name, pdf.section_id, pdf.name), ("plan 1.pdf", self.section.pk, "Plan (PDF)"))
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.versions.count(), 2)  # shtamp to'ldirilgan DWG — yangi reviziya
        self.assertEqual(self.send_doc.call_args.args[2], "plan 1.pdf")

    def test_translation_keeps_file_name_as_revision(self):
        job = create_job(JobKind.DWG_TRANSLATE, self.doc, self.user, params={"target_lang": "zh"})
        claim("pc1")
        self.client.post(reverse("worker:result", args=[job.pk]), {
            "ok": "1", "result": "{}", "file": SimpleUploadedFile("plan 1.dwg", b"ZH")}, **self.auth)
        self.assertEqual(Document.objects.count(), 1)
        self.doc.refresh_from_db()
        self.assertEqual((self.doc.original_name, self.doc.versions.count()), ("plan 1.dwg", 2))

    def test_retryable_error_requeues_and_final_error_notifies(self):
        job = create_job(JobKind.DWG_PRINT, self.doc, self.user)
        claim("pc1")
        self.client.post(reverse("worker:result", args=[job.pk]), {"ok": "0", "error": "AutoCAD busy",
                                                                   "result": json.dumps({"retry": True})}, **self.auth)
        job.refresh_from_db()
        self.assertEqual(job.status, JobStatus.QUEUED)
        claim("pc1")
        self.client.post(reverse("worker:result", args=[job.pk]), {"ok": "0", "error": "bad file"}, **self.auth)
        job.refresh_from_db()
        self.assertEqual(job.status, JobStatus.ERROR)
        self.assertIn("bad file", self.send.call_args.args[1])

    def test_stale_running_job_is_given_again(self):
        job = create_job(JobKind.DWG_PRINT, self.doc, self.user)
        claim("pc1")
        WorkerJob.objects.filter(pk=job.pk).update(started_at=timezone.now() - timedelta(hours=1))
        self.assertEqual(claim("pc2").pk, job.pk)

    def test_ai_proxy_adds_user_rules(self):
        from apps.ai_agents.models import AgentMemory

        AgentMemory.objects.create(user=self.user, agent="translator", text="matn ustma-ust tushmasin")
        job = create_job(JobKind.DWG_TRANSLATE, self.doc, self.user, params={"target_lang": "en"})
        claim("pc1")
        with mock.patch("apps.ai_agents.services.ask_json", return_value={"items": []}) as ask:
            response = self.post("ai", {"job": str(job.pk), "agent": "translator", "input": {"target": "en", "items": []}})
        self.assertEqual(response.json(), {"ok": True, "data": {"items": []}})
        self.assertIn("ustma-ust", ask.call_args.args[0])
        self.assertEqual(self.post("ai", {"job": str(job.pk), "agent": "treasurer", "input": {}}).status_code, 400)

    def test_norm_control_remarks_are_sent(self):
        pdf_doc = Document.objects.create(name="Set", project=self.project, uploaded_by=self.user,
                                          file=SimpleUploadedFile("set.pdf", b"%PDF"), file_size=4)
        DocumentVersion.objects.create(document=pdf_doc, version_number="1.0", file=pdf_doc.file.name, uploaded_by=self.user)
        job = create_job(JobKind.NORM_CONTROL, pdf_doc, self.user)
        claim("pc1")
        remarks = [{"sheet": "3", "issue": "Наложение текста в штампе", "severity": "critical"}]
        self.client.post(reverse("worker:result", args=[job.pk]), {"ok": "1", "result": json.dumps({"remarks": remarks})},
                         **self.auth)
        self.assertIn("Наложение текста", self.send.call_args.args[1])

    def test_orchestrator_queues_jobs_for_matching_files(self):
        from apps.ai_agents import orchestrator

        data = {"project": "Zavod", "object": "", "discipline": "AR", "file": "", "target_lang": ""}
        with mock.patch("apps.ai_agents.orchestrator.ask_json", return_value=data):
            reply = orchestrator.handle(self.user, "Zavod AR chizmalarini PDF qil", "uz")
        self.assertIn("1", reply.text)
        self.assertEqual(WorkerJob.objects.get().kind, JobKind.DWG_PRINT)

    def test_drawing_pipeline_chains_revisions_and_skips_duplicate_result(self):
        from apps.ai_agents import orchestrator
        from .services import finish

        selection = {"project": "Zavod", "object": "", "discipline": "AR", "file": "", "target_lang": ""}
        with mock.patch("apps.ai_agents.orchestrator.ask_json", return_value=selection):
            orchestrator.handle(self.user, "Zavod chizmalar konveyeri", "uz")
        first = claim("cad")
        self.assertEqual((first.kind, first.params["preserve_english"]), (JobKind.DWG_TRANSLATE, True))
        original = first.version
        finish(first, True, {}, "plan 1.dwg", b"translated")
        finish(first, True, {}, "plan 1.dwg", b"duplicate")
        self.assertEqual(WorkerJob.objects.count(), 2)
        gost = claim("cad")
        self.assertEqual(gost.kind, JobKind.GOST_FORMAT)
        finish(gost, True, {}, "plan 1.dwg", b"formatted")
        check = claim("cad")
        self.assertEqual(check.kind, JobKind.NORM_CONTROL)
        finish(check, True, {"remarks": []}, "plan 1.remarks.xlsx", b"report")
        printer = claim("cad")
        self.assertEqual((printer.kind, printer.version_id), (JobKind.DWG_PRINT, check.version_id))
        output = finish(printer, True, {}, "plan 1.pdf", b"%PDF-test")
        self.assertEqual(output.result_document.original_name, "plan 1.pdf")
        self.assertEqual(output.result_document.versions.get().mdr_state, "pending")
        with original.file.open("rb") as source:
            self.assertEqual(source.read(), b"DWG")

    @override_settings(GASTEC_MDR_SPREADSHEET_ID="test", GASTEC_MDR_TAB="MDR",
                       GASTEC_MDR_COLUMNS={"filename": "Файл", "link": "Ссылка"})
    def test_mdr_appends_only_mapped_fields_and_recovers_after_lost_response(self):
        from apps.documents.mdr import sync_revision
        from requests import Timeout

        version = self.doc.versions.get()
        version.drive_file_id, version.mdr_state = "drive-file", "pending"
        version.save(update_fields=["drive_file_id", "mdr_state"])
        sheet = {"properties": {"title": "MDR", "sheetId": 125}}
        def response(data):
            result = mock.Mock()
            result.json.return_value = data
            return result
        with mock.patch("apps.documents.mdr.drive._session") as session:
            http = session.return_value
            http.get.side_effect = [response({"sheets": [sheet]}), response({"values": [["Файл", "Формула", "Ссылка"]]}),
                                    response({"sheets": [sheet], "namedRanges": [
                                        {"name": f"GASTEC_MDR_{version.pk.hex}", "range": {"sheetId": 125}}]})]
            http.post.side_effect = Timeout("lost response")
            sync_revision(version)
            self.assertEqual(http.post.call_args.kwargs["json"]["requests"][1]["appendCells"]["rows"][0]["values"][1], {})
            version.refresh_from_db()
            self.assertEqual(version.mdr_state, "pending")
            sync_revision(version)
            version.refresh_from_db()
            self.assertEqual(version.mdr_state, "synced")
            self.assertEqual(http.post.call_count, 1)


@override_settings(MEDIA_ROOT=_MEDIA)
class SecretaryTests(TestCase):
    def setUp(self):
        from apps.pult.models import SealImage

        self.director = User.objects.create_user(email="d@example.com", password="x", full_name="Direktor",
                                                 role=User.Role.ADMIN, telegram_chat_id="700")
        self.clerk = User.objects.create_user(email="c@example.com", password="x", full_name="Kotiba",
                                              role=User.Role.MANAGER, telegram_chat_id="701")
        for kind in ("seal", "sign"):
            SealImage.objects.create(kind=kind, encrypted=encrypt(base64.b64encode(png()).decode()))
        for target in (SEND, SEND_DOC):
            patcher = mock.patch(target, return_value=True)
            setattr(self, "send" if target == SEND else "send_doc", patcher.start())
            self.addCleanup(patcher.stop)

    def test_letter_draft_pdf_approval_and_seal(self):
        from apps.ai_agents import secretary

        from .services import finish

        letter = {"title": "Письмо о сроках", "addressee": "Директору ООО «Заказчик»", "body": "Сообщаем...",
                  "signature_label": "Директор"}
        with mock.patch("apps.ai_agents.secretary.ask_json", return_value=letter):
            reply = secretary.draft(self.clerk, "Zakazchikka muddatlar haqida xat tayyorla", "uz")
        self.assertIn("Письмо о сроках", reply.text)
        job = WorkerJob.objects.get()
        self.assertEqual((job.kind, job.then), (JobKind.DOCX_TO_PDF, "secretary_review"))
        self.assertTrue(job.document.original_name.endswith(".docx"))

        claim("pc1")
        pdf = pdf_with((72, 700, "Письмо о сроках"), (72, 150, "Директор ООО «GASTEC PROJECT»"))
        finish(WorkerJob.objects.get(), True, {}, "Письмо_о_сроках.pdf", pdf)
        doc = WorkerJob.objects.get().result_document
        buttons = self.send.call_args.kwargs["buttons"]
        self.assertEqual(self.send.call_args.args[0], "700")  # faqat imzo huquqi bor direktorga
        self.assertEqual(buttons[0][0][1], f"sg:ok:{doc.pk}")

        self.assertIn("faqat", secretary.decide(self.clerk, f"sg:ok:{doc.pk}", "uz").text)  # kotiba imzolay olmaydi
        done = secretary.decide(self.director, f"sg:ok:{doc.pk}", "uz")
        self.assertIn("imzolandi", done.text)
        doc.refresh_from_db()
        self.assertTrue(AuditLog.objects.filter(object_id=str(doc.pk), action="signed").exists())
        self.assertEqual({c.args[0] for c in self.send_doc.call_args_list[-2:]}, {"700", "701"})
        self.assertNotIn("imzolandi", secretary.decide(self.director, f"sg:ok:{doc.pk}", "uz").text)  # ikki marta emas

    def test_pdf_from_telegram_goes_to_director(self):
        from apps.ai_agents import secretary

        reply = secretary.submit_pdf(self.clerk, "akt.pdf", pdf_with((72, 150, "Директор")), "uz")
        self.assertIn("direktorga", reply.text)
        self.assertEqual(self.send.call_args.args[0], "700")
        self.assertIn("PDF", secretary.submit_pdf(self.clerk, "akt.docx", b"x", "uz").text)

