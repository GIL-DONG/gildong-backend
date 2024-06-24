def travel_info_collector(response: dict):
    # Extracting and removing 'message' from the response dictionary.
    message = response.pop('message', None)
    
    # Storing the remaining data as travel_info.
    travel_info = response
    
    # Returning the 'message' and 'travel_info'.
    return travel_info, message