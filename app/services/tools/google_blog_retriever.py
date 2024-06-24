from langchain.utilities import GoogleSearchAPIWrapper

import structlog

from core import common_parameters


logger = structlog.get_logger()


class BlogSearcher:
    def __init__(self):
        self.search_api = GoogleSearchAPIWrapper(
            google_api_key=common_parameters["GOOGLE_API_KEY"], 
            google_cse_id=common_parameters["GOOGLE_CSE_ID"]
        )

    def _get_top5_results(self, query: str):
        """Retrieve top 5 results for a given query."""
        return self.search_api.results(query, 5)

    @staticmethod
    def _filter_snippet(data):
        """Remove 'snippet' key from the data."""
        return [{k: v for k, v in item.items() if k != 'snippet'} for item in data]

    def search_blog(self, query: str):
        """Search for blogs and return results without the 'snippet' field."""

        logger.info("Start search_blog", query=query)

        raw_results = self._get_top5_results(query)
        logger.info("Result form _get_top5_results", raw_results=raw_results)
        # filtered_results = self._filter_snippet(raw_results)
        
        input_data = []
        hyperlink = {}
        for item in raw_results:
            input_data.append((item['title'], item['snippet']))
            hyperlink[item['title']] = f"[{item['title']}]({item['link']})"
            
        output = {
            "input_data": input_data,
            "hyperlink": hyperlink
        }
        
        logger.info("Result of search_blog", output=output)

        return output


if __name__ == "__main__":
    searcher = BlogSearcher()
    result = searcher.search_blog("제주도 맛집 추천")
    print(result)