import os
import uuid
import aiofiles
from fastapi import UploadFile, HTTPException
from app.config import settings


async def save_upload_file(file: UploadFile, subfolder: str = "general") -> tuple[str, int]:
    upload_dir = os.path.join(settings.UPLOAD_DIR, subfolder)
    os.makedirs(upload_dir, exist_ok=True)

    ext = os.path.splitext(file.filename or "file")[1]
    unique_filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(upload_dir, unique_filename)

    content = await file.read()
    file_size = len(content)

    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large")

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    return file_path, file_size


def delete_file(file_path: str) -> None:
    if file_path and os.path.exists(file_path):
        os.remove(file_path)


def get_file_url(file_path: str) -> str:
    return f"/{file_path.replace(os.sep, '/')}"
