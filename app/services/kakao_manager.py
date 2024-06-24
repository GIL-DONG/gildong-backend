from fastapi import APIRouter, HTTPException
import requests
from core import common_parameters

import json

class KakaoManager:

    def __init__(self, token:str):
        self.token = token

    def get_user_info(self):
        headers = {
            "Authorization": f"Bearer {self.token}"
        }
        kakao_response = requests.post(common_parameters["KAKAO_USER_INFO_URL"], headers=headers)
        
        # 카카오 응답에 오류가 있을 경우
        if kakao_response.status_code != 200:
            raise HTTPException(status_code=401, detail={"message": "Invalid or expired token provided.", "kakao_response": kakao_response.json()})

        return kakao_response.json()
    
    def create_caledar(self, data_json):
        headers = {
            "Authorization": f"Bearer {self.token}"
        }

        data = {
            "event": json.dumps(data_json)
        }

        kakao_response = requests.post(common_parameters["KAKAO_CALENDAR_URL"], headers=headers, data=data)
        if kakao_response.status_code == 200:
            result = kakao_response.json()
            return {"id": result['event_id']}
        
        else:
            raise ValueError(f"{kakao_response.json()}")
            # raise HTTPException(detail={"kakao_response": kakao_response.json()})



        