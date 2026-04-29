from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from agents.core.events import EventEmitter
import asyncio
import json

app = FastAPI()
global_emitter = EventEmitter()

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    
    # Setup listener for this connection
    async def on_event(name: str, payload: dict):
        await websocket.send_json({"type": name, "payload": payload})
        
    global_emitter.subscribe(on_event)
    
    try:
        while True:
            text = await websocket.receive_text()
            # Send immediate ack
            await websocket.send_json({
                "type": "chat_chunk", 
                "payload": {"text": f"正在处理您的请求: {text}"}
            })
            # In a real scenario, this would spawn parse_intent & orchestrator.run
            # asyncio.create_task(handle_user_request(text, global_emitter))
    except WebSocketDisconnect:
        pass
