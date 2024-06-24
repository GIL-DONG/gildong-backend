from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import List
import os
from datetime import datetime
from pydantic import BaseModel

router = APIRouter()

# 정적 파일 디렉터리 등록 (예: 이미지를 저장하는 디렉터리)
router.mount("/static", StaticFiles(directory="uploads"), name="static")

class FileUploadResponse(BaseModel):
    fileUrls: List[str]

UPLOAD_DIR = "uploads/images"

@router.post("/upload_images", response_model=FileUploadResponse)
async def upload_images(in_files: List[UploadFile]):
    file_urls = []

    for file in in_files:
        currentTime = datetime.now().strftime("%Y%m%d%H%M%S")
        saved_file_name = ''.join([currentTime, '_', file.filename])
        file_location = os.path.join(UPLOAD_DIR, saved_file_name)
        with open(file_location, "wb") as file_object:
            file_object.write(file.file.read())

        # 업로드된 파일의 URL 생성
        file_url = f"{saved_file_name}"  # 예: /static/20231015150610_l_2020080401000347500024081.jpg
        file_urls.append(file_url)

    return FileUploadResponse(fileUrls=file_urls)

@router.get("/view-image/{file_name}")
async def view_image(file_name: str):
    file_path = os.path.join(UPLOAD_DIR, file_name)
    return FileResponse(file_path)