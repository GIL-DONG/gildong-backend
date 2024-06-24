from typing import List, Union

import structlog

from services.utils import ResponsePreprocessor


logger = structlog.get_logger()


class travelDestinationRetrieval:
    
    def __init__(
        self,
        retriever,
        token_limiter = None,
    ) -> None:
        """
        Initialize the destination retrieval class.

        Args:
        - retriever: The semantic search tool.
        - TokenLimiter: Tool to limit tokens in the search result.
        
        """
        self.retriever = retriever
        self.token_limiter = token_limiter
    
    async def retrieve(self, memory, **kwargs) -> List[Union[str, tuple]]:
        """
        Retrieve destination information based on provided criteria.

        Args:
        - kwargs (dict): Additional arguments necessary for the retrieval function.

        Returns:
        - list: Formatted search results.
        
        """
        user_info = memory.get("user_info", {})
        query = kwargs.get("query", "")
        vector_field = kwargs.get("vector_field")
        index_n = kwargs.get("index_n")
        top_k = kwargs.get("top_k", 10)
        exclude = kwargs.get("exclude", [])
        source_fields = kwargs.get("source_fields")
        key_field = kwargs.get("key_field")
        value_fields = kwargs.get("value_fields")
        
        # Exclude specified keywords if any
        if exclude:
            exclude_keywords = [{"terms": {field: exclude}} for field in source_fields]
        else:
            exclude_keywords = []

        # Conducting the retrieval
        logger.info("Starting the retrieval process.", input=kwargs)
        
        try:
            filter = [
                {"exists": {"field": vector_field}},
                {"exists": {"field": "overview_summ"}}
            ]

            if user_info and user_info.get("disability_type"):
                # filter.append({"exists": {"field": user_info.get("disability_type")}})
                
                disability_en2ko = {
                    "physical": "지체장애인",
                    "visual": "시각장애인",
                    "hearing": "청각장애인"
                }
                
                query = disability_en2ko[user_info.get("disability_type")] + " " + query
                
            hits = await self.retriever(
                query, 
                vector_field,
                index_n=index_n,
                top_k=top_k, 
                source_fields=source_fields, 
                filter=filter,
                must_not=exclude_keywords
            )
            logger.info(f"Retrieved hits: {hits}")
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
                logger.info("Number of items has been limited.", original_len=len(formatted_data_list), limited_len=len(limited_formatted_data_list), limited_data=limited_formatted_data_list)
                
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