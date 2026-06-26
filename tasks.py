import time
from celery import Celery
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import redis_client
import models
import subprocess
import sys


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


@celery_app.task
def execute_room_code(room_id:str,language:str):
    print(f"executing code for room_id :{room_id}")

    state_key = f"room_state:{room_id}"
    code_to_run = redis_client.get(state_key)

    if not code_to_run:
        return "Error : no code found in workspace"
    
    if language.lower() == "python":
        try:

            result = subprocess.run(
                [sys.executable,"-c",code_to_run],
                capture_output=True,
                text=True,
                timeout= 5
            )
            output = result.stdout if result.returncode==0 else result.stderr
        except subprocess.TimeoutExpired:
            output = "error : process timedout after 5 sec"
        except Exception as e:
            output = f"error : {str(e)}"
    else:
        output = f"language : {language} is not implemented yet"
    

    redis_client.publish(f"room_output:{room_id}",output)
    print("Celery execution finished , output is broadcasted to redis")
    return output
