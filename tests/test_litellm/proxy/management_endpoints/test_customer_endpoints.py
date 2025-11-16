from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from litellm.proxy._types import (
    LiteLLM_BudgetTable,
    LiteLLM_EndUserTable,
    LitellmUserRoles,
)
from litellm.proxy.auth.user_api_key_auth import UserAPIKeyAuth
from litellm.proxy.management_endpoints.customer_endpoints import router
from litellm.proxy.proxy_server import ProxyException

app = FastAPI()
app.include_router(router)
client = TestClient(app)


@pytest.fixture
def mock_prisma_client():
    with patch("litellm.proxy.proxy_server.prisma_client") as mock:
        yield mock


@pytest.fixture
def mock_user_api_key_auth():
    with patch("litellm.proxy.proxy_server.user_api_key_auth") as mock:
        mock.return_value = UserAPIKeyAuth(
            user_id="test-user", user_role=LitellmUserRoles.PROXY_ADMIN
        )
        yield mock


def test_update_customer_success(mock_prisma_client, mock_user_api_key_auth):
    # Mock the database responses
    mock_end_user = LiteLLM_EndUserTable(
        user_id="test-user-1", alias="Test User", blocked=False
    )
    updated_mock_end_user = LiteLLM_EndUserTable(
        user_id="test-user-1", alias="Updated Test User", blocked=False
    )

    # Mock the find_first response
    mock_prisma_client.db.litellm_endusertable.find_first = AsyncMock(
        return_value=mock_end_user
    )

    # Mock the update response
    mock_prisma_client.db.litellm_endusertable.update = AsyncMock(
        return_value=updated_mock_end_user
    )

    # Test data
    test_data = {"user_id": "test-user-1", "alias": "Updated Test User"}

    # Make the request
    response = client.post(
        "/customer/update", json=test_data, headers={"Authorization": "Bearer test-key"}
    )

    # Assert response
    assert response.status_code == 200
    assert response.json()["user_id"] == "test-user-1"
    assert response.json()["alias"] == "Updated Test User"


def test_update_customer_not_found(mock_prisma_client, mock_user_api_key_auth):
    # Mock the database response to return None (user not found)
    mock_prisma_client.db.litellm_endusertable.find_first = AsyncMock(return_value=None)

    # Test data
    test_data = {"user_id": "non-existent-user", "alias": "Test User"}

    # Make the request
    try:
        response = client.post(
            "/customer/update",
            json=test_data,
            headers={"Authorization": "Bearer test-key"},
        )
    except Exception as e:
        print(e, type(e))
        assert isinstance(e, ProxyException)
        assert int(e.code) == 400
        assert "End User Id=non-existent-user does not exist in db" in e.message


def test_get_customer_spend_list_success(mock_prisma_client, mock_user_api_key_auth):
    """Test GET /customer/spend - list all customers with pagination"""
    # Mock count query response
    mock_prisma_client.db.query_raw = AsyncMock(
        side_effect=[
            # Count query response
            [{"total": 2}],
            # Spend report query response
            [
                {
                    "end_user_id": "user-1",
                    "alias": "Alice",
                    "total_spend": 150.50,
                    "total_requests": 100,
                    "total_tokens": 5000,
                    "total_prompt_tokens": 3000,
                    "total_completion_tokens": 2000,
                },
                {
                    "end_user_id": "user-2",
                    "alias": None,
                    "total_spend": 50.25,
                    "total_requests": 30,
                    "total_tokens": 1500,
                    "total_prompt_tokens": 900,
                    "total_completion_tokens": 600,
                },
            ],
        ]
    )

    # Make the request
    response = client.get(
        "/customer/spend?page=1&page_size=50",
        headers={"Authorization": "Bearer test-key"},
    )

    # Assert response
    assert response.status_code == 200
    data = response.json()
    assert data["total_customers"] == 2
    assert data["page"] == 1
    assert data["page_size"] == 50
    assert data["total_pages"] == 1
    assert len(data["spend_report"]) == 2

    # Check first user
    assert data["spend_report"][0]["end_user_id"] == "user-1"
    assert data["spend_report"][0]["alias"] == "Alice"
    assert data["spend_report"][0]["total_spend"] == 150.50
    assert data["spend_report"][0]["total_requests"] == 100

    # Check second user (with null alias)
    assert data["spend_report"][1]["end_user_id"] == "user-2"
    assert data["spend_report"][1]["alias"] is None
    assert data["spend_report"][1]["total_spend"] == 50.25


def test_get_customer_spend_list_with_date_filter(
    mock_prisma_client, mock_user_api_key_auth
):
    """Test GET /customer/spend with date range filter"""
    mock_prisma_client.db.query_raw = AsyncMock(
        side_effect=[
            [{"total": 1}],
            [
                {
                    "end_user_id": "user-1",
                    "alias": "Alice",
                    "total_spend": 100.0,
                    "total_requests": 50,
                    "total_tokens": 2500,
                    "total_prompt_tokens": 1500,
                    "total_completion_tokens": 1000,
                }
            ],
        ]
    )

    response = client.get(
        "/customer/spend?start_date=2024-01-01&end_date=2024-01-31&page=1&page_size=50",
        headers={"Authorization": "Bearer test-key"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["date_range"]["start_date"] == "2024-01-01"
    assert data["date_range"]["end_date"] == "2024-01-31"
    assert len(data["spend_report"]) == 1


def test_get_customer_spend_list_empty(mock_prisma_client, mock_user_api_key_auth):
    """Test GET /customer/spend with no customers"""
    mock_prisma_client.db.query_raw = AsyncMock(
        side_effect=[
            [{"total": 0}],
            [],
        ]
    )

    response = client.get(
        "/customer/spend?page=1&page_size=50",
        headers={"Authorization": "Bearer test-key"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_customers"] == 0
    assert data["total_pages"] == 0
    assert len(data["spend_report"]) == 0


def test_get_customer_spend_detail_success(mock_prisma_client, mock_user_api_key_auth):
    """Test GET /customer/{end_user_id}/spend - detail with model breakdown"""
    # Mock end user exists
    mock_end_user = LiteLLM_EndUserTable(
        user_id="user-123", alias="Test User", blocked=False
    )
    mock_prisma_client.db.litellm_endusertable.find_unique = AsyncMock(
        return_value=mock_end_user
    )

    # Mock group_by responses
    mock_prisma_client.db.litellm_spendlogs.group_by = AsyncMock(
        side_effect=[
            # Total aggregation
            [
                {
                    "end_user": "user-123",
                    "_sum": {
                        "spend": 200.75,
                        "total_tokens": 10000,
                        "prompt_tokens": 6000,
                        "completion_tokens": 4000,
                    },
                    "_count": {"_all": 150},
                }
            ],
            # Model breakdown
            [
                {
                    "model": "gpt-4",
                    "_sum": {
                        "spend": 150.50,
                        "total_tokens": 7000,
                        "prompt_tokens": 4200,
                        "completion_tokens": 2800,
                    },
                    "_count": {"_all": 100},
                },
                {
                    "model": "gpt-3.5-turbo",
                    "_sum": {
                        "spend": 50.25,
                        "total_tokens": 3000,
                        "prompt_tokens": 1800,
                        "completion_tokens": 1200,
                    },
                    "_count": {"_all": 50},
                },
            ],
        ]
    )

    # Make the request
    response = client.get(
        "/customer/user-123/spend",
        headers={"Authorization": "Bearer test-key"},
    )

    # Assert response
    assert response.status_code == 200
    data = response.json()
    assert data["end_user_id"] == "user-123"
    assert data["alias"] == "Test User"
    assert data["total_spend"] == 200.75
    assert data["total_requests"] == 150
    assert data["total_tokens"] == 10000
    assert data["total_prompt_tokens"] == 6000
    assert data["total_completion_tokens"] == 4000

    # Check model breakdown
    assert len(data["spend_by_model"]) == 2
    assert data["spend_by_model"][0]["model"] == "gpt-4"
    assert data["spend_by_model"][0]["total_spend"] == 150.50
    assert data["spend_by_model"][1]["model"] == "gpt-3.5-turbo"
    assert data["spend_by_model"][1]["total_spend"] == 50.25


def test_get_customer_spend_detail_not_found(
    mock_prisma_client, mock_user_api_key_auth
):
    """Test GET /customer/{end_user_id}/spend - user not found"""
    # Mock end user does not exist
    mock_prisma_client.db.litellm_endusertable.find_unique = AsyncMock(
        return_value=None
    )

    # Make the request
    response = client.get(
        "/customer/non-existent-user/spend",
        headers={"Authorization": "Bearer test-key"},
    )

    # Assert 404 response
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]["error"]


def test_get_customer_spend_detail_no_spend(
    mock_prisma_client, mock_user_api_key_auth
):
    """Test GET /customer/{end_user_id}/spend - user exists but has no spend"""
    # Mock end user exists
    mock_end_user = LiteLLM_EndUserTable(
        user_id="user-new", alias="New User", blocked=False
    )
    mock_prisma_client.db.litellm_endusertable.find_unique = AsyncMock(
        return_value=mock_end_user
    )

    # Mock empty aggregations
    mock_prisma_client.db.litellm_spendlogs.group_by = AsyncMock(
        side_effect=[
            [],  # Empty total aggregation
            [],  # Empty model breakdown
        ]
    )

    # Make the request
    response = client.get(
        "/customer/user-new/spend",
        headers={"Authorization": "Bearer test-key"},
    )

    # Assert response with zero spend
    assert response.status_code == 200
    data = response.json()
    assert data["end_user_id"] == "user-new"
    assert data["alias"] == "New User"
    assert data["total_spend"] == 0.0
    assert data["total_requests"] == 0
    assert data["total_tokens"] == 0
    assert len(data["spend_by_model"]) == 0
