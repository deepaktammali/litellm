from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from litellm.proxy._types import (
    LiteLLM_BudgetTable,
    LiteLLM_EndUserTable,
    LitellmUserRoles,
    ProxyException,
)
from litellm.proxy.auth.user_api_key_auth import UserAPIKeyAuth
from litellm.proxy.management_endpoints.customer_endpoints import router

app = FastAPI()


@app.exception_handler(ProxyException)
async def openai_exception_handler(request: Request, exc: ProxyException):
    headers = exc.headers
    error_dict = exc.to_dict()
    return JSONResponse(
        status_code=(
            int(exc.code) if exc.code else status.HTTP_500_INTERNAL_SERVER_ERROR
        ),
        content={"error": error_dict},
        headers=headers,
    )


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
    """
    Test that update_end_user raises a 404 ProxyException when user_id does not exist.
    """
    # Mock the database response to return None (user not found)
    mock_prisma_client.db.litellm_endusertable.find_first = AsyncMock(return_value=None)

    # Test data
    test_data = {"user_id": "non-existent-user", "alias": "Test User"}

    # Make the request
    response = client.post(
        "/customer/update",
        json=test_data,
        headers={"Authorization": "Bearer test-key"},
    )

    # Assert response
    assert response.status_code == 404
    response_json = response.json()
    assert "error" in response_json
    assert response_json["error"]["message"] == "End User Id=non-existent-user does not exist in db"
    assert response_json["error"]["type"] == "not_found"
    assert response_json["error"]["param"] == "user_id"
    assert response_json["error"]["code"] == "404"


def test_info_customer_not_found(mock_prisma_client, mock_user_api_key_auth):
    """
    Test that end_user_info raises a 404 ProxyException when end_user_id does not exist.
    """
    # Mock the database response to return None (user not found)
    mock_prisma_client.db.litellm_endusertable.find_first = AsyncMock(return_value=None)

    # Make the request
    response = client.get(
        "/customer/info?end_user_id=non-existent-user",
        headers={"Authorization": "Bearer test-key"},
    )

    # Assert response
    assert response.status_code == 404
    response_json = response.json()
    assert "error" in response_json
    assert response_json["error"]["message"] == "End User Id=non-existent-user does not exist in db"
    assert response_json["error"]["type"] == "not_found"
    assert response_json["error"]["param"] == "end_user_id"
    assert response_json["error"]["code"] == "404"


def test_delete_customer_not_found(mock_prisma_client, mock_user_api_key_auth):
    """
    Test that delete_end_user raises a 404 ProxyException when user_ids do not exist.
    """
    # Mock the database response to return empty list (no users found)
    mock_prisma_client.db.litellm_endusertable.find_many = AsyncMock(return_value=[])

    # Test data
    test_data = {"user_ids": ["non-existent-user-1", "non-existent-user-2"]}

    # Make the request
    response = client.post(
        "/customer/delete",
        json=test_data,
        headers={"Authorization": "Bearer test-key"},
    )

    # Assert response
    assert response.status_code == 404
    response_json = response.json()
    assert "error" in response_json
    assert "do not exist in db" in response_json["error"]["message"]
    assert "non-existent-user-1" in response_json["error"]["message"]
    assert response_json["error"]["type"] == "not_found"
    assert response_json["error"]["param"] == "user_ids"
    assert response_json["error"]["code"] == "404"


def test_error_schema_consistency(mock_prisma_client, mock_user_api_key_auth):
    """
    Test that all customer endpoints return the same error schema format.
    All ProxyException errors should have: message, type, param, and code fields.
    """
    
    def validate_error_schema(response_json):
        assert "error" in response_json, "Response should have 'error' key"
        error = response_json["error"]
        assert "message" in error, "Error should have 'message' field"
        assert "type" in error, "Error should have 'type' field"
        assert "param" in error, "Error should have 'param' field"
        assert "code" in error, "Error should have 'code' field"
        assert isinstance(error["message"], str), "message should be a string"
        assert isinstance(error["type"], str), "type should be a string"
        assert isinstance(error["code"], str), "code should be a string"
        return error

    # Test /customer/info - not found error
    mock_prisma_client.db.litellm_endusertable.find_first = AsyncMock(return_value=None)
    response = client.get(
        "/customer/info?end_user_id=non-existent",
        headers={"Authorization": "Bearer test-key"},
    )
    error = validate_error_schema(response.json())
    assert error["type"] == "not_found"
    assert error["code"] == "404"

    # Test /customer/update - not found error
    mock_prisma_client.db.litellm_endusertable.find_first = AsyncMock(return_value=None)
    response = client.post(
        "/customer/update",
        json={"user_id": "non-existent", "alias": "Test"},
        headers={"Authorization": "Bearer test-key"},
    )
    error = validate_error_schema(response.json())
    assert error["type"] == "not_found"
    assert error["code"] == "404"

    # Test /customer/delete - not found error
    mock_prisma_client.db.litellm_endusertable.find_many = AsyncMock(return_value=[])
    response = client.post(
        "/customer/delete",
        json={"user_ids": ["non-existent"]},
        headers={"Authorization": "Bearer test-key"},
    )
    error = validate_error_schema(response.json())
    assert error["type"] == "not_found"
    assert error["code"] == "404"

    # Test /customer/new - duplicate user error
    from unittest.mock import MagicMock
    
    mock_end_user = LiteLLM_EndUserTable(
        user_id="existing-user", alias="Existing User", blocked=False
    )
    mock_prisma_client.db.litellm_endusertable.create = AsyncMock(
        side_effect=Exception("Unique constraint failed on the fields: (`user_id`)")
    )
    response = client.post(
        "/customer/new",
        json={"user_id": "existing-user"},
        headers={"Authorization": "Bearer test-key"},
    )
    error = validate_error_schema(response.json())
    assert error["type"] == "bad_request"
    assert error["code"] == "400"


def test_customer_endpoints_error_schema_consistency(mock_prisma_client, mock_user_api_key_auth):
    """
    Test the exact scenarios from the curl examples provided.
    
    Scenario 1: GET /end_user/info with non-existent user
    OLD (incorrect): {"detail":{"error":"End User Id=... does not exist in db"}}
    NEW (correct):   {"error":{"message":"...","type":"not_found","param":"end_user_id","code":"404"}}
    
    Scenario 2: POST /end_user/new with existing user
    Expected:        {"error":{"message":"...","type":"bad_request","param":"user_id","code":"400"}}
    
    Both should use the same error format structure.
    """
    
    # Scenario 1: GET /end_user/info with non-existent user
    # Should return 404 with proper error schema
    mock_prisma_client.db.litellm_endusertable.find_first = AsyncMock(return_value=None)
    
    response1 = client.get(
        "/end_user/info?end_user_id=fake-test-end-user-michaels-local-testng",
        headers={"Authorization": "Bearer test-key"},
    )
    
    assert response1.status_code == 404, "Should return 404 for non-existent user"
    response1_json = response1.json()

    
    # Should have the correct format with {"error": {...}}
    assert "error" in response1_json, "Should have top-level 'error' key"
    error1 = response1_json["error"]
    assert "message" in error1, "Error should have 'message' field"
    assert "type" in error1, "Error should have 'type' field"
    assert "param" in error1, "Error should have 'param' field"
    assert "code" in error1, "Error should have 'code' field"
    assert error1["type"] == "not_found"
    assert error1["code"] == "404"
    assert "does not exist in db" in error1["message"]
    
    # Scenario 2: POST /end_user/new with existing user
    # Should return 400 with proper error schema
    mock_prisma_client.db.litellm_endusertable.create = AsyncMock(
        side_effect=Exception("Unique constraint failed on the fields: (`user_id`)")
    )
    
    response2 = client.post(
        "/end_user/new",
        json={"user_id": "fake-test-end-user-michaels-local-testing", "budget_id": "Tier0"},
        headers={"Authorization": "Bearer test-key"},
    )
    
    assert response2.status_code == 400, "Should return 400 for duplicate user"
    response2_json = response2.json()
    
    # Should have the same error structure as Scenario 1
    assert "error" in response2_json, "Should have top-level 'error' key"
    error2 = response2_json["error"]
    assert "message" in error2, "Error should have 'message' field"
    assert "type" in error2, "Error should have 'type' field"
    assert "param" in error2, "Error should have 'param' field"
    assert "code" in error2, "Error should have 'code' field"
    assert error2["type"] == "bad_request"
    assert error2["code"] == "400"
    assert "Customer already exists" in error2["message"]
    
    # Verify both errors have the same schema structure
    assert set(error1.keys()) == set(error2.keys()), \
        "Both errors should have the same top-level keys"
    
    # Both should have string values for all fields
    for key in ["message", "type", "code"]:
        assert isinstance(error1[key], str), f"error1[{key}] should be a string"
        assert isinstance(error2[key], str), f"error2[{key}] should be a string"


def test_customer_spend_report_success(mock_prisma_client, mock_user_api_key_auth):
    """
    Test the /customer/spend/report endpoint returns spend data with end user aliases.
    """
    from datetime import datetime
    from unittest.mock import MagicMock

    # Mock spend logs data
    mock_spend_log_1 = MagicMock()
    mock_spend_log_1.end_user = "user-1"
    mock_spend_log_1.spend = 10.5
    mock_spend_log_1.total_tokens = 1000
    mock_spend_log_1.prompt_tokens = 600
    mock_spend_log_1.completion_tokens = 400
    mock_spend_log_1.model = "gpt-4"

    mock_spend_log_2 = MagicMock()
    mock_spend_log_2.end_user = "user-1"
    mock_spend_log_2.spend = 5.25
    mock_spend_log_2.total_tokens = 500
    mock_spend_log_2.prompt_tokens = 300
    mock_spend_log_2.completion_tokens = 200
    mock_spend_log_2.model = "gpt-3.5-turbo"

    mock_spend_log_3 = MagicMock()
    mock_spend_log_3.end_user = "user-2"
    mock_spend_log_3.spend = 20.0
    mock_spend_log_3.total_tokens = 2000
    mock_spend_log_3.prompt_tokens = 1200
    mock_spend_log_3.completion_tokens = 800
    mock_spend_log_3.model = "gpt-4"

    # Mock the find_many response for spend logs
    mock_prisma_client.db.litellm_spendlogs.find_many = AsyncMock(
        return_value=[mock_spend_log_1, mock_spend_log_2, mock_spend_log_3]
    )

    # Mock end user data with aliases
    mock_end_user_1 = MagicMock()
    mock_end_user_1.user_id = "user-1"
    mock_end_user_1.alias = "Alice"

    mock_end_user_2 = MagicMock()
    mock_end_user_2.user_id = "user-2"
    mock_end_user_2.alias = "Bob"

    # Mock the find_many response for end users
    mock_prisma_client.db.litellm_endusertable.find_many = AsyncMock(
        return_value=[mock_end_user_1, mock_end_user_2]
    )

    # Make the request
    response = client.get(
        "/customer/spend/report?start_date=2024-01-01&end_date=2024-12-31",
        headers={"Authorization": "Bearer test-key"},
    )

    # Assert response
    assert response.status_code == 200
    response_json = response.json()

    assert "spend_report" in response_json
    assert "total_customers" in response_json
    assert response_json["total_customers"] == 2

    # Check that spend report is sorted by total_spend (descending)
    spend_report = response_json["spend_report"]
    assert len(spend_report) == 2

    # User 2 should be first (higher spend: $20.0)
    assert spend_report[0]["user_id"] == "user-2"
    assert spend_report[0]["alias"] == "Bob"
    assert spend_report[0]["total_spend"] == 20.0
    assert spend_report[0]["total_requests"] == 1
    assert spend_report[0]["total_tokens"] == 2000

    # User 1 should be second (lower spend: $15.75)
    assert spend_report[1]["user_id"] == "user-1"
    assert spend_report[1]["alias"] == "Alice"
    assert spend_report[1]["total_spend"] == 15.75  # 10.5 + 5.25
    assert spend_report[1]["total_requests"] == 2
    assert spend_report[1]["total_tokens"] == 1500  # 1000 + 500

    # Check spend_by_model breakdown for user-1
    assert "spend_by_model" in spend_report[1]
    assert "gpt-4" in spend_report[1]["spend_by_model"]
    assert spend_report[1]["spend_by_model"]["gpt-4"]["spend"] == 10.5
    assert "gpt-3.5-turbo" in spend_report[1]["spend_by_model"]
    assert spend_report[1]["spend_by_model"]["gpt-3.5-turbo"]["spend"] == 5.25


def test_customer_spend_report_admin_only(mock_prisma_client):
    """
    Test that /customer/spend/report endpoint is admin-only.
    """
    # Mock non-admin user
    with patch("litellm.proxy.proxy_server.user_api_key_auth") as mock_auth:
        mock_auth.return_value = UserAPIKeyAuth(
            user_id="test-user", user_role=LitellmUserRoles.INTERNAL_USER
        )

        # Make the request
        response = client.get(
            "/customer/spend/report",
            headers={"Authorization": "Bearer test-key"},
        )

        # Assert response is 401 Unauthorized
        assert response.status_code == 401
        response_json = response.json()
        assert "error" in response_json
        assert "Admin-only endpoint" in response_json["detail"]["error"]
