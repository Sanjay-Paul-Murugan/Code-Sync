import time
from celery import Celery
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import redis_client
import models

celery_app = Celery(
    "tasks", 
    broker="redis://localhost:6379/0", 
    backend="redis://localhost:6379/0"
)


SYNC_DATABASE_URL = "postgresql://postgres:sanjay@localhost:5432/projects"
sync_engine = create_engine(SYNC_DATABASE_URL)
SessionLocalSync = sessionmaker(bind=sync_engine)


@celery_app.task
def persist_room_code_to_db(room_id:str):

    state_key = f"room_state:{room_id}"
    latest_code = redis_client.get(state_key)

    db=SessionLocalSync()

    try:

        room_record = db.query(models.Rooms).filter(models.Rooms.room_id==room_id).first()

        if room_record:
            #overwriting the code

            room_record.saved_code = latest_code
            db.commit()
            print("Room successfully saved to postgres")
        else:
            print("Room doesnot exists")
    except Exception as e:
        db.rollback()
        print(f"Error saving room : {str(e)}")
    finally:
        db.close()
