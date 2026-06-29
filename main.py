from collaboration import code_sync_manager
from fastapi import WebSocket, WebSocketDisconnect, FastAPI, Depends, HTTPException, status
from fastapi import FastAPI,Body,Depends,Request
from database import async_engine, Base,redis_client,async_redis_client,sessionLocal
from tasks import execute_room_code
import models
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from database import sessionLocal
from sqlalchemy import text
from jose import jwt
from datetime import datetime,timedelta
from auth import create_access_token,SECRET_KEY,ALGORITHM
from jose import jwt,JWTError



app = FastAPI()

async def rate_limit_execution(request : Request,room_id : str):

    client_ip = request.client.host
    rate_key = f"rate_limit:run:{room_id}:{client_ip}"

    request_count = await async_redis_client.incr(rate_key)

    if request_count ==1:

        await async_redis_client.expire(rate_key,10)
    
    if request_count>3:
        print(f"Rate limit : blocked execution from {client_ip} in room {room_id}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="You are compiling too fast, please wait a few seconds"
        )
    return True
    



def verify_ws_token(token:str):
    if not token:
        return None
    try :
        payload = jwt.decode(token,SECRET_KEY,algorithms=[ALGORITHM])
        user_id : str = payload.get("sub")
        if user_id is None:
            return None
        return user_id
    except JWTError:
        return None
        





async def get_db():
    async with sessionLocal() as session:
        yield session


@app.on_event("startup")
async def startup_event():
    async with async_engine.begin() as conn:
        # This reads models.py and creates tables if they don't exist yet
        await conn.run_sync(Base.metadata.create_all)



@app.get("/test-login/{user_id}")
async def get_test_token(user_id:str):

    token = create_access_token(user_id)
    return{
        "acsess token" : token,
        "type" : "bearer"
    }




@app.post("/rooms/create",status_code=status.HTTP_201_CREATED)
async def create_new_room(db:AsyncSession = Depends(get_db)):

    new_room_id = code_sync_manager.generate_room_id()

    try:

        new_room = models.Rooms(room_id = new_room_id,saved_code="")

        db.add(new_room)
        await db.commit()
        await db.refresh(new_room)

        return{
            "message": "Collaborative CodeSpace successfully orchestrated",
            "room_id": new_room_id
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f" database orchestration failure : {str(e)}"
        )


#async listener function 
async def listen_to_pubsub(room_id:str,websocket:WebSocket):

    pubsub = async_redis_client.pubsub()
    await pubsub.subscribe(f"room_output:{room_id}")

    async for messages in pubsub.listen():

        if messages["type"] == "message":

            terminal_output = f"TERMINAL OUTPUT : \n{messages['data']}"
            await websocket.send_text(terminal_output)

@app.websocket("/ws/code/{room_id}")
async def websocket_code_sync(websocket:WebSocket,room_id:str,token:str=None):


    #JWT auth verification
    user_id = verify_ws_token(token)
    if not user_id:
        await websocket.accept()
        await websocket.send_text("error : unauthorized or invalid or missing jwt token")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        print("Blocked unauthenticated access")
        return




    #room verification 
    async with sessionLocal() as db:
        result = await db.execute(
            text("SELECT 1 FROM rooms WHERE room_id = :room_id LIMIT 1"), 
            {"room_id": room_id}
        )
        room_exists = result.scalar()

        if not room_exists:

            await websocket.accept()
            await websocket.send_text("Error: invvalid invitation code")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            print(f"Blocked connection due to invalid room id : {room_id}")
            return


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

@app.post("/room/{room_id}/run",dependencies=[Depends(rate_limit_execution)])
async def run_room_code(room_id:str,language:str=Body(default="python",embed=True)):


    #running the code asynchronosly [.delay()]
    task = execute_room_code.delay(room_id,language)

    return {"message": "Execution started in background", "task_id": task.id}


