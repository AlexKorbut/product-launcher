from fastapi import APIRouter, HTTPException, status

from app.schemas import LoginRequest, TokenResponse
from app.security import create_token, verify_credentials

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    if not verify_credentials(body.email, body.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return TokenResponse(access_token=create_token(body.email))
