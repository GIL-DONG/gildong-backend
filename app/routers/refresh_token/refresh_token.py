from fastapi import APIRouter,Request, HTTPException, Response
from jwt import ExpiredSignatureError, InvalidTokenError
import structlog

from core import get_payload
from core import common_parameters
from services import TokenManager

token_manager = TokenManager(common_parameters)
logger = structlog.get_logger()

router = APIRouter()

@router.post("/refresh-access-token")
async def refresh_access_token(request: Request):
    try:
        auth_header = request.headers.get("Authorization")
        data = get_payload(auth_header)
        new_access_token = token_manager.create_access_token(data)
        return {"message": "successfully!","access_token": new_access_token}
    
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail={"code": -3, "message": "Token has expired"})
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail={"code": -2, "message": "Invalid token"})
    except Exception as e:
        logger.error("An error occurred while fetching detail", error=str(e))  # 이 줄을 추가
        raise HTTPException(status_code=500, detail="An error occurred.")

@router.post("/refresh-refresh-token")
async def refresh_refresh_token(request: Request, response: Response):
    # Validate the refresh token from cookies
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")

    try:
        # Decode the refresh token
        data = get_payload(refresh_token)
        new_refresh_token = token_manager.create_refresh_token(data)
        response.set_cookie(key="refresh_token", value=new_refresh_token, httponly=True, max_age=1209600, samesite="lax", secure=True)
        
        logger.info("refreshing refresh_token", data=new_refresh_token)
        return {"message": "successfully! refresh_token" }
    
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail={"code": -3, "message": "Token has expired"})
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail={"code": -2, "message": "Invalid token"})
    except Exception as e:
        logger.error("An error occurred while fetching detail", error=str(e))  # 이 줄을 추가
        raise HTTPException(status_code=500, detail="An error occurred.")