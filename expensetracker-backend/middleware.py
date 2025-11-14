import jwt
from dotenv import load_dotenv 
import os
from datetime import datetime, timedelta
from fastapi import Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Security

bearer = HTTPBearer()

load_dotenv()

secret_key = os.getenv("secret_key")

def create_token(request, expiry):
    expire = datetime.now() + timedelta(minutes=expiry)
    
    request.update({'exp': expire})
    
    token = jwt.encode(request,secret_key )
    
    return token

def verify_token(request: HTTPAuthorizationCredentials = Security(bearer)):
    
    token = request.credentials
    
    verified_token =jwt.decode(token, secret_key, algorithms=["HS256"])
    
    # expiry_time = verified_token.get("exp")
    
    
    
    return {
        "email": verified_token.get("email"),
        "userType": verified_token.get("userType"),
        "id" : verified_token.get("id")
    }   