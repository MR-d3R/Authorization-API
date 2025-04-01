import json
import models
import secrets
import requests
from icecream import ic
from pathlib import Path
from datetime import datetime, timedelta
from passlib.context import CryptContext
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import Optional
from jose import jwt, JWTError

from logger.logger import ColorfulLogger
from configurator.utils import load_and_validate_config

#! Конфигурация
CONFIG_PATH = Path("config.json")
LOCAL_API_URL = "http://web:8000"
config = load_and_validate_config(CONFIG_PATH)

app = FastAPI()
logger = ColorfulLogger(config=config)
SECRET_KEY = app.secret_key = secrets.token_hex(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

#! Хранилище для кодов верификации
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# Вспомогательные функции
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    try:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now() + expires_delta
        else:
            expire = datetime.now() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire})
        encode_jwt = jwt.encode(to_encode, key=SECRET_KEY, algorithm=ALGORITHM)
        return encode_jwt

    except Exception as e:
        ic(f"Token creation error: {str(e)}")
        return False


def update_token_in_DB(username, access_token):
    try:
        service_name = config.service_name
        local_api_data = {
            "micro_name": {
                "name": service_name
            },
            "token_data": {
                "login": username,
                "jwt_token": access_token
            }
        }
        response = requests.post(f"{LOCAL_API_URL}/token/update",
                                 json=local_api_data)
        if not response.ok:
            ic(f"Token update failed with status {response.status_code}: {response.text}"
               )
            return False
        return True

    except requests.RequestException as e:
        ic(f"Network error while updating token: {str(e)}")
        return False
    except Exception as e:
        ic(f"Unexpected error while updating token: {str(e)}")
        return False


def get_user(username: str):
    try:
        service_name = config.service_name
        local_api_data = {"name": service_name}
        response = requests.get(f"{LOCAL_API_URL}/data/{username}",
                                json=local_api_data)

        if not response.ok:
            ic(f"Failed to get user data. Status: {response.status_code}, Response: {response.text}"
               )
            return None

        response_json = response.json()
        data = response_json.get("data")

        if not data:
            ic(f"No data found for user: {username}")
            return None

        return data

    except requests.RequestException as e:
        ic(f"Network error while getting user data: {str(e)}")
        return None
    except json.JSONDecodeError as e:
        ic(f"Invalid JSON response while getting user data: {str(e)}")
        return None
    except Exception as e:
        ic(f"Unexpected error while getting user data: {str(e)}")
        return None


# Эндпоинты
@app.post("/login", response_model=models.Token)
async def login(user_data: models.User):
    user = get_user(user_data.username)

    if not user:
        ic(f"Login failed: User not found - {user_data.username}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="User not found")

    if not verify_password(user_data.password, user["password"]):
        ic(f"Login failed: Invalid password for user - {user_data.username}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Incorrect password")

    access_token = create_access_token(
        data={
            "sub": user["login"],
            "ngy": user["agency_id"]
        },
        expires_delta=timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS))

    if not access_token:
        ic(f"Login failed: Token creation error for user - {user_data.username}"
           )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to create access token")

    if not update_token_in_DB(user_data.username, access_token):
        ic(f"Login failed: Token update in DB error for user - {user_data.username}"
           )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to update token in database")

    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/token/create", response_model=models.Token)
async def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends()):

    user = get_user(form_data.username)

    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Incorrect username or password",
                            headers={"WWW-Authenticate": "Bearer"})

    access_token = create_access_token(
        data={
            "sub": user["login"],
            "ngy": user["agency_id"]
        },
        expires_delta=timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS))

    if not access_token:
        raise HTTPException(status_code=400, detail="Token creation error")

    updated = update_token_in_DB(form_data.username, access_token)

    if updated:
        return {"access_token": access_token, "token_type": "bearer"}
    else:
        raise HTTPException(status_code=400, detail="Token update in DB error")


@app.post("/token/verify")
async def verify_token(token_data: models.TokenVerify):
    try:
        payload = jwt.decode(token_data.token,
                             key=SECRET_KEY,
                             algorithms=[ALGORITHM])
        username = payload.get("sub")

        if not username:
            ic("Token verification failed: No username in token")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Invalid token: missing username")

        exp_timestamp = payload.get("exp")
        if not exp_timestamp:
            ic("Token verification failed: No expiration in token")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Invalid token: missing expiration")

        exp_datetime = datetime.fromtimestamp(exp_timestamp)
        if datetime.now() >= exp_datetime:
            ic(f"Token verification failed: Token expired for user - {username}"
               )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Token has expired")

        agency_id = payload.get("ngy")
        if not agency_id:
            ic("Agency ID not found in token!")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Invalid token: missing expiration")

        user = get_user(token_data.username)
        if not user:
            ic(f"Token verification failed: User not found - {token_data.username}"
               )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="User not found")

        stored_token = user.get("jwt_token")
        if stored_token != token_data.token:
            ic(f"Token verification failed: Tokens do not match for user - {token_data.username}"
               )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: does not match stored token")

        return {"valid": True, "user_id": username, "agency_id": agency_id}

    except JWTError as e:
        ic(f"Token verification failed: JWT decode error - {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid token format")


@app.post("/token/refresh", response_model=models.Token)
async def refresh_token(token_data: models.TokenRefresh):
    try:
        payload = jwt.decode(token_data.refresh_token,
                             key=SECRET_KEY,
                             algorithms=ALGORITHM)
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=400,
                                detail="Invalid refresh token")

        access_token = create_access_token(
            data={"sub": username},
            expires_delta=timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS))

        if not access_token:
            raise HTTPException(status_code=400, detail="Token update error")

        updated = update_token_in_DB(token_data.username, access_token)

        if updated:
            return {"access_token": access_token, "token_type": "bearer"}
        else:
            raise HTTPException(status_code=400,
                                detail="Token update in DB error")

    except jwt.PyJWTError:
        raise HTTPException(status_code=400, detail="Invalid refresh token")


@app.post("/logout")
async def logout(token_data: models.TokenVerify):
    try:
        valid_response = await verify_token(token_data)
        if not valid_response.get("valid"):
            ic(f"Logout failed: Invalid token for user - {token_data.username}"
               )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid token")

        service_name = config.service_name
        local_api_data = {
            "micro_name": {
                "name": service_name
            },
            "token_data": {
                "login": token_data.username,
                "jwt_token": token_data.token
            }
        }

        response = requests.delete(f"{LOCAL_API_URL}/token/delete",
                                   json=local_api_data)

        if not response.ok:
            ic(f"Logout failed: Token deletion error - Status: {response.status_code}, Response: {response.text}"
               )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete token from database")

        return {"message": "Successfully logged out"}

    except HTTPException:
        raise
