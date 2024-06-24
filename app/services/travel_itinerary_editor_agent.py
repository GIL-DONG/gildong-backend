import json
from typing import AsyncGenerator

import structlog
import asyncio
import pytz
from datetime import datetime
from toolva import Toolva
from toolva.utils import (
    PromptTemplate,
    LogCapture,
    TokenLimiter
)

from services.utils import ResponsePreprocessor
from services.tools import (
    travel_info_collector,
    imageRetrieval,
    travelDestinationRetrieval,
    travelItineraryGenerator,
    WeatherForecast,
    BlogSearcher
)


logger = structlog.get_logger()


class TIEAgentFactory:

    def __init__(self, config: dict):
        self.config = config
        self._setup()

    def _setup(self):
        # Strategy Planner
        self.planner = Toolva(
            tool="text_generation", 
            src="openai",
            model=self.config.get("planner_ai_model", "gpt-4"), 
            prompt_template=PromptTemplate().load(self.config.get("planner_template")), 
            max_tokens=self.config.get("planner_max_tokens", 800), 
            temperature=self.config.get("planner_temperature", 0.), 
            top_p=self.config.get("planner_top_p", 1.0), 
            frequency_penalty=self.config.get("planner_frequency_penalty", 0.), 
            presence_penalty=self.config.get("planner_presence_penalty", 0.), 
            async_mode=True
        )
        
        # Itinerary Generator
        self.generator = Toolva(
            tool="text_generation", 
            src="openai",
            model=self.config.get("generator_ai_model", "gpt-4"),
            prompt_template=PromptTemplate().load(self.config.get("generator_template")), 
            max_tokens=self.config.get("generator_max_tokens", 800), 
            temperature=self.config.get("generator_temperature", 1.0), 
            top_p=self.config.get("generator_top_p", 1.0),
            frequency_penalty=self.config.get("generator_frequency_penalty", 0.), 
            presence_penalty=self.config.get("generator_presence_penalty", 0.), 
            stream=True
        )
        
        from core import SingletonSummarizer, SingletonRetriever, SingletonAsyncFetcher
        
        # Itinerary Summarizer
        self.summarizer = SingletonSummarizer().get_summarizer()
        
        tokenizer = Toolva(
            tool="tokenization", 
            src="openai", 
            model=self.config["travel_destination_retriever"].get("generator_ai_model", "gpt-4")
        )
        token_limiter = TokenLimiter(
            tokenizer=tokenizer, 
            max_tokens=self.config["travel_destination_retriever"].get("max_tokens", 3000)
        )
        
        # Itinerary image_retriever Tool
        image_retriever = self.config["image_retriever"].get("url")
        image_retrieval = imageRetrieval(image_retriever, token_limiter)
        
        # Itinerary travel_destination_retriever Tool
        text_retriever = SingletonRetriever().get_retriever()
        destination_retrieval = travelDestinationRetrieval(text_retriever, token_limiter)
        
        # Itinerary weather_forecast Tool
        weather_forecaster = WeatherForecast()
        
        # Itinerary blog_searcher Tool
        blog_searcher = BlogSearcher()
        
        # Itinerary travel_itinerary_generator Tool
        fetcher = SingletonAsyncFetcher().get_fetcher()
        destination_fetcher = travelItineraryGenerator(fetcher)
        
        self.tools = {
            "travel_info_collector": lambda planner_result: travel_info_collector(planner_result),
            "image_retriever": lambda image : image_retrieval.retrieve(
                image_name=image,
                key_field=self.config["travel_destination_retriever"].get("key_field"),
                value_fields=self.config["travel_destination_retriever"].get("value_fields")
            ),
            "travel_destination_retriever": lambda memory, kwargs: destination_retrieval.retrieve(
                memory=memory,
                query=kwargs.get("query"),
                vector_field=self.config["travel_destination_retriever"].get("vector_field"),
                index_n=self.config["travel_destination_retriever"].get("index_name"),
                top_k=kwargs.get("top_k"),
                exclude=kwargs.get("exclude"),
                source_fields=self.config["travel_destination_retriever"].get("source_fields"),
                key_field=self.config["travel_destination_retriever"].get("key_field"),
                value_fields=self.config["travel_destination_retriever"].get("value_fields")
            ),
            "weather_forecaster": lambda kwargs: weather_forecaster.get_forecast(
                weather_dates=kwargs.get("weather_dates", None),
                location=kwargs.get("location", None)
            ),
            "blog_searcher": lambda kwargs: blog_searcher.search_blog(
                query=kwargs.get("query")
            ),
            "travel_itinerary_generator": lambda memory, kwargs: destination_fetcher.fetch(
                memory=memory, 
                input_data=kwargs.get("input_data"),
                index_n=self.config["travel_destination_retriever"].get("index_name"),
                source_fields=self.config["travel_destination_retriever"].get("source_fields"),
                key_field=self.config["travel_destination_retriever"].get("key_field"),
                value_fields=self.config["travel_destination_retriever"].get("value_fields")
            )
        }

    def load(self):
        return TravelItineraryEditorAgent(
            self.planner,
            self.generator,
            self.summarizer,
            self.tools,
            self.config.get("error_message")
        )

class TravelItineraryEditorAgent:
    
    def __init__(
        self,
        planner,
        generator,
        summarizer,
        tools,
        error_message
    ) -> None:
        self.planner = planner
        self.generator = generator
        self.summarizer = summarizer
        self.tools = tools
        self.error_message = error_message
        
        self.preprocessor = ResponsePreprocessor()
        self.korea_time = pytz.timezone('Asia/Seoul')
        self.llm_log = LogCapture("toolva.models.base")
    
    async def run(self, memory_manager: bool, question: str, image=None) -> AsyncGenerator[str, None]:
        session_id = memory_manager.session_id
        memory = memory_manager.get_data()
        logger.info(f"Conversation Memory: {memory}")
        
        today_date = datetime.now(self.korea_time).strftime('%Y-%m-%dT%H:%M:%S')
        
        message = None
        hits = {}
        destination_hits = {}
        input_data = []
        hyperlinks = {}
        previous_itinerary = ""
        if image:
            steps = []
            
            tasks = [self.tools['image_retriever'](image)]
            
            if memory.get("user_message"):
                tasks.append(
                    self.summarizer.asummarize(
                        input=memory.get("user_message"), 
                        output=memory.get("ai_message")
                    )
                )
            
            outputs = await asyncio.gather(*tasks)
            
            destination_hits = outputs[0]
            
            hyperlinks.update(destination_hits.get('hyperlink', {}))
            input_data.append("#### Image Analysis Results: User-uploaded image insights and related content.\n" + str(destination_hits.get("input_data")))
        else:
            tasks = [
                self.planner(
                    today_date=today_date,
                    user_info=memory.get("user_info", {}),
                    travel_info=memory.get("travel_info", {}),
                    history=', '.join(memory.get("history", [])),
                    user=memory.get("user_message"),
                    assistant=memory.get("ai_message"),
                    question=question
                )
            ]
            
            if memory.get("user_message"):
                tasks.append(
                    self.summarizer.asummarize(
                        input=memory.get("user_message"), 
                        output=memory.get("ai_message")
                    )
                )
            
            outputs = await asyncio.gather(*tasks)
            
            plan = outputs[0]
            
            try:
                plan = json.loads(plan)
                logger.info(f"Generated Plan: {plan}")
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                yield json.dumps({
                    "message": self.error_message, 
                    "session_id": session_id
                }) + "\n"
            
            steps = plan.keys()
            for step in steps:
                if step == "message":
                    message = plan[step]
                    if message:
                        formatted_message = message
                        yield json.dumps({
                            "message": message,
                            "session_id": session_id
                        }) + "\n"
                    else:
                        logger.error("Error in Only message tool", input=plan[step])
                
                if step == "travel_info_collector":
                    travel_info, message = self.tools[step](plan[step])
                    if travel_info:
                        formatted_message = message
                        memory["travel_info"] = travel_info
                        if message:
                            yield json.dumps({
                                "message": message,
                                "session_id": session_id
                            }) + "\n"
                    else:
                        logger.error("Error in travel_info_collector tool", input=plan[step], travel_info=travel_info, message=message)
                
                if step == "travel_destination_retriever":
                    if type(plan[step]) == list:
                        for param in plan[step]:
                            tasks = [self.tools[step](memory, param)]
                        
                        all_hits = await asyncio.gather(*tasks)
                        
                        hits = {k: v for hit in all_hits for k, v in hit.items() if k != ['input_data', 'hyperlink']}

                        input_data_combined = [item for hit in all_hits for item in hit.get('input_data', [])]
                        if input_data_combined:
                            hits['input_data'] = input_data_combined
                            
                        hyperlinks_combined = {key: value for hit in all_hits for key, value in hit.get('hyperlink', {}).items()}
                        if hyperlinks_combined:
                            hits['hyperlink'] = hyperlinks_combined

                        destination_hits = hits
                    else:
                        destination_hits = await self.tools[step](memory, plan[step])
                    
                    if destination_hits:
                        hyperlinks.update(destination_hits.get('hyperlink', {}))
                        input_data.append("#### Spotlight Destinations: Personalized tourist spot recommendations.\n" + str(destination_hits.get("input_data")))
                    else:
                        logger.error("Error in travel_destination_retriever tool", input=plan[step], destination_hits=destination_hits)
                
                if step == "weather_forecaster":
                    hits = self.tools[step](plan[step])
                    
                    if hits:
                        hyperlinks.update(hits.get('hyperlink', {}))
                        input_data.append("#### Weather Forecast Snapshot: Real-time weather updates for your travel destination.\n" + str(hits.get("input_data")))
                    else:
                        logger.error("Error in weather_forecaster tool", hits=hits)
                
                if step == "blog_searcher":
                    hits = self.tools[step](plan[step])
                    
                    if hits:
                        hyperlinks.update(hits.get('hyperlink', {}))
                        input_data.append("#### Attraction Review Highlights: Authentic reviews for popular tourist attractions from Google.\n" + str(hits.get("input_data")))
                    else:
                        logger.error("Error in blog_searcher tool", hits=hits)
                
                if step == "travel_itinerary_generator":
                    previous_itinerary = memory.get("itinerary_section", "")
                    logger.info("Load itinerary_section from memory", previous_itinerary=previous_itinerary)
                    
                    previous_hits = await self.tools[step](memory, plan[step])
                    
                    if previous_hits:
                        destination_hits = previous_hits
                        hyperlinks.update(destination_hits.get('hyperlink', {}))
                        input_data.append("#### Spotlight Destinations: Personalized tourist spot recommendations.\n" + str(destination_hits.get("input_data")))
                    else:
                        logger.error("Error in travel_itinerary_generator tool", input=plan[step], memory=memory, previous_hits=previous_hits)
                        
                
        itinerary = {}
        if input_data or "travel_itinerary_generator" in steps or message is None:
            logger.info(f"Relevant Candidates: {input_data}")
            
            input_data = '\n'.join(input_data)
            
            messages = self.generator(
                today_date=today_date,
                user_info=memory.get("user_info", {}),
                travel_info=memory.get("travel_info", {}),
                history=', '.join(memory.get("history", [])),
                user=memory.get("user_message"),
                assistant=memory.get("ai_message"),
                question=question,
                itinerary=previous_itinerary,
                input_data=input_data,
            )
            
            message_list = []
            formatted_message_list = []
            temp_key = []
            collecting_key = False
            for item in messages:
                message_list.append(item)
                
                if "'" in item:
                    item_parts = item.split("'")  # 작은따옴표를 기준으로 item 분할
                    
                    for part in item_parts[:-1]:  # 마지막 부분을 제외하고 모든 부분 처리
                        temp_key.append(part)
                    
                    item = item_parts[-1]  # item을 마지막 부분으로 설정
                    
                    if collecting_key:  # 만약 데이터 수집 중이라면
                        collecting_key = False  # 데이터 수집 종료
                        
                        full_key = self.preprocessor.normalize_text(''.join(temp_key))  # 수집한 데이터를 하나의 문자열로 합치고 정규화
                        
                        try:
                            full_data = hyperlinks[full_key]  # 변환
                        except KeyError:
                            link_from_previous = self.preprocessor.find_key_in_memory(full_key, memory)
                            if link_from_previous:
                                full_data = link_from_previous
                            else:
                                full_data = full_key
                        
                        formatted_message_list.append(full_data)
                        yield json.dumps({
                            "message": full_data,
                            "session_id": session_id
                        }) + "\n"  # 후처리된 데이터 출력
                        
                        formatted_message_list.append(item)
                        yield json.dumps({
                            "message": item,
                            "session_id": session_id
                        }) + "\n"  # 끝나는 작은 따옴표가 포함된 chunk 출력
                        
                        temp_key = []  # 임시 데이터 초기화
                    
                    else:
                        collecting_key = True  # 데이터 수집 시작
                        formatted_message_list.append(item)
                        yield json.dumps({
                            "message": item,
                            "session_id": session_id
                        }) + "\n"  # 시작되는 작은 따옴표가 포함된 chunk 출력
                
                elif collecting_key:
                    temp_key.append(item)  # 데이터 수집 중일 때 임시 리스트에 항목 추가
                
                else:
                    formatted_message_list.append(item)
                    yield json.dumps({
                        "message": item,
                        "session_id": session_id
                    }) + "\n"
            
            if len(steps) == 1 and "blog_searcher" in steps:
                item = "\n\n"
                formatted_message_list.append(item)
                yield json.dumps({
                    "message": item,
                    "session_id": session_id
                }) + "\n"
                
                for title, link in hyperlinks.items():
                    item = f"- {link}\n"
                    formatted_message_list.append(item)
                    yield json.dumps({
                        "message": item,
                        "session_id": session_id
                    }) + "\n"
            
            message = ''.join(message_list)
            formatted_message = ''.join(formatted_message_list)
            
            itinerary = self.preprocessor.preprocess_itinerary(message, destination_hits, memory)
        
            if itinerary:
                yield json.dumps({
                    "message": "",
                    "itinerary_id": itinerary['uuid'],
                    "session_id": session_id
                }) + "\n"
        
        if destination_hits:
            input_data = [hit['_id'] for hit in {k: v for k, v in destination_hits.items() if k not in ['input_data', 'hyperlink']}.values()]
        else:
            if message is None:
                message = self.error_message
                formatted_message = message
                yield json.dumps({
                    "message": message, 
                    "session_id": session_id
                }) + "\n"
            
            input_data = []
        
        new_turn_data = {
            "travel_info": memory.get("travel_info", {}),
            "user_message": question,
            "ai_message": message,
            "formatted_ai_message": formatted_message,
            "input_data": input_data,
            "itinerary": itinerary,
            "image_name": image
        }
        
        if len(outputs) > 1:
            memory_manager.index_data(new_turn_data, outputs[1])
        else:
            memory_manager.index_data(new_turn_data)
            
        logger.info(f"Completed processing for question", output=formatted_message)
        yield json.dumps({"message": "completed", "session_id": session_id})