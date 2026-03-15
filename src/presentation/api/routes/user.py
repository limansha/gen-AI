from pydantic import BaseModel

from fastapi import APIRouter, Depends

from src.domain.entities.user import User
from src.presentation.api.dependencies import get_current_user

router = APIRouter(prefix="/api", tags=["user"])


class UserResponse(BaseModel):
    id: str
    email: str
    name: str


@router.get("/user", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
    )

