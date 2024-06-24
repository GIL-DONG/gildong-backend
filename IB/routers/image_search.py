from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from typing import List
import os
import json
from datetime import datetime
from pydantic import BaseModel
import numpy as np
import structlog
from typing import Union
import data
import torch
from models import imagebind_model
from models.imagebind_model import ModalityType
from routers.router_config import parameters
from services import ElasticsearchDataManager

router = APIRouter()

# 정적 파일 디렉터리 등록 (예: 이미지를 저장하는 디렉터리)
# router.mount("/static", StaticFiles(directory="uploads"), name="static")

# 업로드된 파일을 저장할 디렉토리 경로
UPLOAD_DIR = "/home/pcn/RnS/test/wslee/project/gildong/app/uploads/images/"
# UPLOAD_DIR = "/home/pcn/RnS/test/wslee/project/gildong_test/app/uploads/images"

class FileUploadResponse(BaseModel):
    fileUrls: List[str]

device = "cuda:0" if torch.cuda.is_available() else "cpu"

# Instantiate model
model = imagebind_model.imagebind_huge(pretrained=True)
#model.eval()
model.to(device)

router = APIRouter()

logger = structlog.get_logger()
db = ElasticsearchDataManager(parameters['elasticsearch_host'])

def embeddings(url):
    inputs = {
    ModalityType.VISION: data.load_and_transform_vision_data([url], device)
    }
    with torch.no_grad():
        embeddings = model(inputs)
    return embeddings

def round5(body):
    body = np.round(body.tolist(), 5)
    body = body.tolist()
    return body

def script_query(embed, source):
    script_query_text = {
        "_source" : [
            "title", 
            "contenttypeid", 
            "overview_summ", 
            "physical_en", 
            "visual_en", 
            "hearing_en", 
            "location"
        ],
        "size" : 10,
  "query": {
    "script_score": {
      "query": {
        "exists": {"field": "imagebind_vector"}
      },
      "script": {
        "source": source,
        "params": {
          "query_vector": embed
        }
      }
    }
  }
}

    return script_query_text


def search(es,script_query,index,size):
        result = es.search(
            index=index,
            query=script_query,size = size)
        
        return result

# UPLOAD_DIR = "/home/pcn/RnS/test/wslee/project/gildong_test/IB/uploads/images"

# @router.post("/upload_images", response_model=FileUploadResponse)
# async def upload_images(in_files: List[UploadFile]):

#     for file in in_files:
#         currentTime = datetime.now().strftime("%Y%m%d%H%M%S")
#         saved_file_name = ''.join([currentTime, '_', file.filename])
#         file_location = os.path.join(UPLOAD_DIR, saved_file_name)
#         with open(file_location, "wb") as file_object:
#             file_object.write(file.file.read())

#     return FileResponse(file_location)

# @router.get("/view-image/{file_name}")
# async def view_image(file_name: str):
#     file_path = os.path.join(UPLOAD_DIR, file_name)
#     if not os.path.exists(file_path):
#         raise HTTPException(status_code=404, detail="File not found")
#     return FileResponse(file_path), file_path

@router.post("/search_image")
async def search_image(file_name: dict):
    file_name = file_name.get("file_name")  # 요청 데이터에서 "file_name" 키의 값을 가져옴
    file_path = os.path.join(UPLOAD_DIR, file_name)
    array_img = embeddings(file_path)
    query_vector = array_img[ModalityType.VISION].tolist()[0]  # PyTorch Tensor를 Python 리스트로 변환
    script_query_img = script_query(query_vector, "cosineSimilarity(params.query_vector, 'imagebind_vector') + 1.0")
    res = db.fetch_region(index_n=parameters['index_name'], body=script_query_img)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    json_string = json.dumps(res['hits']['hits'])
    return Response(json_string, media_type='application/json')

