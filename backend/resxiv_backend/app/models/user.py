"""
User Pydantic Models

Request/response models for user-related API endpoints.
These are separate from SQLAlchemy schemas and used for API validation.
"""

from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


class UserRegistration(BaseModel):
    """Model for user registration requests"""
    name: str = Field(..., min_length=1, max_length=255, description="User's full name")
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., min_length=8, description="User's password")
    username: Optional[str] = Field(None, description="Optional username")
    interests: Optional[List[str]] = Field(default=[], description="Research interests")
    accepted_terms: bool = Field(..., description="Whether user accepted terms and conditions")


class UserLogin(BaseModel):
    """Model for user login requests"""
    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")


class TokenResponse(BaseModel):
    """Model for authentication token responses"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class UserResponse(BaseModel):
    """Model for user profile responses"""
    id: uuid.UUID = Field(..., description="User ID")
    name: str = Field(..., description="User's full name")
    email: str = Field(..., description="User's email address")
    email_verified: bool = Field(..., description="Whether email is verified")
    interests: List[str] = Field(default=[], description="Research interests")
    intro: str = Field(default="Fill in your information", description="User introduction")
    created_at: datetime = Field(..., description="Account creation timestamp")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    
    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    """Model for user profile update requests"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="User's full name")
    email: Optional[EmailStr] = Field(None, description="User's email address")
    interests: Optional[List[str]] = Field(None, description="Research interests")
    intro: Optional[str] = Field(None, description="User introduction")


class PasswordChangeRequest(BaseModel):
    """Model for password change requests"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")


class PasswordResetRequest(BaseModel):
    """Model for password reset requests"""
    email: EmailStr = Field(..., description="Email address for password reset")


class PasswordResetConfirm(BaseModel):
    """Model for password reset confirmation"""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, description="New password")


class RefreshTokenRequest(BaseModel):
    """Model for refresh token requests"""
    refresh_token: str = Field(..., description="Refresh token")


class UserPublicProfile(BaseModel):
    """Model for public user profile responses"""
    id: uuid.UUID = Field(..., description="User ID")
    name: str = Field(..., description="User's full name")
    interests: List[str] = Field(default=[], description="Research interests")
    intro: str = Field(default="Fill in your information", description="User introduction")
    created_at: datetime = Field(..., description="Account creation timestamp")
    
    class Config:
        from_attributes = True 