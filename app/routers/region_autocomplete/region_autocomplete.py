from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import structlog
from typing import Optional
from services import ElasticsearchDataManager
from routers.region_autocomplete.router_config import parameters

router = APIRouter()

logger = structlog.get_logger()
db = ElasticsearchDataManager(parameters['elasticsearch_host'])

class AutoComplete(BaseModel):
    autocomplete: str

@router.get("/region/autocomplete")
async def autocomplete(
    autocomplete: str = Query(..., description="Search query for autocomplete"),
    page: int = Query(1, description="Page number (default: 1)"),
    page_size: int = Query(10, description="Number of results per page (default: 10)"),
):
    try:
        logger.info("region_autocomplte", autocomplete=autocomplete, page=page, page_size=page_size)
        from_item = (page - 1) * page_size
        body = {
            "from": from_item,
            "size": page_size,
            "query": {
                "multi_match": {
                    "query": autocomplete,
                    "type": "phrase_prefix",
                    "fields": ["word", "city^10", "district"]
                }
            }
        }
        res = db.fetch_region(index_n=parameters['index_name'], body=body)
        result = [] 
        for i in res['hits']['hits']:
            result.append(i['_source'])
        result_fin = {"result" : result,
                           "total" : res['hits']['total']['value']}
        return result_fin
    
    except Exception as e:
        logger.error("An error occurred while fetching detail", error=str(e))  # 이 줄을 추가
        raise HTTPException(status_code=500, detail="An error occurred.")