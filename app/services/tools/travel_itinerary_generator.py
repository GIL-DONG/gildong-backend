import asyncio
import structlog

from services.utils import ResponsePreprocessor


logger = structlog.get_logger()


class travelItineraryGenerator:
    
    def __init__(self, fetcher):
        self.fetcher = fetcher
        
    async def fetch(self, memory, **kwargs):
        input_data = kwargs.get("input_data")
        
        if input_data == "previous_ai_answer" and memory.get("input_data"):
            
            logger.info(f"Fetch data from elasticsearch.")
            
            input_data = memory.get("input_data")
            index_n = kwargs.get("index_n")
            source_fields = kwargs.get("source_fields", [])
            key_field = kwargs.get("key_field")
            value_fields = kwargs.get("value_fields")
            
            tasks = [
                self.fetcher.search(
                    index=index_n, 
                    body={
                        "_source": source_fields,
                        "query": {
                            "term": {
                                "_id": data_id
                            }
                        }
                    }
                )
                for data_id in input_data
            ]
            
            responses = await asyncio.gather(*tasks)
            
            logger.info(f"Fetched responses: {responses}")
            
            # Formatting the responses for the output
            output = {}
            formatted_data_list = []
            hyperlink = {}
            for response in responses:
                item = response['hits']['hits'][0]
                
                key = ResponsePreprocessor.normalize_text(item["_source"].get(key_field))
                other_values = []
                for field in value_fields:
                    value = item["_source"].get(field, "")
                    if isinstance(value, list):
                        other_values.extend(value) 
                    else:
                        other_values.append(str(value))

                detail_url = f"https://gildong.site/travel/detail/{item['_id']}"
                hyperlink[key] = f"[{key}]({detail_url})"
                item['_source']["detail_url"] = detail_url
                output[key] = {
                    "_id": item['_id'],
                    "_source": item['_source'],
                }

                other_fields = ", ".join(other_values)
                formatted_data_list.append({key: other_fields})
            
            output['input_data'] = formatted_data_list
            output["hyperlink"] = hyperlink
            
            return output