from typing import Dict, List, Optional
import structlog
from fastapi import APIRouter, Query, HTTPException, Request, status, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from core import get_user_id
from routers.user_login.router_config import parameters
from services import ElasticsearchDataManager, KakaoManager
from services import TokenManager
from core import common_parameters
from jwt import ExpiredSignatureError, InvalidTokenError
 
logger = structlog.get_logger()
router = APIRouter()
#**service**
db = ElasticsearchDataManager(parameters['elasticsearch_host'])
token_manager = TokenManager(common_parameters)

# class Response(BaseModel):
#     data: List[Dict]

class User(BaseModel):
    Email:  Optional[str] = None
    age: Optional[int] = None
    age_group: int
    disability_status: bool
    disability_type: Optional[str] = None  # This field can be omitted
    gender: str
    prefer_travel: list
    residence: dict  # Geo point can be represented as dict
    significant: Optional[str] = None
    userID: str
    user_name: str
    user_photo : str

class UserName(BaseModel):
    user_name: str


class Userinfo(BaseModel):
    user_name: Optional[str] = None
    user_photo: Optional[str] = None

 
@router.get("/login")
async def login(
    token:str,
    request: Request,
    response: Response):
    
    userinfo = KakaoManager(token=token).get_user_info()
    logger.info("kakao_get_userinfo", userinfo=userinfo)
    
    #payload data
    kakao_user_id = userinfo.get("id")
    
    try:
        result = db.fetch_userinfo(
            index_n=parameters['index_name'], 
            user_id=kakao_user_id, 
        )

        data= {"user_id": kakao_user_id}
        if result["user_photo"] and result["user_name"]:
            data.update({"user_id": kakao_user_id, "user_name": result["user_name"], "user_image": result["user_photo"], "disability_status": result["disability_status"] })
        if result["disability_status"]:
            data.update({"disability_type": result["disability_type"]})
        access_token =token_manager.create_access_token(data)
        refresh_token = token_manager.create_refresh_token(data)
        # Set the refresh token as an HTTP-only cookie with Secure attribute
        response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, max_age=1209600, samesite=None, secure=True )  # 1209600 seconds = 2 weeks 
        
        logger.info("access_token in login", data=access_token)
        logger.info("refresh_token in login", data=refresh_token)

        return JSONResponse(
                    status_code=200,
                    content={
                        "message": "Logged in successfully",
                        "data": {
                            "access_token": access_token,
                            "expires_in": "8 Hours"
                        }
                    }
                )

    except ValueError as ve: 
        logger.error("User not registered in Elasticsearch", error=str(ve))
        return JSONResponse(
                        status_code=200,
                        content={
                            "message": "User not registered. Please sign up first.",
                            "data": userinfo} ) 
    except Exception as e:
        logger.error("An error occurred while fetching detail", error=str(e))  # 이 줄을 추가
        raise HTTPException(status_code=500, detail="An error occurred.")
    

    
@router.get("/login_test")
async def login_test(user_id:str):
    logger.info("logining test_id", user_id=user_id)

    try:
        result = db.fetch_userinfo(
            index_n=parameters['index_name'], 
            user_id=user_id, 
        )
        data= {"user_id": user_id}
        if result["user_photo"] and result["user_name"]:
            data.update({"user_id": user_id, "user_name": result["user_name"], "user_image": result["user_photo"], "disability_status": result["disability_status"] })
        if result["disability_status"]:
            data.update({"disability_type": result["disability_type"]})

        access_token =token_manager.create_access_token(data)
        # refresh_token =token_manager.create_refresh_token(data)

        return JSONResponse(
                    status_code=200,
                    content={
                        "message": "Logged in successfully",
                        "data": {
                            "access_token": access_token,
                            "expires_in": "8 Hours"
                        }
                    }
                )

    except ValueError as ve: 
        return JSONResponse(
                        status_code=200,
                        content={
                            "message": "User not registered. Please sign up first.",
                            "data": user_id} ) 
    except Exception as e:
        logger.error("An error occurred while fetching detail", error=str(e))  # 이 줄을 추가
        raise HTTPException(status_code=500, detail="An error occurred.")

@router.post("/users/register")
async def register_user(user: User, request: Request, response: Response): #response: Response, 
    data = {"user_id": user.userID}
    try: 
        es_create = db.update_user_info(index_n=parameters['index_name'], body = user.dict())
        logger.info("indexing userinfo in es.", data=user.dict())
        if es_create == 'created' and user.user_photo:
            data.update({"user_name": user.user_name, "user_image": user.user_photo, "disability_status": user.disability_status})
            if user.disability_status:
                data.update({"disability_type": user.disability_type})

         
        access_token = token_manager.create_access_token(data)
        logger.info("access_token in register", data=access_token)
        refresh_token = token_manager.create_refresh_token(data)
        # Set refresh_token as HTTP only cookie
        response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, max_age=1209600, samesite="lax", secure=True)
        
        return {"message": "User registered successfully!", "access_token": access_token}

    except ValueError as ve: 
        logger.error("Registration failed!", error=str(ve))
        raise HTTPException(status_code=400, detail="Registration failed!", userid=user.userID)
    except Exception as e:
        logger.error("An error occurred while fetching detail", error=str(e))  # 이 줄을 추가
        raise HTTPException(status_code=500, detail="An error occurred.")


@router.post("/users/check-username")
async def check_username(user_name: UserName):
    try:
        res = db.fetch_username(index_n=parameters['index_name'], username=user_name.user_name)
        if res['hits']['total']['value'] > 0:
            return {"detail": "Username already exists!"}
        return Response(status_code=status.HTTP_204_NO_CONTENT) 

    except Exception as e:
        logger.error("An error occurred while fetching detail", error=str(e))  # 이 줄을 추가
        raise HTTPException(status_code=500, detail="An error occurred.")


@router.patch("/users/update-userinfo")
async def update_user_info(user_info: Userinfo, request: Request): 
    auth_header = request.headers.get("Authorization")
    user_id = get_user_id(auth_header)
    logger.info("Fetching update-userinfo", user_info=user_info)
    # # Validate the refresh token from cookies
    # refresh_token = request.cookies.get("refresh_token")
    # if not refresh_token:
    #     raise HTTPException(status_code=400, detail="Refresh token missing")
    
    # # Try to decode the refresh token (it will raise an error if it's invalid or expired)
    # _, _ = decode_token(refresh_token)
    try:
        doc_id = db.fetch_userinfo(index_n=parameters['index_name'], user_id=user_id, doc_id=True)
        db.update_userinfo(index_n=parameters['index_name'], id=doc_id, username=user_info.user_name, userphoto=user_info.user_photo)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except ValueError as ve: 
        logger.error("ValueError", error=str(ve))
        raise HTTPException(status_code=400, detail= {"code": -1, "message": str(ve)})
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail={"code": -3, "message": "Token has expired"})
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail={"code": -2, "message": "Invalid token"})
    except Exception as e:
        logger.error("An error occurred while fetching detail", error=str(e))  # 이 줄을 추가
        raise HTTPException(status_code=500, detail="An error occurred.")

@router.delete("/users/delete-userinfo")
async def delete_user_info(request: Request): #request: Request
    auth_header = request.headers.get("Authorization")
    user_id = get_user_id(auth_header)
    logger.info("delete userinfo", user_id=user_id)
    # # Validate the refresh token from cookies
    # refresh_token = request.cookies.get("refresh_token")
    # if not refresh_token:
    #     raise HTTPException(status_code=400, detail="Refresh token missing")
    # # Try to decode the refresh token (it will raise an error if it's invalid or expired)
    # _, _ = decode_token(refresh_token)
    try:        
        doc_id = db.fetch_userinfo(index_n=parameters['index_name'], user_id=user_id, doc_id=True)
        db.delete_userinfo(index_n=parameters['index_name'], id=doc_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except ValueError as ve: 
        logger.error("User not found", error=str(ve))
        raise HTTPException(status_code=400, detail= {"code": -1, "message": "User not found!"})
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail={"code": -3, "message": "Token has expired"})
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail={"code": -2, "message": "Invalid token"})
    except Exception as e:
        logger.error("An error occurred while fetching detail", error=str(e))  # 이 줄을 추가
        raise HTTPException(status_code=500, detail="An error occurred.")
