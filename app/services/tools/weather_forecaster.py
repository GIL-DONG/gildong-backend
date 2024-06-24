import requests
import re
from datetime import datetime

from toolva import Toolva

from core import common_parameters
from services.tools.kakao_address import find_full_address


class APIHandler:
    @staticmethod
    def call_api(url, params, timeout=5):
        try:
            response = requests.get(url, params=params)
            if response.status_code != 200:
                raise ConnectionError(f"API Error {response.status_code}: {response.text}")
            return response.text
        except requests.Timeout:
            raise TimeoutError(f"API call to {url} timed out after {timeout} seconds.")
        except requests.ConnectionError:
            raise ConnectionError(f"API call to {url} failed.")


class WeatherForecast(APIHandler):
    BASE_URL = "https://apihub.kma.go.kr/api/typ01/url/"
    ENDPOINTS = {
        "mid_rain": "fct_afs_wl.php",
        "mid_temperature": "fct_afs_wc.php",
        "short": "fct_afs_dl.php"
    }

    def __init__(self):
        self.authKey = common_parameters["Weather_APP_KEY"]
        self.host = common_parameters["elasticsearch_host"]
        self.retriever = self._initialize_retriever()
        self.BASE_URL = common_parameters["weather_url"]
        self.ENDPOINTS = {
            "mid_rain": "fct_afs_wl.php",
            "mid_temperature": "fct_afs_wc.php",
            "short": "fct_afs_dl.php"
        }

    def _initialize_retriever(self):
        return Toolva(
            tool="semantic_search",
            src="es",
            model={
                "host_n": self.host,
                "http_auth": ("", ""),
                "index_n": "weather_regioncode",
                "encoder_key": {
                    "src": "drive",
                    "model": "sts.klue/roberta-large.klue-nli_klue-sts.bi-nli-sts"
                }
            },
            async_mode=False
        )
    
    def _convert_location_code(self, locCode):
        kakao_loc_code = find_full_address(locCode)
        hits = self.retriever(kakao_loc_code, "vector", knn=False, top_k=3, source_fields=["text", "REG_ID"])
        print(hits[0]['_source']["REG_ID"])
        return hits[0]['_source']["REG_ID"]    

    def _extract_json(self, data):
        actual_data = re.search('#START7777\n(.*?)#7777END', data, re.DOTALL).group(1).replace(",=", "")
        lines = [line for line in actual_data.split('\n') if line and not line.startswith("#")]
        columns_line = [line for line in actual_data.split('\n') if line.startswith("# REG_ID")]
        headers = str(columns_line[0]).replace("#","").split()
        return [{header: value.strip('"') for header, value in zip(headers, re.findall(r'".+?"|\S+', line))} for line in lines]

    def _fetch_midterm_records(self, params):
        rain_data = self.call_api(self.BASE_URL + self.ENDPOINTS['mid_rain'], params)
        temp_data = self.call_api(self.BASE_URL + self.ENDPOINTS['mid_temperature'], params)
        rain_records = self._extract_json(rain_data)
        temp_records = self._extract_json(temp_data)
        merged_results = []
        if rain_records:
            for rain_record in rain_records:
                merged_record = {
                    "날짜": rain_record['TM_EF'][:8],
                    "하늘상태": rain_record['WF'].replace("\"",""),
                    "강수확률": rain_record['RN_ST']
                }
                merged_results.append(merged_record)
        else:
            for tempr_record in temp_records:
                merged_record = {
                    "날짜": tempr_record['TM_EF'][:8],
                    "최저기온": tempr_record['MIN'],
                    "최고기온": tempr_record['MAX']
                }
                merged_results.append(merged_record)
        return merged_results

    def _fetch_shortterm_records(self, params):
        response_data = self.call_api(self.BASE_URL + self.ENDPOINTS['short'], params)
        records = self._extract_json(response_data)
        return [{
            "날짜": rec['TM_EF'][:10],
            "기온": rec['TA'],
            "강수확률": rec['ST'],
            "하늘상태": rec['WF']
        } for rec in records if rec['TA'] != '-99']

    def cleansing(self, data, startDate, endDate=None):
        print(f"endDate: {endDate}")
        if endDate:
            filtered_results = [entry for entry in data if startDate <= entry['날짜'][:8] <= endDate]
        else: 
            filtered_results = [entry for entry in data if entry['날짜'][:8] == startDate]

        output = {
            "input_data": filtered_results,
            "hyperlink": {}
        }
        
        return output

    def get_forecast(self, weather_dates=None, location=None):
        start_date = weather_dates.get("start_date", None)
        end_date = weather_dates.get("end_date", None)
        
        if not start_date or not location:
            raise ValueError("Both startDate and locCode are required parameters.")
        
        current_date = datetime.now().strftime('%Y%m%d')
        date_difference = (datetime.strptime(start_date, '%Y%m%d') - datetime.strptime(current_date, '%Y%m%d')).days
        # Convert location code to match API requirements
        loc_code_converted = self._convert_location_code(location)   

        params = {
            'reg': loc_code_converted,
            'tmef1': start_date, 
            'tmef2' : start_date if end_date is None else end_date,
            'mode': "0",
            'disp': "0",
            'help' : '1',
            'authKey': self.authKey
        }
        
        #단기예보
        if date_difference < 4:
            print("단기예보")
            response = self._fetch_shortterm_records(params)
            return self.cleansing(response, start_date, end_date)
        
        #중기예보
        else:
            print("중기예보")
            params['tmef1'] = current_date + ("0600" if datetime.now().hour < 18 else "1800")
            response = self._fetch_midterm_records(params)
            return self.cleansing(response, start_date, end_date)