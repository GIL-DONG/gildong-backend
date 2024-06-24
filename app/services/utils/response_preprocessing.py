import re
import uuid
import structlog
from datetime import datetime


logger = structlog.get_logger()


class ResponsePreprocessor:

    def __init__(self) -> None:
        pass
    
    @staticmethod
    def normalize_text(text):
        """
        Normalize text for consistent processing.

        Convert text to lowercase, strip whitespace from both ends, 
        and remove all spaces.

        Args:
        - text (str): The text to be normalized.

        Returns:
        - str: Normalized text.
        
        """
        return text.lower().strip()
    
    @staticmethod
    def preprocess_hyperlink(key, metadata):
        detail_url = f"https://gildong.site/travel/detail/{metadata[key]['_id']}"
        return f"[{key}]({detail_url})"
    
    @staticmethod
    def find_key_in_memory(key, memory):
        formatted_ai_message = memory.get("formatted_ai_message", "")
        
        pattern = r'\[{}\]\(([^)]+)\)'.format(re.escape(key))
        match = re.search(pattern, formatted_ai_message)
        
        if match:
            return f"[{key}]({match.group(1)})"
        
        schedule = memory.get("itinerary_schedule", [])
        if schedule:
            for item in schedule:
                if item.get("title") == key:
                    return f"[{key}]({item.get('url')})"
        
        return None
    
    def _check_table_format(self, response):
        table_re = re.compile(r'\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|')
        return bool(table_re.search(response))

    def _extract_title(self, response):
        title_re = re.compile(r'\*\*(.+?)\*\*')
        title_match = title_re.search(response)
        return title_match.group(1) if title_match else ""

    def _extract_schedule(self, response, metadata, memory):
        schedule = []
        previous_schedule = memory.get("itinerary_schedule", []) or []
        
        # 현재 년도 가져오기
        current_year = datetime.now().year
        
        table_re = re.compile(r'\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|')
        matches = table_re.findall(response)
        
        # First pass to extract schedule without updating end_time
        for match in matches[2:]:
            date, time, place, description = match

            # 작은따옴표 제거
            place = place.replace("'", "")

            date_type = "date"
            try:
                date = datetime.strptime(date, "%m/%d")
                date = date.replace(year=current_year)
                date = date.strftime("%Y-%m-%d")
            except ValueError:
                date_type = "day_label"

            try:
                start_time, end_time = time.split('-')

                metadata_place = next((item for item in previous_schedule if item.get("title") == place), {})

                if metadata_place:
                    metadata_place["date"] = date
                    metadata_place["date_type"] = date_type
                    schedule.append(metadata_place)
                else:
                    metadata_place = metadata.get(place, {"_source": {}})["_source"]

                    title = metadata_place.get("title", place)
                    url = metadata_place.get("detail_url", "")
                    location = metadata_place.get('location', {})
                    image_url = metadata_place.get('url', "")
                    physical = True if metadata_place.get('physical_en') else False
                    visual = True if metadata_place.get('visual_en') else False
                    hearing = True if metadata_place.get('hearing_en') else False

                    schedule.append({
                        "title": title,
                        "url": url,
                        "date": date,
                        "date_type": date_type,
                        "start_time": f"{start_time.strip()}:00",
                        "end_time": f"{end_time.strip()}:00" if end_time else None,  # set end_time as None if not present
                        "location": location,
                        "description": description.strip(),
                        "image_url": image_url,
                        "physical": physical,
                        "visual": visual,
                        "hearing": hearing
                    })
            except Exception as e:
                logger.error(f"An error occurred: {e}")

        # Second pass to update end_time
        for i, event in enumerate(schedule[:-1]):  # skip the last event
            if event["end_time"] is None:
                event["end_time"] = schedule[i+1]["start_time"]

        return schedule
    
    def _extract_itinerary_section(self, response):
        """
        Extract the section of the response containing the title and table.

        Args:
        - response (str): The AI's response containing the itinerary.

        Returns:
        - str: Extracted section containing the title and table.
        """
        pattern = r'(\*\*.*\*\*.*\|.*\|\n(\|-*\|-*\|-*\|-*\|\n)+(\|.*\|\n)+)'
        match = re.search(pattern, response, re.DOTALL)
        return match.group(1) if match else ""
    
    def preprocess_itinerary(self, message, metadata, memory):
        # 체크 표 형식
        if not self._check_table_format(message):
            return {}

        itinerary = {
            "uuid": str(uuid.uuid4())
        }

        # 제목 추출
        itinerary["title"] = self._extract_title(message)

        # 일정 추출
        itinerary["schedule"] = self._extract_schedule(message, metadata, memory)
        
        # 제목부터 표 영역까지 추출
        itinerary["itinerary_section"] = self._extract_itinerary_section(message)

        return itinerary