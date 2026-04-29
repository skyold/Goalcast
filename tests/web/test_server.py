import pytest
from fastapi.testclient import TestClient
from agents.web.server import app

def test_websocket_chat():
    client = TestClient(app)
    with client.websocket_connect("/ws/chat") as websocket:
        websocket.send_text("Hello")
        data = websocket.receive_json()
        assert data["type"] == "chat_chunk"
        assert "正在处理" in data["payload"]["text"]
