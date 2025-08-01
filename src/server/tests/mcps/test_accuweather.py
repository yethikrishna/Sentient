import pytest
from unittest.mock import AsyncMock, MagicMock
from fastmcp.testing import TestClient
from mcp_hub.accuweather.main import mcp

# --- Fixtures ---

@pytest.fixture
def mock_auth(mocker):
    """Mocks the authentication functions for the AccuWeather MCP."""
    mocker.patch('mcp_hub.accuweather.auth.get_accuweather_api_key', return_value="fake-api-key")

@pytest.fixture
def mock_httpx(mocker):
    """Mocks the httpx client used for external API calls."""
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    
    # Default responses
    mock_response.json.return_value = [{
        "Key": "12345", "LocalizedName": "Test City", 
        "Country": {"LocalizedName": "TC"}, "AdministrativeArea": {"LocalizedName": "TS"}
    }]

    mock_async_client = AsyncMock()
    mock_async_client.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
    
    mocker.patch('httpx.AsyncClient', return_value=mock_async_client)
    return mock_async_client, mock_response

# --- Tests ---

@pytest.mark.asyncio
async def test_get_current_weather_success(mock_auth, mock_httpx):
    mock_client, mock_response = mock_httpx
    
    # Set a specific response for the current conditions call
    mock_response.json.side_effect = [
        # First call (location search)
        [{"Key": "12345", "LocalizedName": "Test City", "Country": {"LocalizedName": "TC"}, "AdministrativeArea": {"LocalizedName": "TS"}}],
        # Second call (current conditions)
        [{
            "WeatherText": "Sunny", "Temperature": {"Metric": {"Value": 25.0}},
            "RealFeelTemperature": {"Metric": {"Value": 26.0}}, "RelativeHumidity": 50,
            "Wind": {"Speed": {"Metric": {"Value": 10.0}}}, "UVIndex": 5, "UVIndexText": "Moderate"
        }]
    ]

    async with TestClient(mcp) as client:
        response = await client.tool(
            "getCurrentWeather",
            {"location": "Test City"},
            headers={"X-User-ID": "test-user"}
        )
    
    assert response["status"] == "success"
    result = response["result"]
    assert result["location"] == "Test City, TS, TC"
    assert result["weather"] == "Sunny"
    assert result["temperature"]["Value"] == 25.0

@pytest.mark.asyncio
async def test_get_forecast_invalid_days(mock_auth):
    async with TestClient(mcp) as client:
        response = await client.tool(
            "getForecast",
            {"location": "Test City", "days": 10}, # Invalid number of days
            headers={"X-User-ID": "test-user"}
        )
    
    assert response["status"] == "failure"
    assert "Forecast can only be retrieved for 1 to 5 days" in response["error"]

@pytest.mark.asyncio
async def test_location_not_found(mock_auth, mock_httpx):
    mock_client, mock_response = mock_httpx
    mock_response.json.return_value = [] # Simulate no locations found

    async with TestClient(mcp) as client:
        response = await client.tool(
            "getCurrentWeather",
            {"location": "Nonexistent Place"},
            headers={"X-User-ID": "test-user"}
        )
        
    assert response["status"] == "failure"
    assert "Location 'Nonexistent Place' not found" in response["error"]