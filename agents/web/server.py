from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from agents.core.events import EventEmitter
from agents.adapters.adapter import ClaudeAdapter
from agents.core.orchestrator import Orchestrator
from agents.web.intent import parse_intent
import asyncio
import json
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI()
global_emitter = EventEmitter()

async def handle_user_request(text: str, emitter: EventEmitter):
    logger.info(f"Starting handle_user_request for: {text}")
    try:
        # 使用 ClaudeAdapter 作为底层 LLM 驱动
        adapter = ClaudeAdapter()
        logger.info("Initialized ClaudeAdapter")
        
        # 解析用户意图
        intent = await parse_intent(text, adapter)
        logger.info(f"Parsed intent: {intent}")
        
        leagues = intent.get("leagues")
        date = intent.get("date")
        models = intent.get("models", ["v4.0"])
        
        # 初始化 Orchestrator 并启动流水线
        orchestrator = Orchestrator(adapter=adapter, semi_mode=False, emitter=emitter)
        logger.info("Initialized Orchestrator, calling run()")
        await orchestrator.run(leagues=leagues, date=date, models=models)
        logger.info("Orchestrator run() finished")
        
    except Exception as e:
        logger.error(f"Error in handle_user_request: {str(e)}", exc_info=True)
        await emitter.emit("match_step_error", {"match_id": "system", "message": f"系统错误: {str(e)}"})

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection accepted")
    
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
            
            # Start background pipeline
            asyncio.create_task(handle_user_request(text, global_emitter))
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    finally:
        global_emitter.unsubscribe(on_event)
