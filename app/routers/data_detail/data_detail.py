from typing import Dict, Any

import structlog
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from routers.data_detail.router_config import parameters
from services import ElasticsearchDataManager


logger = structlog.get_logger()
router = APIRouter()


class Response(BaseModel):
    data: Dict[str, Any]


db = ElasticsearchDataManager(parameters['elasticsearch_host'])

@router.get("/data-detail", response_model=Response)
async def data_detail(data_id: str = Query(..., description="The ID of the data to retrieve.")):
    logger.info("Fetching detail", data_id=data_id)
    try:
        result = db.fetch_data(
            index_n=parameters['index_name'], 
            doc_id=data_id, 
            query_field="_id",
            source_fields=parameters['source_fields']
        )
        return Response(data=result)
    except Exception as e:
        logger.error("An error occurred while fetching detail", error=str(e))
        raise HTTPException(status_code=500, detail="An error occurred.")