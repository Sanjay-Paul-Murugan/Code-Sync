import random
import string
from fastapi import WebSocket
from typing import Dict, List
from database import redis_client
from tasks import persist_room_code_to_db



class CodeSyncManager:
    def __init__(self):
        self.rooms: Dict[str, List[WebSocket]] = {}

    def generate_room_id(self) -> str:
        invite_code = "".join(random.choices(string.digits,k=6))
        return invite_code

    async def connect_user_to_room(self, room_id: str, websocket: WebSocket):
        await websocket.accept()

        state_key = f"room_state:{room_id}"
        current_code = redis_client.get(state_key)

        if current_code:
            await websocket.send_text(current_code)

        if room_id not in self.rooms:
            self.rooms[room_id]=[]
        self.rooms[room_id].append(websocket)

    def disconnect_user_from_room(self, room_id: str, websocket: WebSocket):
    
       
        if room_id in self.rooms:
            self.rooms[room_id].remove(websocket)

            if not self.rooms[room_id]:
                #trigger the celery worker to save the code if the room is empty
                persist_room_code_to_db.delay(room_id)

                del self.rooms[room_id]


    async def broadcast_to_room(self, room_id: str, message: str, sender: WebSocket):
       
        if room_id in self.rooms:

            for conn in self.rooms[room_id]:
                if conn!=sender:
                    await conn.send_text(message)


code_sync_manager = CodeSyncManager()