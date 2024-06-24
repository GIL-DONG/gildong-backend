from typing import List, Union

import structlog
import aiohttp
from aiohttp.client_exceptions import ContentTypeError

from services.utils import ResponsePreprocessor


logger = structlog.get_logger()


class imageRetrieval:
    
    def __init__(
        self,
        retriever,
        token_limiter = None,
    ) -> None:
        """
        Initialize the destination retrieval class.

        Args:
        - retriever: The image search tool.
        - TokenLimiter: Tool to limit tokens in the search result.
        
        """
        self.retriever = retriever
        self.token_limiter = token_limiter
    
    async def retrieve(self, **kwargs) -> List[Union[str, tuple]]:
        """
        Retrieve destination information based on provided criteria.

        Args:
        - kwargs (dict): Additional arguments necessary for the retrieval function.

        Returns:
        - list: Formatted search results.
        
        """
        image_name = kwargs.get("image_name")
        key_field = kwargs.get("key_field")
        value_fields = kwargs.get("value_fields")
        
        logger.info("Starting the retrieval process.", input=kwargs)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.retriever, json={'file_name': image_name}) as response:
                    hits = await response.json()
                    
            logger.info("Retrieved data", hits=hits)
        except ContentTypeError as ce:
            response_text = await response.text()
            logger.error(f"ContentTypeError in retrieving: {ce}. Response content: {response_text}")
            raise ce
        except ValueError as e:
            logger.error(f"Error in retrieving: {e}")
            raise e
        
        # Formatting the hits for the output
        output = {}
        formatted_data_list = []
        hyperlink = {}
        for item in hits:
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
                
        # Limiting tokens if necessary
        if self.token_limiter:
            try:
                limited_formatted_data_list = self.token_limiter.cutoff(
                    formatted_data_list, 
                    "back"
                )
                logger.info(f"Number of items has been limited. Original: {len(formatted_data_list)}, Now: {len(limited_formatted_data_list)}")
                
                # Filter output based on limited_formatted_data_list
                limited_keys = [list(item.keys())[0] for item in limited_formatted_data_list]  # extracting keys from limited_formatted_data_list
                
                # keeping only those keys in output which are present in limited_keys
                filtered_output = {}
                filtered_hyperlink = {}
                for key in limited_keys:
                    filtered_output[key] = output[key]
                    filtered_hyperlink[key] = hyperlink[key]
                
                filtered_output["input_data"] = limited_formatted_data_list
                filtered_output["hyperlink"] = filtered_hyperlink
                output = filtered_output
            
            except ValueError as e:
                logger.error(f"Error in TokenLimiter: {e}")
                raise e
        else:
            output["input_data"] = formatted_data_list
            output["hyperlink"] = hyperlink
        
        return output