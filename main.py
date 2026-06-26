from collaboration import code_sync_manager
from fastapi import WebSocket, WebSocketDisconnect, FastAPI, Depends, HTTPException, status
from fastapi import FastAPI,Body
from database import async_engine, Base,redis_client,async_redis_client
from tasks import execute_room_code
import asyncio


app = FastAPI()




@app.on_event("startup")
async def startup_event():
    async with async_engine.begin() as conn:
        # This reads models.py and creates tables if they don't exist yet
        await conn.run_sync(Base.metadata.create_all)



#async listener function 
async def listen_to_pubsub(room_id:str,websocket:WebSocket):

    pubsub = async_redis_client.pubsub()
    await pubsub.subscribe(f"room_output:{room_id}")

    async for messages in pubsub.listen():

        if messages["type"] == "message":

            terminal_output = f"TERMINAL OUTPUT : \n{messages['data']}"
            await websocket.send_text(terminal_output)

@app.websocket("/ws/code/{room_id}")
async def websocket_code_sync(websocket:WebSocket,room_id:str):

    await code_sync_manager.connect_user_to_room(room_id,websocket)

    pubsub_task = asyncio.create_task(listen_to_pubsub(room_id,websocket))

    try:

        while True:
            data = await websocket.receive_text()

            state_key = f"room_state:{room_id}"
            redis_client.set(state_key,data)

            await code_sync_manager.broadcast_to_room(room_id,message = data, sender = websocket)
    except WebSocketDisconnect:
        code_sync_manager.disconnect_user_from_room(room_id,websocket)
        pubsub_task.cancel()

@app.post("/room/{room_id}/run")
async def run_room_code(room_id:str,language:str=Body(default="python",embed=True)):


    #running the code asynchronosly [.delay()]
    task = execute_room_code.delay(room_id,language)

    return {"message": "Execution started in background", "task_id": task.id}


