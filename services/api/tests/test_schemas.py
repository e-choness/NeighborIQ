"""Response schemas validate straight from ORM objects (Pydantic v2 from_attributes)."""

from datetime import UTC, datetime

from app.schemas import CommunityResponse, HouseResponse, UserResponse
from shared.models.auth_models import User, UserRoleEnum
from shared.models.house_models import Community, House


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
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    # This should work with from_attributes=True
    response = UserResponse.model_validate(user)

    assert response.id == 1
    assert response.email == "test@example.com"
    assert response.name == "Test User"
    assert response.role == "user"
    assert response.created_at is not None


def test_house_response_from_orm():
    """Test HouseResponse.model_validate works with ORM House object."""
    # Create a mock ORM House object
    house = House(
        id=1,
        title="Beautiful House",
        community="Test Community",
        city="Toronto",
        region="Old Toronto",
        street="Main Street",
        price=5000000,
        area=100.5,
        rooms=3,
        floor=5,
        decoration="renovated",
        age=5,
        latitude=43.6532,
        longitude=-79.3832,
        url="http://example.com",
        images='["image1.jpg", "image2.jpg"]',
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    # This should work with from_attributes=True
    response = HouseResponse.model_validate(house)

    assert response.id == 1
    assert response.title == "Beautiful House"
    assert response.city == "Toronto"
    assert response.images == ["image1.jpg", "image2.jpg"]
    assert response.is_synthetic is False
    assert response.created_at is not None


def test_community_response_from_orm():
    """Test CommunityResponse.model_validate works with ORM Community object."""
    # Create a mock ORM Community object
    community = Community(
        id=1,
        name="Test Community",
        city="Toronto",
        region="Old Toronto",
        street="Main Street",
        latitude=43.6532,
        longitude=-79.3832,
        house_count=100,
        avg_price=5000000.0,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    # This should work with from_attributes=True
    response = CommunityResponse.model_validate(community)

    assert response.id == 1
    assert response.name == "Test Community"
    assert response.city == "Toronto"
    assert response.house_count == 100
