
from jose import jwt
from datetime import datetime, timedelta

SECRET_KEY = "my_super_secret_key"
ALGORITHM = "HS256"

def create_access_token(user_id:str):

    expire = datetime.utcnow() + timedelta(hours=1)

    to_encode = {"sub":user_id,"exp":expire}

    encoded_jwt = jwt.encode(to_encode,SECRET_KEY,algorithm = ALGORITHM)
    return encoded_jwt