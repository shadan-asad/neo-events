from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import settings
from app.core.security import get_password_hash
from app.api import deps
from app.schemas.user import User, UserCreate, Token, UserWithToken, LoginRequest
from app.crud import crud_user

router = APIRouter()


@router.post("/register", response_model=UserWithToken)
def register(
    *,
    db: Session = Depends(deps.get_db),
    user_in: UserCreate,
) -> Any:
    """
    Register a new user.

    Creates a new user account with the provided username, email, and password.
    Returns the user object and access token upon successful registration.

    Request Body Example:
    ```json
    {
        "username": "johndoe",
        "email": "john.doe@example.com",
        "password": "securepassword123"
    }
    ```

    Response Example:
    ```json
    {
        "user": {
            "id": 1,
            "username": "johndoe",
            "email": "john.doe@example.com",
            "is_active": true,
            "is_superuser": false,
            "created_at": "2024-03-20T09:00:00Z",
            "updated_at": "2024-03-20T09:00:00Z"
        },
        "tokens": {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        }
    }
    ```

    Error Responses:
    1. Username already exists:
    ```json
    {
        "detail": "Username already registered"
    }
    ```

    2. Email already exists:
    ```json
    {
        "detail": "Email already registered"
    }
    ```

    3. Invalid email format:
    ```json
    {
        "detail": "Invalid email format"
    }
    ```

    4. Password too short:
    ```json
    {
        "detail": "Password must be at least 8 characters long"
    }
    ```

    Notes:
    - Username must be unique
    - Email must be unique and valid
    - Password must be at least 8 characters long
    - The response includes both user details and authentication tokens
    """
    user = crud_user.user.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    user = crud_user.user.get_by_username(db, username=user_in.username)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    user = crud_user.user.create(db, obj_in=user_in)
    tokens = security.create_tokens(user.id)
    return {"user": user, "tokens": tokens}


@router.post("/login", response_model=UserWithToken)
def login(
    db: Session = Depends(deps.get_db),
    login_data: LoginRequest = None,
) -> Any:
    """
    Login with email/username and password.

    Authenticates a user using either their email or username along with their password.
    Returns the user object and access token upon successful authentication.

    Request Body Examples:

    1. Login with email:
    ```json
    {
        "email": "john.doe@example.com",
        "password": "securepassword123"
    }
    ```

    2. Login with username:
    ```json
    {
        "username": "johndoe",
        "password": "securepassword123"
    }
    ```

    Response Example:
    ```json
    {
        "user": {
            "id": 1,
            "username": "johndoe",
            "email": "john.doe@example.com",
            "is_active": true,
            "is_superuser": false,
            "created_at": "2024-03-20T09:00:00Z",
            "updated_at": "2024-03-20T09:00:00Z"
        },
        "tokens": {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        }
    }
    ```

    Error Responses:
    1. Invalid credentials:
    ```json
    {
        "detail": "Incorrect email/username or password"
    }
    ```

    2. Inactive user:
    ```json
    {
        "detail": "Inactive user"
    }
    ```

    3. Missing credentials:
    ```json
    {
        "detail": "Either email or username must be provided"
    }
    ```

    Notes:
    - Either email or username must be provided (not both)
    - Password is required
    - The response includes both user details and authentication tokens
    """
    if login_data.email:
        user = crud_user.user.authenticate(
            db, email=login_data.email, password=login_data.password
        )
    elif login_data.username:
        user = crud_user.user.authenticate(
            db, username=login_data.username, password=login_data.password
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either email or username must be provided"
        )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/username or password"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    tokens = security.create_tokens(user.id)
    return {"user": user, "tokens": tokens}


@router.get("/me", response_model=User)
def read_users_me(
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user information.

    Returns the details of the currently authenticated user.

    Headers Required:
    ```
    Authorization: Bearer <access_token>
    ```

    Response Example:
    ```json
    {
        "id": 1,
        "username": "johndoe",
        "email": "john.doe@example.com",
        "is_active": true,
        "is_superuser": false,
        "created_at": "2024-03-20T09:00:00Z",
        "updated_at": "2024-03-20T09:00:00Z"
    }
    ```

    Error Responses:
    1. Missing token:
    ```json
    {
        "detail": "Not authenticated"
    }
    ```

    2. Invalid token:
    ```json
    {
        "detail": "Could not validate credentials"
    }
    ```

    3. Expired token:
    ```json
    {
        "detail": "Token has expired"
    }
    ```

    4. Inactive user:
    ```json
    {
        "detail": "Inactive user"
    }
    ```

    Notes:
    - Requires a valid JWT access token in the Authorization header
    - Token must not be expired
    - User must be active
    """
    return current_user


@router.post("/refresh", response_model=UserWithToken)
def refresh_token(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Refresh access token.

    Generates new access and refresh tokens for the current user.

    Headers Required:
    ```
    Authorization: Bearer <access_token>
    ```

    Response Example:
    ```json
    {
        "user": {
            "id": 1,
            "username": "johndoe",
            "email": "john.doe@example.com",
            "is_active": true,
            "is_superuser": false,
            "created_at": "2024-03-20T09:00:00Z",
            "updated_at": "2024-03-20T09:00:00Z"
        },
        "tokens": {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        }
    }
    ```

    Error Responses:
    1. Missing token:
    ```json
    {
        "detail": "Not authenticated"
    }
    ```

    2. Invalid token:
    ```json
    {
        "detail": "Could not validate credentials"
    }
    ```

    3. Expired token:
    ```json
    {
        "detail": "Token has expired"
    }
    ```

    4. Inactive user:
    ```json
    {
        "detail": "Inactive user"
    }
    ```

    Notes:
    - Requires a valid JWT access token in the Authorization header
    - Token must not be expired
    - User must be active
    - Returns new access and refresh tokens
    """
    tokens = security.create_tokens(current_user.id)
    return {"user": current_user, "tokens": tokens}


@router.post("/logout")
def logout(
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Logout user (invalidate token).
    """
    # In a real application, you would want to blacklist the token
    # This is a simplified version
    return {"msg": "Successfully logged out"} 