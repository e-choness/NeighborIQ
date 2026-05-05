#!/usr/bin/env python3
"""
Test script to verify Pydantic V2 ConfigDict configuration works correctly.
Tests that the from_attributes=True setting allows model_validate to work with ORM objects.
"""

import sys
sys.path.insert(0, '/app')

from datetime import datetime, timezone
from shared.models.schemas import UserResponse, HouseResponse, CommunityResponse
from shared.models.auth_models import User, UserRoleEnum
from shared.models.house_models import House, Community


def test_user_response_from_orm():
    """Test UserResponse.model_validate works with ORM User object."""
    # Create a mock ORM User object
    user = User(
        id=1,
        email="test@example.com",
        name="Test User",
        password_hash="hashed_password",
        role=UserRoleEnum.USER,
        is_active=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    
    # This should work with from_attributes=True
    response = UserResponse.model_validate(user)
    
    assert response.id == 1
    assert response.email == "test@example.com"
    assert response.name == "Test User"
    assert response.role == "user"
    assert response.created_at is not None
    print("✓ UserResponse.model_validate works correctly with ORM objects")


def test_house_response_from_orm():
    """Test HouseResponse.model_validate works with ORM House object."""
    # Create a mock ORM House object
    house = House(
        id=1,
        title="Beautiful House",
        community="Test Community",
        city="Shanghai",
        region="Pudong",
        street="Main Street",
        price=5000000,
        area=100.5,
        rooms=3,
        floor=5,
        decoration="精装",
        age=5,
        latitude=31.2304,
        longitude=121.4737,
        url="http://example.com",
        images='["image1.jpg", "image2.jpg"]',
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    
    # This should work with from_attributes=True
    response = HouseResponse.model_validate(house)
    
    assert response.id == 1
    assert response.title == "Beautiful House"
    assert response.city == "Shanghai"
    assert response.created_at is not None
    print("✓ HouseResponse.model_validate works correctly with ORM objects")


def test_community_response_from_orm():
    """Test CommunityResponse.model_validate works with ORM Community object."""
    # Create a mock ORM Community object
    community = Community(
        id=1,
        name="Test Community",
        city="Shanghai",
        region="Pudong",
        street="Main Street",
        latitude=31.2304,
        longitude=121.4737,
        house_count=100,
        avg_price=5000000.0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    
    # This should work with from_attributes=True
    response = CommunityResponse.model_validate(community)
    
    assert response.id == 1
    assert response.name == "Test Community"
    assert response.city == "Shanghai"
    assert response.house_count == 100
    print("✓ CommunityResponse.model_validate works correctly with ORM objects")


if __name__ == "__main__":
    print("Testing Pydantic V2 ConfigDict configuration...\n")
    try:
        test_user_response_from_orm()
        test_house_response_from_orm()
        test_community_response_from_orm()
        print("\n✅ All Pydantic V2 ConfigDict tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
