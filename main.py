from collaboration import code_sync_manager
from fastapi import WebSocket, WebSocketDisconnect, FastAPI, Depends, HTTPException, status
from fastapi import FastAPI
from database import async_engine, Base,redis_client


app = FastAPI()




@app.on_event("startup")
async def startup_event():
    async with async_engine.begin() as conn:
        # This reads models.py and creates tables if they don't exist yet
        await conn.run_sync(Base.metadata.create_all)




@app.websocket("/ws/code/{room_id}")
async def websocket_code_sync(websocket:WebSocket,room_id:str):

    await code_sync_manager.connect_user_to_room(room_id,websocket)

    try:

        while True:
            data = await websocket.receive_text()

            state_key = f"room_state:{room_id}"
            redis_client.set(state_key,data)

            await code_sync_manager.broadcast_to_room(room_id,message = data, sender = websocket)
    except WebSocketDisconnect:
        code_sync_manager.disconnect_user_from_room(room_id,websocket)

