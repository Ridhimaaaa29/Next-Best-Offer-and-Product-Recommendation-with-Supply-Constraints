"""
Product Pydantic Schemas.
"""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class ProductBase(BaseModel):
    product_id: str = Field(..., description="Unique product ID")
    product_name: str = Field(..., description="Product name")
    category: str = Field(..., description="Category")
    subcategory: Optional[str] = Field(None, description="Subcategory")
    brand: Optional[str] = Field(None, description="Brand")
    unit_price: float = Field(..., description="Unit price in USD")
    product_rating: Optional[float] = Field(None, description="Average review rating")
    product_popularity: Optional[float] = Field(None, description="Product popularity score")
    product_status: str = Field(default="active", description="Lifecycle status")

    model_config = ConfigDict(extra="ignore")


class ProductOperationalDetail(ProductBase):
    available_stock: Optional[int] = Field(None, description="Current stock available")
    inventory_status: Optional[str] = Field(None, description="Stock status")
    gross_margin_pct: Optional[float] = Field(None, description="Gross profit margin percentage")
    shipping_days: Optional[int] = Field(None, description="Fulfillment lead time in days")
    reward_eligible: Optional[bool] = Field(None, description="Reward program eligibility")
    promotion_eligible: Optional[bool] = Field(None, description="Promotion eligibility")
