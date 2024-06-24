import os
from fastapi import APIRouter, File, UploadFile
from typing import List
from pydantic import BaseModel
from google.cloud import speech
import librosa
import tempfile

router = APIRouter()

class FileUploadResponse(BaseModel):
    transcripts: List[str]

def run_stt(audio_file_path):
    client = speech.SpeechClient()

    with open(audio_file_path, "rb") as audio_file:
        audio_content = audio_file.read()
    
    audio = speech.RecognitionAudio(content=audio_content)

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
        sample_rate_hertz=48000,
        audio_channel_count=1,
        language_code="ko-KR"
    )

    operation = client.long_running_recognize(config=config, audio=audio)

    print("Waiting for operation to complete...")
    operation_result = operation.result(timeout=90)

    transcript_builder = []
    for result in operation_result.results:
        transcript_builder.append(f"\nTranscript: {result.alternatives[0].transcript}")
        transcript_builder.append(f"\nConfidence: {result.alternatives[0].confidence}")

    transcript = "".join(transcript_builder)
    print(transcript)

    return transcript

@router.post("/STT", response_model=FileUploadResponse)
async def upload_audios(in_files: List[UploadFile]):

    transcripts = []

    for file in in_files:
        # 임시 파일 생성
        with tempfile.NamedTemporaryFile(delete=False) as temp_audio_file:
            temp_audio_path = temp_audio_file.name
            temp_audio_file.write(await file.read())

        # Perform STT on the uploaded audio
        # sample_rate_hertz = librosa.get_samplerate(temp_audio_path)
        result = run_stt(temp_audio_path)

        # 결과를 리스트에 추가
        transcripts.append(result)

        # 임시 파일 삭제
        os.remove(temp_audio_path)

    return {"transcripts": transcripts}
