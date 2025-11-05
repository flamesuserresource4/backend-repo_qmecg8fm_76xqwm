"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional

# Example schemas (replace with your own):

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# Add your own schemas here:
# --------------------------------------------------

class ModelFile(BaseModel):
    """
    Model files uploaded via Admin Panel
    Collection name: "modelfile"
    """
    name: str = Field(..., description="Original filename of the uploaded model archive")
    size: int = Field(..., ge=0, description="Size in bytes")
    content_type: str = Field(..., description="MIME type, e.g. application/zip")
    data_b64: str = Field(..., description="Base64-encoded file content of the model .zip")
    active: bool = Field(True, description="Whether this model is currently active")

class ModelConfig(BaseModel):
    """
    Configuration for active inference source
    Collection name: "modelconfig"
    """
    source_type: str = Field(..., description="'url' or 'db' to indicate model source")
    url: Optional[HttpUrl] = Field(None, description="Public URL of Teachable Machine model.json")
    active: bool = Field(True, description="Whether this config is active")
