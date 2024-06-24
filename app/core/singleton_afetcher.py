from elasticsearch import AsyncElasticsearch

from core.common_config import common_parameters


class SingletonAsyncFetcher:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SingletonAsyncFetcher, cls).__new__(cls)
            cls._instance.initialize_fetcher()
        return cls._instance

    def initialize_fetcher(self):
        self.fetcher = AsyncElasticsearch(
            common_parameters.get("elasticsearch_host"), 
            timeout=5, 
            max_retries=2, 
            retry_on_timeout=True
        )
        
    def get_fetcher(self):
        return self.fetcher