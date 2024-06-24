from typing import List

import structlog
import pytz
from datetime import datetime
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError, RequestError


logger = structlog.get_logger()


class ElasticsearchDataManager:

    def __init__(self, host):
        self.client = Elasticsearch(host, timeout=5, max_retries=2, retry_on_timeout=True)
        
        self.korea_time = pytz.timezone('Asia/Seoul')

    def index_memory(self, index_n: str, doc_id: str, data):
        try:
            self.client.index(index=index_n, id=doc_id, body=data)
            logger.info("Data indexed successfully.", index=index_n, id=doc_id)
        except Exception as e:
            logger.error("Error occurred while indexing data.", error=str(e))
    
    def update_summary(self, index_n: str, doc_id: str, summary: str, summary_tokens: int):
        try:
            # 문서를 업데이트합니다.
            self.client.update(
                index=index_n,
                id=doc_id,
                body={
                    "doc": {
                        "summary": summary,
                        "summary_tokens": summary_tokens
                    }
                }
            )
            logger.info("Data updated successfully.", index=index_n, id=doc_id)
        except Exception as e:
            logger.error("Error occurred while updating data.", error=str(e))
    
    def fetch_travel_destination(self, index_n: str, doc_id: str, source_fields: List[str] = []):
        try:
            response = self.client.search(
                index=index_n, 
                body={
                    "_source": source_fields,
                    "query": {"term": {"_id": doc_id}}
                }
            )
            hits = response['hits']['hits']
            
            if hits:
                return hits[0]['_source']
            else:
                raise ValueError(f"No documents found for id {doc_id} in index {index_n}")
        
        except Exception as e:
            raise ValueError(f"Error occurred while retrieving document {doc_id} from Elasticsearch: {str(e)}")

    def fetch_user_info(self, index_n: str, user_id:str, doc_id=False):
        try:
            response = self.client.search(
                index=index_n, 
                body={"query": {"term": {"userID": user_id}}}
            )
            hits = response['hits']['hits']

            if doc_id:
                if response['hits']['total']['value'] > 0:
                    return response['hits']['hits'][0]['_id']
                else:
                    raise ValueError(f" {user_id} User not found! from Elasticsearch: {str(e)}")
                
            if hits:
                return hits[0]['_source']
            else:
                raise ValueError(f"No documents found for id {user_id} in index {index_n}")
        
        except Exception as e:
            raise ValueError(f"Error occurred while retrieving document {user_id} from Elasticsearch: {str(e)}")
    
    def fetch_memory(self, index_n: str, session_id: str, source_fields: List[str] = []):
        try:
            # 초기 검색 요청을 수행하고 scroll ID를 얻습니다.
            response = self.client.search(
                index=index_n,
                body={
                    "_source": source_fields,
                    "sort": [{"turn_id": {"order": "asc"}}],
                    "query": {"term": {"session_id.keyword": session_id}},
                    "size": 1000  # 이 값은 필요에 따라 조정할 수 있습니다.
                },
                scroll='1m'  # 1분 동안 scroll context를 유지합니다.
            )

            old_scroll_id = response['_scroll_id']
            hits = response['hits']['hits']

            all_hits = []

            while len(hits):
                # 검색된 결과를 all_hits에 추가합니다.
                all_hits.extend([hit['_source'] for hit in hits])

                # 다음 batch의 결과를 검색합니다.
                response = self.client.scroll(
                    scroll_id=old_scroll_id,
                    scroll='1m'  # 1분 동안 scroll context를 유지합니다.
                )

                # scroll ID를 업데이트합니다.
                old_scroll_id = response['_scroll_id']
                hits = response['hits']['hits']

            # 모든 검색 결과를 반환합니다.
            logger.info("Fetched memories successfully.", session_id=session_id, hits_len=len(all_hits))
            return all_hits

        except NotFoundError:
            # Elasticsearch에 인덱스나 필드가 없을 때의 예외 처리
            raise ValueError(f"No index or field found for session_id {session_id} in Elasticsearch.")

        except RequestError as e:
            # 쿼리 또는 정렬 필드 오류를 처리합니다.
            if 'No mapping found for [turn_id]' in str(e):
                logger.error(f"No mapping found for [turn_id] in Elasticsearch for session_id {session_id}.")
                return {}
            else:
                raise ValueError(f"Error occurred while retrieving documents for session_id {session_id} from Elasticsearch: {str(e)}")

        except Exception as e:
            # 일반적인 예외 처리
            raise ValueError(f"An unexpected error occurred while retrieving documents for session_id {session_id} from Elasticsearch: {str(e)}")

    def fetch_last_memory(self, index_n: str, session_id: str, source_fields: List[str]):
        try:
            response = self.client.search(
                index=index_n,
                body={
                    "_source": source_fields,
                    "sort": [{"turn_id": {"order": "desc"}}],
                    "query": {"term": {"session_id": session_id}},
                    "size": 1
                }
            )
            hits = response['hits']['hits']
            return hits[0]['_source'] if hits else None

        except Exception as e:
            raise ValueError(f"Error occurred while retrieving last turn data for session_id {session_id} from Elasticsearch: {str(e)}")

    def index_confirmed_itinerary(self, index_n: str, doc_id:str, data):
        self.client.index(index=index_n, id=doc_id, body=data)

    def fetch_itinerary(self, index_n: str, itinerary_uuid: str, source_fields: List[str] = []):
        try:
            response = self.client.search(
                index=index_n,
                body={
                    "_source": source_fields,
                    "query": {"term": {"itinerary.uuid.keyword": itinerary_uuid}}
                }
            )
            hits = response['hits']['hits']
            
            if hits:
                return hits[0]['_source']
            else:
                raise ValueError(f"No documents found for uuid {itinerary_uuid} in index {index_n}")
        
        except Exception as e:
            raise ValueError(f"Error occurred while retrieving document {itinerary_uuid} from Elasticsearch: {str(e)}")
    
    def fetch_confirmed_itineraries(
        self, 
        index_n: str, 
        user_id: str, 
        source_fields: List[str], 
        page: int = 1, 
        size: int = 10
    ):
        try:
            # 계산된 시작점 (0-indexed)
            from_index = (page - 1) * size

            response = self.client.search(
                index=index_n,
                body={
                    "_source": source_fields,
                    "query": {"term": {"user_id": user_id}},
                    "sort": [{"timestamp": {"order": "desc"}}],
                    "size": size, 
                    "from": from_index, 
                }
            )

            return [hit["_source"] for hit in response["hits"]["hits"]]

        except Exception as e:
            raise ValueError(f"Error occurred while retrieving latest itineraries for user_id {user_id} from Elasticsearch: {str(e)}")


    def update_user_info(self, index_n: str, body: dict):
        try:
            response = self.client.index(
                index=index_n, 
                body=body
            )
            
            if response['result']:
                return response['result']
            else:
                raise ValueError(f"No documents found for id {body.user_id} in index {index_n}")
        
        except Exception as e:
            raise ValueError(f"Error occurred while retrieving document {body.user_id} from Elasticsearch: {str(e)}")     

    def fetch_username(self, index_n: str, username: str):
        try:
            response = self.client.search(
                index=index_n, 
                body={"query": {"term": {"user_name.keyword": username}}}
            )
            return response

        except Exception as e:
            raise ValueError(f"Error occurred while retrieving document from Elasticsearch: {str(e)}")
    
    def update_userinfo(self, index_n: str, username: str, id: str):
        try:
            response = self.client.update(
                index=index_n, 
                id=id,
                body={"doc": {"user_name": username}}
            )
            return response

        except Exception as e:
            raise ValueError(f"Error occurred while retrieving document from Elasticsearch: {str(e)}")
    
    def delete_userinfo(self, index_n: str, id: str):
        try:
            response = self.client.delete(
                index=index_n, 
                id=id
            )
            return response

        except Exception as e:
            raise ValueError(f"Error occurred while retrieving document from Elasticsearch: {str(e)}")
        
    
    def fetch_region(self, index_n: str, body: dict):
        try:
            response = self.client.search(
                index=index_n, 
                body=body
            )
            logger.info("Data indexed successfully.", response=response)
            return response

        except Exception as e:
            raise ValueError(f"Error occurred while retrieving document from Elasticsearch: {str(e)}")
    