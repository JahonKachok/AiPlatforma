"""Append the released PDF revision to the configured Google Sheets document register."""
from urllib.parse import quote

import requests
from django.conf import settings

from . import drive
from .models import AuditLog, DocumentVersion
from .services import file_basename


def row_cells(headers, columns, version):
    section = version.document.section
    values = {"project": version.document.project.name, "filename": file_basename(version),
              "link": f"https://drive.google.com/open?id={version.drive_file_id}", "revision": version.version_number,
              "discipline": section.discipline.code if section else "",
              "object": section.sub_object.name if section and section.sub_object_id else ""}
    if not isinstance(columns, dict) or not {"link", "filename"} <= columns.keys() or columns.keys() - values.keys():
        raise ValueError("Check the MDR column mapping (filename and link are required)")
    cells = [{} for _ in headers]
    for field, title in columns.items():
        if not title or headers.count(title) != 1:
            raise ValueError(f"Missing or ambiguous MDR header: {title}")
        index = headers.index(title)
        if cells[index]:
            raise ValueError(f"Duplicate MDR column mapping: {title}")
        cells[index] = {"userEnteredValue": {"stringValue": str(values[field])}}
    return cells


def append_revision(version):
    book = settings.GASTEC_MDR_SPREADSHEET_ID
    row = settings.GASTEC_MDR_HEADER_ROW
    if not book or row < 1:
        raise ValueError("Set the MDR spreadsheet ID and header row")
    tab = settings.GASTEC_MDR_TAB
    marker = f"GASTEC_MDR_{version.pk.hex}"
    url = "https://sheets.googleapis.com/v4/spreadsheets/" + quote(book, safe="")
    session = drive._session()
    meta = session.get(url, params={"fields":"sheets(properties(sheetId,title)),namedRanges(name,range(sheetId))"},
                       timeout=drive.TIMEOUT)
    meta.raise_for_status()
    metadata = meta.json()
    sheet = next((s["properties"] for s in metadata["sheets"] if s["properties"]["title"] == tab), None)
    if sheet is None:
        raise ValueError("MDR tab not found")
    sheet_id = sheet["sheetId"]
    if any(r["name"] == marker and r["range"].get("sheetId", 0) == sheet_id for r in metadata.get("namedRanges", [])):
        return
    header_range = "'" + tab.replace("'", "''") + f"'!{row}:{row}"
    response = session.get(url + "/values/" + quote(header_range, safe=""), timeout=drive.TIMEOUT)
    response.raise_for_status()
    rows = response.json().get("values", [])
    cells = row_cells(rows[0] if rows else [], settings.GASTEC_MDR_COLUMNS, version)
    # Both requests commit together. A lost HTTP response can safely be retried.
    address = {"sheetId": sheet_id, "startRowIndex": row - 1, "endRowIndex": row,
               "startColumnIndex": 0, "endColumnIndex": 1}
    batch = [{"addNamedRange": {"namedRange": {"name": marker, "range": address}}},
             {"appendCells": {"sheetId": sheet_id, "rows": [{"values": cells}], "fields": "userEnteredValue"}}]
    response = session.post(url + ":batchUpdate", json={"requests": batch}, timeout=drive.TIMEOUT)
    response.raise_for_status()


def sync_revision(version):
    if version.mdr_state != "pending" or not version.drive_file_id:
        return
    try:
        append_revision(version)
    except (drive.DriveError, requests.RequestException, ValueError) as exc:
        message = f"Google Sheets HTTP {exc.response.status_code}" if isinstance(exc, requests.HTTPError) and exc.response is not None else str(exc)
        DocumentVersion.objects.filter(pk=version.pk, mdr_state="pending").update(mdr_error=message[:300])
    else:
        if DocumentVersion.objects.filter(pk=version.pk, mdr_state="pending").update(mdr_state="synced", mdr_error=""):
            AuditLog.log(obj=version, user=version.uploaded_by, action="mdr_registered",
                         details={"spreadsheet": settings.GASTEC_MDR_SPREADSHEET_ID, "tab": settings.GASTEC_MDR_TAB})
