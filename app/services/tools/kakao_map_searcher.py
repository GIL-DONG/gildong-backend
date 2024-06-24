from PyKakao import Local
from core import common_parameters

class locSearch:
    def __init__(self):
        self.searcher = Local(service_key=common_parameters["Kakao_APP_KEY"])

    def _construct_keyword(self):
        """Construct the keyword for searching."""
        keyword = self.location

        # Set default category based on search_type if category is not provided
        if not self.category:
            if self.search_type == "restaurant_info":
                self.category = "맛집"  # No default for restaurants
            elif self.search_type == "hotel_info":
                self.category = "호텔"
            elif self.search_type == "tourism_info":
                self.category = "관광지"

        if self.category:
            keyword = f"{keyword} {self.category}".strip()

        return keyword

    def get_results(self):
        """Fetch search results based on the type and category."""
        try:
            keyword = self._construct_keyword()

            # Determine search type
            if self.search_type not in ["restaurant_info", "hotel_info", "tourism_info"]:
                raise ValueError("Invalid search type")

            results = self.searcher.search_keyword(keyword, dataframe=True)

            if results.empty:
                raise ValueError("No matching results found")

            return results
        except ValueError as e:
            raise Exception(f"Search error: {str(e)}")

    def get_message(self, location, search_type, category=None):
        """Extract and format the top results."""
        # Update class attributes based on the provided arguments
        self.location = location
        self.search_type = search_type
        self.category = category
        
        try:
            results = self.get_results()
            message_list = []

            # Extract top 5 results
            for index, result in results.head(5).iterrows():
                message = {
                    "place_name": result["place_name"],
                    "category_name": result["category_name"].replace(" > ", ", "),
                    "url": result["place_url"]
                }
                message_list.append(message)

            return message_list
        except Exception as e:
            return {'error': str(e)}
        



