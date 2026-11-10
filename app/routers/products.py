from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.products import Product as ProductModel
from app.models.categories import Category as CategoryModel
from app.models.users import User as UserModel
from app.schemas import Product as ProductSchema, ProductCreate
from app.auth import get_current_seller
from app.db_depends import get_async_db

router = APIRouter(
    prefix="/products",
    tags=["products"]
)

@router.get("/", response_model=list[ProductSchema])
async def get_all_products(db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех товаров.
    """
    db_scalars = await db.scalars(
        select(ProductModel).where(ProductModel.is_active == True)
    )
    return db_scalars.all()

@router.post("/", response_model=ProductSchema, status_code=status.HTTP_201_CREATED)
async def create_product(
    product: ProductCreate,
    seller: UserModel = Depends(get_current_seller),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Создаёт новый товар, привязанный к текущему продавцу (только для 'seller').
    """
    category_result = await db.scalars(
        select(CategoryModel).where(CategoryModel.id == product.category_id, CategoryModel.is_active == True)
    )
    db_category = category_result.first()
    if db_category is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category not found or inactive")

    db_product = ProductModel(**product.model_dump(), seller_id=seller.id)
    db.add(db_product)
    await db.commit()
    await db.refresh(db_product)

    return db_product

@router.get("/category/{category_id}", response_model=list[ProductSchema])
async def get_products_by_category(category_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список товаров в указанной категории по её ID.
    """
    db_scalars =  await db.scalars(
        select(CategoryModel).where(CategoryModel.id == category_id, CategoryModel.is_active == True)
    )
    db_category = db_scalars.first()
    if db_category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found or inactive")

    db_scalars = await db.scalars(
        select(ProductModel).where(ProductModel.category_id == category_id, ProductModel.is_active == True)
    )
    db_products = db_scalars.all()

    return db_products

@router.get("/{product_id}", response_model=ProductSchema)
async def get_product(product_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает детальную информацию о товаре по его ID.
    """
    db_scalars = await db.scalars(
        select(ProductModel).where(ProductModel.id == product_id, ProductModel.is_active == True)
    )
    db_product = db_scalars.first()
    if db_product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found or inactive")

    db_scalars = await db.scalars(
        select(CategoryModel).where(CategoryModel.id == db_product.category_id, CategoryModel.is_active == True)
    )
    db_category = db_scalars.first()
    if db_category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found or inactive")
    
    return db_product

@router.put("/{product_id}", response_model=ProductSchema)
async def update_product(
    product_id: int, 
    product: ProductCreate,
    seller: UserModel = Depends(get_current_seller),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Обновляет товар по его ID.
    """
    product_result = await db.scalars(
        select(ProductModel).where(ProductModel.id == product_id, ProductModel.is_active == True)
    )
    db_product = product_result.first()
    if db_product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found or inactive")
    if db_product.seller_id != seller.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only update your own products")

    category_result = await db.scalars(
        select(CategoryModel).where(CategoryModel.id == product.category_id, CategoryModel.is_active == True)
    )
    db_category = category_result.first()
    if db_category is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category not found or inactive")

    for field, value in product.model_dump().items():
        setattr(db_product, field, value)

    await db.commit()
    await db.refresh(db_product)

    return db_product

@router.delete("/{product_id}", response_model=ProductSchema)
async def delete_product(product_id: int, db: AsyncSession = Depends(get_async_db)):
    """
    Логически удаляет продукт по его ID, устанавливая is_active = False.
    """
    db_scalars = await db.scalars(
        select(ProductModel).where(ProductModel.id == product_id, ProductModel.is_active == True)
    )
    db_product = db_scalars.first()
    if db_product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found or inactive")

    db_product.is_active = False
    await db.commit()
    await db.refresh(db_product)

    return db_product