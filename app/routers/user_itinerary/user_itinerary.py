from typing import Dict, List

import structlog
from fastapi import APIRouter, Query, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from jwt import ExpiredSignatureError, InvalidTokenError

from core import get_user_id
from routers.user_itinerary.router_config import parameters
from services import ElasticsearchDataManager, KakaoManager
from datetime import datetime, timedelta


logger = structlog.get_logger()
router = APIRouter()


class listResponse(BaseModel):
    data: List[Dict]

class dictResponse(BaseModel):
    data: Dict


db = ElasticsearchDataManager(parameters['elasticsearch_host'])

@router.get("/itinerary")
async def load_itineraries(request: Request):
    auth_header = request.headers.get("Authorization")
    user_id = get_user_id(auth_header)
    
    logger.info("Request received for load_itineraries", user_id=user_id)
    
    try:
        result = db.fetch_confirmed_itineraries(
            index_n=parameters['itinerary_index'], 
            user_id=user_id,
            source_fields=parameters['source_fields']
        )
        
        logger.info("Data fetched successfully in fetch_confirmed_itineraries.", data=result)
        
        return listResponse(data=result)
    
    except Exception as e:
        logger.error("An error occurred while fetching", error=str(e))
        raise HTTPException(status_code=500, detail="An error occurred.")

@router.get("/itinerary/detail")
async def load_itinerary(
    request: Request,
    itinerary_id: str = Query(..., description="The Itinerary id of the data to retrieve.")
):
    auth_header = request.headers.get("Authorization")
    user_id = get_user_id(auth_header)
    
    logger.info("Request received for load_itinerary", user_id=user_id, itinerary_id=itinerary_id)
    
    try:
        result = db.fetch_data(
            index_n=parameters['itinerary_index'], 
            doc_id=itinerary_id, 
            query_field="itinerary.uuid.keyword",
            source_fields=parameters['source_fields']
        )
        
        logger.info("Data fetched successfully in fetch_data.", data=result)
        
        return dictResponse(data=result['itinerary'])
    
    except Exception as e:
        logger.error("An error occurred while fetching", error=str(e))
        raise HTTPException(status_code=500, detail="An error occurred.")

@router.get("/itinerary/registration")
async def regist_itinerary(
    request: Request,
    itinerary_id: str = Query(..., description="The ID of the data to regist.")
):
    auth_header = request.headers.get("Authorization")
    user_id = get_user_id(auth_header)
    
    logger.info("Request received for regist_itinerary", user_id=user_id, itinerary_id=itinerary_id)
    
    try:
        itinerary_data = db.fetch_data(
            index_n=parameters['convo_index'], 
            doc_id=itinerary_id,
            query_field="itinerary.uuid.keyword",
            source_fields=parameters['source_fields']
        )
        
        logger.info("Data fetched successfully in fetch_data.", data=itinerary_data)
        
        db.index_confirmed_itinerary(
            index_n=parameters['itinerary_index'], 
            doc_id=itinerary_data["session_id"],
            data=itinerary_data
        )
        
        return JSONResponse(content={"message": "Itinerary registered successfully."}, status_code=200)
    
    except Exception as e:
        logger.error("An error occurred while fetching", error=str(e))
        return JSONResponse(content={"message": "An error occurred."}, status_code=500)

@router.delete("/itinerary/deletion")
async def delete_itinerary(
    request: Request,
    itinerary_id: str = Query(..., description="The ID of the data to delete.")
):
    auth_header = request.headers.get("Authorization")
    user_id = get_user_id(auth_header)
    
    logger.info("Request received for delete_itinerary", user_id=user_id, itinerary_id=itinerary_id)
    
    try:
        # Check if the itinerary data exists before deletion
        itinerary_data = db.fetch_data(
            index_n=parameters['convo_index'], 
            doc_id=itinerary_id,
            query_field="itinerary.uuid.keyword",
            source_fields=parameters['source_fields']
        )

        if not itinerary_data:
            return JSONResponse(content={"message": "Itinerary not found."}, status_code=404)

        logger.info("Data fetched successfully in fetch_data.", data=itinerary_data)

        # Delete the itinerary
        db.delete_confirmed_itinerary(
            index_n=parameters['itinerary_index'], 
            doc_id=itinerary_data["session_id"]
        )

        return JSONResponse(content={"message": "Itinerary deleted successfully."}, status_code=200)
    
    except Exception as e:
        logger.error("An error occurred while deleting", error=str(e))
        return JSONResponse(content={"message": "An error occurred."}, status_code=500)

@router.get("/itinerary/calendar")
async def send_kakao_calendar(
    token: str,
    request: Request,
    uuid: str
):  
    try: 
        auth_header = request.headers.get("Authorization")
        user_id = get_user_id(auth_header)

    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail={"code": -3, "message": "Token has expired"})
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail={"code": -2, "message": "Invalid token"})
    
    try:
        logger.info("fetching itinerary", uuid=uuid)
        itinerary_data = db.fetch_data(
            index_n=parameters['itinerary_index'], 
            doc_id=uuid, 
            query_field="itinerary.uuid.keyword", 
            source_fields=parameters['source_fields']
        )

        if itinerary_data["itinerary"]["schedule"][0]["date_type"] == "date":
            for data in itinerary_data["itinerary"]["schedule"]:
                start_datetime = datetime.fromisoformat(data["date"] + "T" + data["start_time"]) - timedelta(hours=9)
                end_datetime = datetime.fromisoformat(data["date"] + "T" + data["end_time"]) - timedelta(hours=9)

                if data["start_time"] >= data["end_time"]:
                    end_datetime = datetime.fromisoformat(data["date"] + "T" + "23:50:00") - timedelta(hours=9)

                data_json = {
                    "title": itinerary_data["itinerary"]["title"],
                    "time": {
                        "start_at": start_datetime.isoformat(),
                        "end_at": end_datetime.isoformat(),
                    },
                    "description": data["description"],
                    "location": {
                        "name": data["title"],
                        "latitude": data["location"]["lat"],
                        "longitude": data["location"]["lon"]
                    },
                    "reminders": [1440, 10080],  # 1 day before, 1 week before
                    "color": "MINT"
                }
                KakaoManager(token).create_caledar(data_json)
            return JSONResponse(content={"message": "successful"}, status_code=200)
        
        else:
            raise HTTPException(status_code=400, detail="Requires specific travel dates")
    
    except ValueError as ve: 
        logger.error("error", error=str(ve))
        raise HTTPException(status_code=400, detail= str(ve))
    # except Exception as e:
    #     logger.error("An error occurred while fetching detail", error=str(e))
    #     return JSONResponse(content={"message": str(e)}, status_code=400)
 
    # except Exception as e:
    #     raise HTTPException(status_code=400, detail=str(e))