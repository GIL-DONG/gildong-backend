from fastapi.testclient import TestClient
from sllm_api import app

client = TestClient(app)

def test_sllm_summ_endpoint():
    # Given
    test_data = {
        "user_message": "나는 가족들과 부산여행을 2박 3일로 즐기고 싶어. 어딜가면 좋을까?",
        "ai_message": "부산여행은 해운대를 추천합니다.!"
    }

    # When
    response = client.post("/sllm/summ", json=test_data)

    # Then
    assert response.status_code == 200
    # 여기에 추가적인 응답 내용 검증 로직을 넣을 수 있습니다.
    # 예: assert "response_key" in response.json()
