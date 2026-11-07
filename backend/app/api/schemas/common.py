"""
Shared Pydantic Schemas for API responses and errors.
"""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error classification")
    detail: str = Field(..., description="Human-readable error details")
    customer_id: Optional[str] = Field(default=None, description="Customer ID associated with request if applicable")

    model_config = ConfigDict(extra="ignore")


class HealthResponse(BaseModel):
    status: str = Field(..., description="Service status (e.g. 'healthy')")
    app_version: str = Field(..., description="Application version")
    database_connected: bool = Field(..., description="True if database connection is verified")
    ml_model_loaded: bool = Field(..., description="True if ML propensity model is loaded")
    ml_model_name: Optional[str] = Field(default=None, description="Name of loaded ML model artifact")

    model_config = ConfigDict(extra="ignore")
