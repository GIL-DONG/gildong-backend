from jwt import ExpiredSignatureError, InvalidTokenError
from fastapi import HTTPException

from services import TokenManager


def get_user_id(auth_header: str):
    from core.common_config import common_parameters
    
    token_manager = TokenManager(common_parameters)
    
    try:
        access_token = auth_header.replace("Bearer ", "").strip()
        _, decoded_access_token = token_manager.decode_token(access_token)  # 토큰 검증
        user_id = decoded_access_token.get("user_id")

        return user_id
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    

def get_payload(auth_header: str):
    from core.common_config import common_parameters
    
    token_manager = TokenManager(common_parameters)
    
    try:
        access_token = auth_header.replace("Bearer ", "").strip()
        payload= token_manager.payload_data(access_token) 
        return payload
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))