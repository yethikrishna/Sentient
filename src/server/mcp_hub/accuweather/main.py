# server/mcp_hub/accuweather/main.py

import os
from typing import Dict, Any
from dotenv import load_dotenv

# Conditionally load .env for local development
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)

from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
from fastmcp.prompts.prompt import Message

from . import auth, prompts, utils

mcp = FastMCP(
    name="AccuWeatherServer",
    instructions="A server for getting weather information from AccuWeather.",
)

# --- Prompt Registration ---
@mcp.resource("prompt://weather-agent-system")
def get_weather_system_prompt() -> str:
    return prompts.weather_agent_system_prompt

@mcp.prompt(name="weather_user_prompt_builder")
def build_weather_user_prompt(query: str, username: str, previous_tool_response: str = "{}") -> Message:
    content = prompts.weather_agent_user_prompt.format(
        query=query, username=username, previous_tool_response=previous_tool_response
    )
    return Message(role="user", content=content)

# --- Tool Definitions ---

@mcp.tool
async def getCurrentWeather(ctx: Context, location: str) -> Dict[str, Any]:
    """Get current weather conditions for a specific location."""
    try:
        api_key = auth.get_accuweather_api_key()
        location_details = await utils.get_location_details(location, api_key)
        conditions = await utils.fetch_current_conditions(location_details["key"], api_key)
        
        return {
            "status": "success",
            "result": {
                "location": f"{location_details['name']}, {location_details['region']}, {location_details['country']}",
                "observation_time": conditions.get("LocalObservationDateTime"),
                "weather": conditions.get("WeatherText"),
                "temperature": conditions.get("Temperature", {}).get("Metric"),
                "real_feel_temperature": conditions.get("RealFeelTemperature", {}).get("Metric"),
                "relative_humidity": conditions.get("RelativeHumidity"),
                "wind": conditions.get("Wind", {}).get("Speed", {}).get("Metric"),
                "uv_index": f"{conditions.get('UVIndex')} {conditions.get('UVIndexText')}",
            }
        }
    except Exception as e:
        return {"status": "failure", "error": str(e)}

@mcp.tool
async def getForecast(ctx: Context, location: str, days: int = 1) -> Dict[str, Any]:
    """Get the daily weather forecast for a location for the next 1-5 days."""
    try:
        if not 1 <= days <= 5:
            raise ToolError("Forecast can only be retrieved for 1 to 5 days.")
        
        api_key = auth.get_accuweather_api_key()
        location_details = await utils.get_location_details(location, api_key)
        forecast_data = await utils.fetch_daily_forecast(location_details["key"], api_key)

        daily_forecasts = []
        for day_forecast in forecast_data.get("DailyForecasts", [])[:days]:
            daily_forecasts.append({
                "date": day_forecast.get("Date"),
                "temperature_min": day_forecast.get("Temperature", {}).get("Minimum"),
                "temperature_max": day_forecast.get("Temperature", {}).get("Maximum"),
                "day": {
                    "condition": day_forecast.get("Day", {}).get("IconPhrase"),
                    "has_precipitation": day_forecast.get("Day", {}).get("HasPrecipitation"),
                },
                "night": {
                    "condition": day_forecast.get("Night", {}).get("IconPhrase"),
                    "has_precipitation": day_forecast.get("Night", {}).get("HasPrecipitation"),
                }
            })

        return {
            "status": "success",
            "result": {
                "location": f"{location_details['name']}, {location_details['country']}",
                "headline": forecast_data.get("Headline", {}).get("Text"),
                "forecasts": daily_forecasts,
            }
        }
    except Exception as e:
        return {"status": "failure", "error": str(e)}

# --- Server Execution ---
if __name__ == "__main__":
    host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_SERVER_PORT", 9007))
    
    print(f"Starting AccuWeather MCP Server on http://{host}:{port}")
    mcp.run(transport="sse", host=host, port=port)