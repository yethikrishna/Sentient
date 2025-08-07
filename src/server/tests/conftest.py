import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
from main.app import app
from main.dependencies import mongo_manager, auth_helper
from main.auth.utils import PermissionChecker

# --- Test User Data ---
TEST_USER_ID = "test-user-123"
TEST_USER_PERMISSIONS = [
    "read:chat", "write:chat", "read:tasks", "write:tasks",
    "read:notifications", "write:notifications", "read:config", "write:config",
    "read:profile", "write:profile"
]

# --- Fixtures ---

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
def mock_mongo_manager(mocker):
    """Mocks the global mongo_manager instance."""
    mock = AsyncMock()
    mock.get_user_profile = AsyncMock(return_value={"user_id": TEST_USER_ID, "userData": {}})
    mock.update_user_profile = AsyncMock(return_value=True)
    mock.add_message = AsyncMock(return_value={"message_id": "new-msg-id"})
    mock.get_message_history = AsyncMock(return_value=[])
    mock.delete_message = AsyncMock(return_value=True)
    mock.delete_all_messages = AsyncMock(return_value=5)
    mock.add_task = AsyncMock(return_value="new-task-id")
    mock.get_task = AsyncMock(return_value={"task_id": "some-task-id", "user_id": TEST_USER_ID, "runs": [{"run_id": "run-1"}]})
    mock.get_all_tasks_for_user = AsyncMock(return_value=[])
    mock.update_task = AsyncMock(return_value=True)
    mock.delete_task = AsyncMock(return_value="Task deleted successfully.")
    
    mocker.patch('main.dependencies.mongo_manager', new=mock)
    mocker.patch('workers.tasks.mongo_manager', new=mock) # Also patch in workers
    mocker.patch('workers.planner.db.PlannerMongoManager', return_value=mock)
    return mock

@pytest.fixture(scope="function")
def client(mock_mongo_manager):
    """Provides a TestClient for the FastAPI app with mocked auth."""
    
    async def override_get_current_user_id():
        return TEST_USER_ID

    async def override_permission_checker():
        return TEST_USER_ID

    # Override dependencies
    app.dependency_overrides[auth_helper.get_current_user_id] = override_get_current_user_id
    # Since PermissionChecker is a class, we need to be careful.
    # This approach overrides any instance of it.
    app.dependency_overrides[PermissionChecker] = override_permission_checker

    with TestClient(app) as test_client:
        yield test_client

    # Clean up overrides after test
    app.dependency_overrides = {}