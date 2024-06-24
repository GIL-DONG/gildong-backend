import jwt
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
from fastapi import HTTPException
from jwt import ExpiredSignatureError, InvalidTokenError


class TokenManager:
    def __init__(self, config):
        self.secret_key = config['secret_key']
        self.algorithm = config['algorithm']
        self.es_index = config['refresh_token_index_name']
        self.client = Elasticsearch(config['elasticsearch_host'], timeout=5, max_retries=2, retry_on_timeout=True)

    def search_user_in_es(self, user_id):
        body = {
            "query": {
                "term": {
                    "userID": user_id
                }
            }
        }
        res = self.client.search(index=self.es_index, body=body)
        return res 

    def create_access_token(self, data, expires_delta=None):
        to_encode = data.copy()
        to_encode.update({"token_type": "access"})
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=8)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def create_refresh_token(self, data, expires_delta=None):
        to_encode = data.copy()
        to_encode.update({"token_type": "refresh"})
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(weeks=2)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        # Elasticsearch에 refresh_token 저장 및 업데이트
        search_userid = self.search_user_in_es(data["user_id"])
        body = {"userID": data["user_id"], "refresh_token": encoded_jwt}
        if search_userid['hits']['total']['value'] > 0:
            doc_id = search_userid['hits']['hits'][0]['_id']
            body = {"doc": {"userID": data["user_id"], "refresh_token": encoded_jwt}}
            self.client.update(index=self.es_index, id=doc_id, body=body)
        else: 
            self.client.index(index="refresh_tokens", body=body)
        return encoded_jwt

    def decode_token(self, token):
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            token_type = payload.get("token_type")
            if token_type == "refresh":
                search_result = self.client.search(index="refresh_tokens", body={
                    "query": {
                        "bool": {
                            "must": [
                                {"match": {"userID": payload["user_id"]}},
                                {"match": {"refresh_token": token}}
                            ]
                        }
                    }
                })
                if search_result["hits"]["total"]["value"] == 0:
                    raise InvalidTokenError("Invalid refresh token")
            return token_type, payload
        except ExpiredSignatureError:
            raise ExpiredSignatureError("Token expired")
        except InvalidTokenError:
            raise InvalidTokenError("Invalid token")

    def verify_and_refresh_tokens(self, access_token, refresh_token):
        try:
            payload = self.decode_token(access_token)
            return {"user_data": payload, "new_access_token": None}
        except Exception as e:
            if str(e) == "Token has expired":
                try:
                    refresh_payload = self.decode_token(refresh_token)
                    new_access_token = self.create_access_token(refresh_payload)
                    return {"user_data": refresh_payload, "new_access_token": new_access_token}
                except Exception as refresh_error:
                    raise Exception(f"Refresh token error: {str(refresh_error)}")
            else:
                raise e
            
    
    def payload_data(self, token):
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            payload.pop('exp', None)
            return payload
        except ExpiredSignatureError:
            raise ExpiredSignatureError("Token expired")
        except InvalidTokenError:
            raise InvalidTokenError("Invalid token")
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))