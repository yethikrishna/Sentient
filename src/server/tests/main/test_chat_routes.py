import json
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

# --- Test /chat/message ---

def test_chat_message_success(client: TestClient, mocker):
    # Mock the LLM stream generator
    async def mock_stream(*args, **kwargs):
        yield {"type": "assistantStream", "token": "Hello", "messageId": "assistant-123"}
        yield {"type": "assistantStream", "token": " World", "messageId": "assistant-123"}
        yield {"type": "assistantStream", "token": "", "done": True, "messageId": "assistant-123"}

    mocker.patch('main.chat.routes.generate_chat_llm_stream', new=mock_stream)
    mock_add_message = mocker.patch('main.dependencies.mongo_manager.add_message', new_callable=AsyncMock)

    response = client.post(
        "/chat/message",
        headers={"Authorization": "Bearer test-token"},
        json={"messages": [{"role": "user", "content": "Hi", "id": "user-1"}]}
    )

    assert response.status_code == 200
    assert "application/x-ndjson" in response.headers["content-type"]
    
    # Check if user message was saved
    mock_add_message.assert_any_call(user_id="test-user-123", role="user", content="Hi", message_id="user-1")
    
    # Check streamed content
    lines = response.text.strip().split('\n')
    assert len(lines) == 3
    assert json.loads(lines[0]) == {"type": "assistantStream", "token": "Hello", "messageId": "assistant-123"}
    assert json.loads(lines[1]) == {"type": "assistantStream", "token": " World", "messageId": "assistant-123"}

def test_chat_message_no_user_message(client: TestClient):
    response = client.post(
        "/chat/message",
        headers={"Authorization": "Bearer test-token"},
        json={"messages": [{"role": "assistant", "content": "How can I help?"}]}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "No user message found in the request."

# --- Test /chat/history ---

def test_get_chat_history(client: TestClient, mock_mongo_manager):
    mock_history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"}
    ]
    mock_mongo_manager.get_message_history.return_value = list(reversed(mock_history)) # DB returns newest first

    response = client.get("/chat/history", headers={"Authorization": "Bearer test-token"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["messages"] == mock_history # Endpoint should reverse it back to chronological
    mock_mongo_manager.get_message_history.assert_called_once()

# --- Test /chat/delete ---

def test_delete_single_message(client: TestClient, mock_mongo_manager):
    response = client.post(
        "/chat/delete",
        headers={"Authorization": "Bearer test-token"},
        json={"message_id": "msg-to-delete"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Message deleted successfully."
    mock_mongo_manager.delete_message.assert_called_once_with("test-user-123", "msg-to-delete")

def test_clear_all_messages(client: TestClient, mock_mongo_manager):
    response = client.post(
        "/chat/delete",
        headers={"Authorization": "Bearer test-token"},
        json={"clear_all": True}
    )
    assert response.status_code == 200
    assert "Successfully deleted 5 messages" in response.json()["message"]
    mock_mongo_manager.delete_all_messages.assert_called_once_with("test-user-123")

def test_delete_invalid_request(client: TestClient):
    response = client.post(
        "/chat/delete",
        headers={"Authorization": "Bearer test-token"},
        json={} # Empty body
    )
    assert response.status_code == 400