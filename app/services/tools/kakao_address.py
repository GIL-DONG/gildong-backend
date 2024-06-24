from PyKakao import Local
from core import common_parameters

def find_full_address(name : str):
    LOCAL = Local(service_key = common_parameters["Kakao_local_APP_KEY"])
    try:
        address = LOCAL.search_address(name, dataframe=False)['documents'][0]['address']['address_name']
        return address
    except:
        return None

if __name__ == "__main__":
    find_full_address("양주")