from typing import Dict, List

import structlog
from fastapi import APIRouter, Query, HTTPException, Request
from pydantic import BaseModel

from core import get_user_id
from routers.user_convo.router_config import parameters
from services import ElasticsearchDataManager


logger = structlog.get_logger()
router = APIRouter()


class Response(BaseModel):
    data: List[Dict]


db = ElasticsearchDataManager(parameters['elasticsearch_host'])

@router.get("/convo", response_model=Response)
async def load_convo(
    request: Request, 
    session_id: str = Query(..., description="The ID of the data to retrieve.")
):
    auth_header = request.headers.get("Authorization")
    user_id = get_user_id(auth_header)

    logger.info("Request received for load_convo", user_id=user_id, session_id=session_id)
    
    try:
        result = db.fetch_memory(
            index_n=parameters['index_name'], 
            session_id=session_id, 
            source_fields=parameters['source_fields']
        )
        
        return Response(data=result)
    
    except Exception as e:
        logger.error("An error occurred while fetching detail", error=str(e))
        raise HTTPException(status_code=500, detail="An error occurred.")