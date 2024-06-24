from typing import List

import structlog
import pytz
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError, RequestError


logger = structlog.get_logger()


class ElasticsearchDataManager:

    def __init__(self, host):
        self.client = Elasticsearch(host, timeout=5, max_retries=2, retry_on_timeout=True)
        self.korea_time = pytz.timezone('Asia/Seoul')

    def update_user_info(self, index_n: str, body: dict):
        try:
            response = self.client.index(index=index_n, body=body, refresh="true")
            
            if response['result']:
                logger.info("Data indexed successfully in update_user_info.", index=index_n)
                return response['result']
            else:
                logger.error("Failed to index user info in update_user_info.", index=index_n)
                raise ValueError(f"Failed to index document {body.user_id} in index {index_n}.")
        
        except Exception as e:
            logger.error("Error occurred while indexing user info.", index=index_n, user_id=body.user_id, error=str(e))
            raise ValueError(f"Error occurred while indexing document {body.user_id} from Elasticsearch: {str(e)}")
    
    def update_userinfo(self, index_n: str, id: str, username: str = None, userphoto: str = None):
        try:
            update_fields = {}
            
            if username:
                update_fields["user_name"] = username
            
            if userphoto:
                update_fields["user_photo"] = userphoto

            body = {"doc": update_fields}
            
            response = self.client.update(
                index=index_n, 
                id=id,
                body=body
            )
            
            if response.get('result') == 'updated':
                logger.info("Data updated successfully in update_userinfo.", index=index_n, id=id)
                return f"Document with ID {id} has been successfully updated in index {index_n}."
            else:
                logger.error("Failed to update user info in update_userinfo.", index=index_n, id=id)
                raise ValueError(f"Failed to update document with ID {id} in index {index_n}. Response: {response}")
        
        except Exception as e:
            logger.error("Error occurred while updating user info.", index=index_n, id=id, error=str(e))
            raise ValueError(f"Error occurred while updating document {id} in Elasticsearch: {str(e)}")
        
    def delete_userinfo(self, index_n: str, id: str):
        try:
            response = self.client.delete(
                index=index_n, 
                id=id
            )

            if response.get('result') == 'deleted':
                logger.info("Data deleted successfully in delete_userinfo.", index=index_n, id=id)
                return f"Document with ID {id} has been successfully deleted from index {index_n}."
            else:
                logger.error("Failed to delete user info in delete_userinfo.", index=index_n, id=id)
                raise ValueError(f"Failed to delete document with ID {id} from index {index_n}. Response: {response}")
            
        except Exception as e:
            logger.error("Error occurred while deleting user info.", index=index_n, id=id, error=str(e))
            raise ValueError(f"Error occurred while deleting document {id} from Elasticsearch: {str(e)}")
    
    def fetch_userinfo(self, index_n: str, user_id: str, doc_id=False):
        try:
            response = self.client.search(
                index=index_n, 
                body={"query": {"term": {"userID": user_id}}}
            )
            hits = response['hits']['hits']

            if doc_id:
                if response['hits']['total']['value'] > 0:
                    logger.info("Document ID fetched successfully in fetch_userinfo.", index=index_n, user_id=user_id)
                    return response['hits']['hits'][0]['_id']
                else:
                    logger.error("User not found in fetch_userinfo.", index=index_n, user_id=user_id)
                    raise ValueError(f"{user_id} User not found! from Elasticsearch")
                    
            elif hits:
                logger.info("Data fetched successfully in fetch_userinfo.", index=index_n, user_id=user_id)
                return hits[0]['_source']
            else:
                logger.error("No documents found in fetch_userinfo.", index=index_n, user_id=user_id)
                raise ValueError(f"No documents found for id {user_id} in index {index_n}")
            
        except Exception as e:
            logger.error("Error occurred in fetch_userinfo.", index=index_n, user_id=user_id, error=str(e))
            raise ValueError(f"Error occurred while retrieving document {user_id} from Elasticsearch: {str(e)}")

    def fetch_username(self, index_n: str, username: str):
        try:
            response = self.client.search(
                index=index_n, 
                body={"query": {"term": {"user_name.keyword": username}}}
            )
            
            logger.info("Data fetched successfully in fetch_username.", index=index_n, username=username)
            return response

        except Exception as e:
            logger.error("Error occurred in fetch_username.", index=index_n, username=username, error=str(e))
            raise ValueError(f"Error occurred while retrieving document with username {username} from Elasticsearch: {str(e)}")
    
    def index_memory(self, index_n: str, doc_id: str, data):
        try:
            self.client.index(index=index_n, id=doc_id, body=data, refresh="true")
            
            logger.info("Data indexed successfully in index_memory.", index=index_n, id=doc_id)
        
        except Exception as e:
            logger.error("Error occurred in index_memory.", index=index_n, id=doc_id, data=data, error=str(e))
            raise ValueError(f"Error occurred while indexing document with id {doc_id} in Elasticsearch: {str(e)}")
    
    def update_summary(self, index_n: str, doc_id: str, summary: str, summary_tokens: int):
        try:
            data = {
                "doc": {
                    "summary": summary,
                    "summary_tokens": summary_tokens
                }
            }
            
            self.client.update(
                index=index_n,
                id=doc_id,
                body=data
            )
            
            logger.info("Data updated successfully in update_summary.", index=index_n, id=doc_id)
        
        except Exception as e:
            logger.error("Error occurred in update_summary.", index=index_n, id=doc_id, data=data, error=str(e))
            raise ValueError(f"Error occurred while updating document with id {doc_id} in Elasticsearch: {str(e)}")
    
    def fetch_data(self, index_n: str, doc_id: str, query_field: str = "_id", source_fields: List[str] = []):
        try:
            response = self.client.search(
                index=index_n, 
                body={
                    "_source": source_fields,
                    "query": {"term": {query_field: doc_id}}
                }
            )
            hits = response['hits']['hits']
            
            if hits:
                logger.info("Data fetched successfully in fetch_data.", index=index_n, id=doc_id)
                return hits[0]['_source']
            else:
                logger.error(f"No documents found in fetch_data.", index=index_n, id=doc_id, query_field=query_field)
                raise ValueError(f"No documents found for id {doc_id} in index {index_n}")
        
        except Exception as e:
            logger.error("Error occurred in fetch_data.", index=index_n, id=doc_id, error=str(e))
            raise ValueError(f"Error occurred while retrieving document {doc_id} from Elasticsearch: {str(e)}")
    
    def fetch_memory(self, index_n: str, session_id: str, source_fields: List[str] = []):
        try:
            # Start the initial search request and get the scroll ID.
            response = self.client.search(
                index=index_n,
                body={
                    "_source": source_fields,
                    "sort": [{"turn_id": {"order": "asc"}}],
                    "query": {"term": {"session_id.keyword": session_id}},
                    "size": 1000  # Adjust this value as needed.
                },
                scroll='1m'  # Keep the scroll context alive for 1 minute.
            )

            old_scroll_id = response['_scroll_id']
            hits = response['hits']['hits']

            all_hits = []

            while len(hits):
                # Append the search results to all_hits.
                all_hits.extend([hit['_source'] for hit in hits])

                # Search for the next batch of results.
                response = self.client.scroll(
                    scroll_id=old_scroll_id,
                    scroll='1m'  # Keep the scroll context alive for 1 minute.
                )

                # Update the scroll ID.
                old_scroll_id = response['_scroll_id']
                hits = response['hits']['hits']

            # Return all search results.
            logger.info("Data fetched successfully in fetch_memory.", index=index_n, session_id=session_id)
            return all_hits

        except NotFoundError:
            # Handle exceptions when there's no index or field in Elasticsearch.
            logger.error("No index or field found in fetch_memory.", index=index_n, session_id=session_id)
            raise ValueError(f"No index or field found for session_id {session_id} in Elasticsearch.")

        except RequestError as e:
            # Handle exceptions related to query or sorting field errors.
            if 'No mapping found for [turn_id]' in str(e):
                logger.error("No mapping found for [turn_id] in fetch_memory.", index=index_n, session_id=session_id)
                return {}
            else:
                logger.error("Error occurred in fetch_memory.", index=index_n, session_id=session_id, error=str(e))
                raise ValueError(f"Error occurred while retrieving documents for session_id {session_id} from Elasticsearch: {str(e)}")

    def fetch_last_memory(self, index_n: str, session_id: str, source_fields: List[str]):
        try:
            response = self.client.search(
                index=index_n,
                body={
                    "_source": source_fields,
                    "sort": [{"turn_id": {"order": "desc"}}],
                    "query": {"term": {"session_id.keyword": session_id}},
                    "size": 1
                }
            )
            hits = response['hits']['hits']
            
            if hits:
                logger.info("Successfully fetched the last memory in fetch_last_memory.", index=index_n, session_id=session_id)
                return hits[0]['_source']
            else:
                logger.error("No documents found in fetch_last_memory.", index=index_n, session_id=session_id)
                return None

        except Exception as e:
            logger.error("Error occurred in fetch_last_memory.", index=index_n, session_id=session_id, error=str(e))
            raise ValueError(f"Error occurred while retrieving last turn data for session_id {session_id} from Elasticsearch: {str(e)}")

    def delete_confirmed_itinerary(self, index_n: str, doc_id: str):
        try:
            response = self.client.delete(index=index_n, id=doc_id, refresh="true")
            
            if response.get('result') == 'deleted':
                logger.info("Data deleted successfully in delete_confirmed_itinerary.", index=index_n, id=doc_id)
            else:
                logger.error("Failed to delete data in delete_confirmed_itinerary.", index=index_n, id=doc_id)
                raise ValueError(f"Failed to delete document {doc_id} in index {index_n}.")
                
        except Exception as e:
            logger.error("Error occurred in delete_confirmed_itinerary.", index=index_n, id=doc_id, error=str(e))
            raise ValueError(f"Error occurred while deleting document {doc_id} in Elasticsearch: {str(e)}")
    
    def index_confirmed_itinerary(self, index_n: str, doc_id: str, data):
        try:
            response = self.client.index(index=index_n, id=doc_id, body=data, refresh="true")
            
            if response.get('result') == 'created' or response.get('result') == 'updated':
                logger.info("Data indexed successfully in index_confirmed_itinerary.", index=index_n, id=doc_id)
            else:
                logger.error("Failed to index data in index_confirmed_itinerary.", index=index_n, id=doc_id, data=data)
                raise ValueError(f"Failed to index document {doc_id} in index {index_n}.")
                
        except Exception as e:
            logger.error("Error occurred in index_confirmed_itinerary.", index=index_n, id=doc_id, data=data, error=str(e))
            raise ValueError(f"Error occurred while indexing document {doc_id} in Elasticsearch: {str(e)}")
    
    def update_confirmed_itinerary(self, index_n: str, doc_id: str, data):
        try:
            response = self.client.update(
                index=index_n,
                id=doc_id,
                body={
                    "doc": data
                }
            )

            # Check if the response indicates the document was successfully updated
            if response.get('result') == 'updated':
                logger.info("Data updated successfully in update_confirmed_itinerary.", index=index_n, id=doc_id)
            else:
                logger.error("Failed to update data in update_confirmed_itinerary.", index=index_n, id=doc_id, data=data)
                raise ValueError(f"Failed to update document {doc_id} in index {index_n}.")

        except Exception as e:
            logger.error("Error occurred in update_confirmed_itinerary.", index=index_n, id=doc_id, data=data, error=str(e))
            raise ValueError(f"Error occurred while updating document {doc_id} in Elasticsearch: {str(e)}")
    
    def fetch_confirmed_itineraries(
        self, 
        index_n: str, 
        user_id: str, 
        source_fields: List[str],
        page: int = None, 
        size: int = 10
    ):
        try:
            body = {
                "_source": source_fields,
                "query": {
                    "term": {"user_id": user_id}
                },
                "sort": [
                    {
                        "timestamp": {"order": "desc"}
                    }
                ]
            }
            
            if page is None:
                body['size'] = 1000
                
                response = self.client.search(index=index_n, body=body, scroll='1m')
                
                hits = []
                while len(response['hits']['hits']):
                    hits.extend(response['hits']['hits'])
                    response = self.client.scroll(scroll_id=response['_scroll_id'], scroll='1m')
            else:
                from_index = (page - 1) * size
                body['size'] = size
                body['from'] = from_index
                
                response = self.client.search(index=index_n, body=body)

                hits = response['hits']['hits']

            logger.info("Confirmed itineraries fetched successfully in fetch_confirmed_itineraries.", index=index_n, user_id=user_id, page=page if page else "all", hits=hits)

            result = []
            for hit in hits:
                destinations = [
                    {
                        "title": destination.get('title', ""),
                        "physical": destination.get('physical', False),
                        "visual": destination.get('visual', False),
                        "hearing": destination.get('hearing', False) 
                    } for destination in hit['_source']['itinerary']['schedule']
                ]
                result.append(
                    {
                        "itinerary_id": hit["_source"]['itinerary']["uuid"],
                        "session_id": hit["_source"]["session_id"],
                        "title": hit["_source"]['itinerary']["title"],
                        "destinations": destinations,
                        "date_type": hit['_source']['itinerary']['schedule'][0]["date_type"],
                        "timestamp" : hit["_source"]["timestamp"]
                    }
                )

            logger.info("Result of fetch_confirmed_itineraries.", index=index_n, user_id=user_id, page=page if page else "all", result=result)
            return result

        except Exception as e:
            logger.error("Error occurred in fetch_confirmed_itineraries.", index=index_n, user_id=user_id, error=str(e))
            raise ValueError(f"Error occurred while retrieving itineraries for user_id {user_id} from Elasticsearch: {str(e)}")
    
    def fetch_region(self, index_n: str, body: dict):
        try:
            response = self.client.search(
                index=index_n, 
                body=body
            )
            
            logger.info("Data fetched successfully in fetch_region.", index=index_n, data=body)
            return response

        except Exception as e:
            raise ValueError(f"Error occurred while retrieving region from Elasticsearch: {str(e)}")