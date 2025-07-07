# server/mcp_hub/quickchart/utils.py

import json
from urllib.parse import quote
from typing import Dict, Any, Optional
import os
import httpx
from datetime import datetime

QUICKCHART_BASE_URL = "https://quickchart.io/chart"
VALID_CHART_TYPES = [
    'bar', 'line', 'pie', 'doughnut', 'radar', 'polarArea', 
    'scatter', 'bubble', 'radialGauge', 'speedometer'
]

def _validate_chart_config(config: Dict[str, Any]):
    """Validates the basic structure of the chart configuration."""
    if 'type' not in config or config['type'] not in VALID_CHART_TYPES:
        raise ValueError(f"Invalid or missing chart type. Must be one of: {', '.join(VALID_CHART_TYPES)}")
    if 'data' not in config or 'datasets' not in config['data']:
        raise ValueError("Config must include 'data' with a 'datasets' list.")
    if not isinstance(config['data']['datasets'], list) or not config['data']['datasets']:
        raise ValueError("'datasets' must be a non-empty list.")

def generate_chart_url(chart_config: Dict[str, Any]) -> str:
    """
    Generates a QuickChart.io URL from a chart configuration dictionary.

    Args:
        chart_config: A dictionary representing the Chart.js configuration.

    Returns:
        A URL string pointing to the generated chart image.
    """
    _validate_chart_config(chart_config)
    
    # URL-encode the JSON string of the configuration
    encoded_config = quote(json.dumps(chart_config))
    return f"{QUICKCHART_BASE_URL}?c={encoded_config}"

def get_default_save_path(chart_type: str) -> str:
    """Determines a default save path for the chart image."""
    home_dir = os.path.expanduser("~")
    desktop_dir = os.path.join(home_dir, "Desktop")
    
    # Prefer Desktop if it exists and is writable, otherwise use home directory
    base_dir = desktop_dir if os.path.isdir(desktop_dir) and os.access(desktop_dir, os.W_OK) else home_dir
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{chart_type}_{timestamp}.png"
    
    return os.path.join(base_dir, filename)

async def download_chart_image(chart_url: str, output_path: Optional[str] = None) -> str:
    """
    Downloads a chart image from a URL and saves it to a local file.

    Args:
        chart_url: The URL of the chart image.
        output_path: The local file path to save the image. A default is used if None.

    Returns:
        The final path where the image was saved.
    """
    # Extract chart type from URL for default filename, fallback to 'chart'
    try:
        config_str = chart_url.split('?c=')[1]
        config = json.loads(config_str)
        chart_type = config.get('type', 'chart')
    except (IndexError, json.JSONDecodeError):
        chart_type = 'chart'
        
    final_path = output_path or get_default_save_path(chart_type)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(chart_url)
            response.raise_for_status()
            
            with open(final_path, "wb") as f:
                f.write(response.content)
                
            return final_path
        except httpx.HTTPStatusError as e:
            raise Exception(f"Failed to fetch chart image: {e.response.status_code}")
        except IOError as e:
            raise Exception(f"Failed to save chart image to {final_path}: {e}")