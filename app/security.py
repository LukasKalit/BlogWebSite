from fastapi.security import OAuth2
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi import Request, Depends
from fastapi.security.utils import get_authorization_scheme_param
from fastapi import HTTPException
from fastapi import status
from typing import Optional
from typing import Dict
from jose import JWTError, jwt, ExpiredSignatureError
from passlib.context import CryptContext
from typing import Union
from datetime import datetime, timedelta
from . import schemas, crud, database
from sqlalchemy.orm import Session
from fastapi.responses import  RedirectResponse

class OAuth2PasswordBearerWithCookie(OAuth2):
    def __init__(
        self,
        tokenUrl: str,
        scheme_name: Optional[str] = None,
        scopes: Optional[Dict[str, str]] = None,
        auto_error: bool = True,
    ):
        if not scopes:
            scopes = {}
        flows = OAuthFlowsModel(password={"tokenUrl": tokenUrl, "scopes": scopes})
        super().__init__(flows=flows, scheme_name=scheme_name, auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[str]:
        authorization = request.headers.get("Authorization")
        if authorization == None:
            authorization: str = request.cookies.get("access_token")  #changed to accept access token from httpOnly Cookie
        print("access_token is",authorization)

        scheme, param = get_authorization_scheme_param(authorization)
        if not authorization or scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None
        return param



SECRET_KEY = "b02a28fa93c2e6f49b7060483aae1a55050db8e7fea1b53c4efe4ea999e89bd8"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="token", auto_error=False)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def authenticate_user(username: str, password: str, db):
    try:
        user = crud.get_user_by_name(db, username)
    except:
        user = None
    if not user:
        return False
    if not verify_password(password, user.password):
        return False
    return user


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(db:Session = Depends(database.get_db), token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            print ("credentials_exception: User name is None")
            raise credentials_exception
        
        token_data = schemas.TokenData(username=username)

    except ExpiredSignatureError:
        token = "expired"
        return token

    except JWTError:
        print ("credentials_exception: something worng with jwt.decode function")
        raise credentials_exception
    
    except:
        # exceptions may include no token, expired JWT, malformed JWT,
        # or database errors - either way we ignore them and return None
        return None
    
    user = crud.get_user_by_name(db, username=token_data.username)
    if user is None:
        print ("credentials_exception: user doesnt exist")
        raise credentials_exception
    return user

def get_current_user_required(user: Union[schemas.User, None] = Depends(get_current_user)) -> Union[schemas.User, None]:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="An authenticated user is required for that action.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

from functools import wraps

# Under work
def admin_privilages(original_function):
    @wraps(original_function)
    async def wrapper_function(*args, **kwargs):
        pass
        return await original_function(*args, **kwargs)
    return wrapper_function
# -----------------

def expired_redirection(original_function):
    @wraps(original_function)
    async def wrapper_function(**kwargs):
        if kwargs["current_user"] == "expired":
            response = RedirectResponse('/login/?error=True')
            response.status_code = 302  
            return response
        return await original_function(**kwargs)
    return wrapper_function

def owner_privilages(original_function):
    @wraps(original_function)
    def wrapper_function(**kwargs):
        data = crud.get_post(kwargs["db"], kwargs["id"])
        print(data)
        if kwargs["current_user"].id == data.owner_id:
            return original_function(**kwargs)
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="An authenticated user is required for that action.",
                headers={"WWW-Authenticate": "Bearer"},
            )
    return wrapper_function