from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import Review as ReviewSchema
from app.models import Review as ReviewModel
from app.db_depends import get_async_db

router = APIRouter(
    prefix="/reviews",
    tags=["reviews"]
)

@router.get("/", response_model=list[ReviewSchema])
async def get_all_reviews(db: AsyncSession = Depends(get_async_db)):
    reviews_result = await db.scalars(
        select(ReviewModel).where(ReviewModel.is_active == True)
    )
    db_reviews = reviews_result.all()
    return db_reviews