from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import Review as ReviewSchema, ReviewCreate
from app.models import Review as ReviewModel, User as UserModel, Product as ProductModel
from app.db_depends import get_async_db
from app.auth import get_current_buyer

router = APIRouter(
    prefix="/reviews",
    tags=["reviews"]
)

@router.get("/", response_model=list[ReviewSchema])
async def get_all_reviews(db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех отзывов.
    """
    reviews_result = await db.scalars(
        select(ReviewModel).where(ReviewModel.is_active == True)
    )
    db_reviews = reviews_result.all()
    return db_reviews

async def upgrade_product_rating(product: ProductModel, db: AsyncSession):
    """
    Пересчитывает средний рейтинг товара на основе всех отзывов.
    """
    avg_grade_result = await db.scalars(
        select(func.avg(ReviewModel.grade)).where(
            ReviewModel.product_id == product.id, ReviewModel.is_active == True
        )
    )
    rating = avg_grade_result.first()
    product.rating = rating or 0.0
    await db.commit()

@router.post("/", response_model=ReviewSchema)
async def create_review(
    review: ReviewCreate, 
    buyer: UserModel = Depends(get_current_buyer),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Создаёт новый отзыв, привязанный к текущему покупателю (только для 'buyer').
    """
    product_result = await db.scalars(
        select(ProductModel).where(ProductModel.id == review.product_id, ProductModel.is_active == True)
    )
    db_product = product_result.first()
    if db_product is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product not found")

    review_result = await db.scalars(
        select(ReviewModel).where(
            ReviewModel.user_id == buyer.id, 
            ReviewModel.product_id == db_product.id, 
            ReviewModel.is_active == True
        )
    )
    db_review = review_result.first()
    if db_review is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Review already exist")

    db_review = ReviewModel(**review.model_dump(), user_id=buyer.id)
    db.add(db_review)
    await db.commit()
    await db.refresh(db_review)

    await upgrade_product_rating(db_product, db)

    return db_review