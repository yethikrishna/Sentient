from typing import Dict, List, Any

def _simplify_rich_text(rich_text_array: List[Dict]) -> str:
    """Converts a Notion rich text array to a simple string."""
    return "".join(item.get("plain_text", "") for item in rich_text_array)

def _simplify_block(block: Dict) -> str:
    """Converts a Notion block object to a simplified string representation."""
    block_type = block.get("type")
    if not block_type or not block.get(block_type):
        return ""

    content = block[block_type]
    rich_text = content.get("rich_text")

    if rich_text:
        text = _simplify_rich_text(rich_text)
        if block_type == "heading_1":
            return f"# {text}"
        if block_type == "heading_2":
            return f"## {text}"
        if block_type == "heading_3":
            return f"### {text}"
        if block_type == "bulleted_list_item":
            return f"- {text}"
        if block_type == "numbered_list_item":
            return f"{content.get('number', '1')}. {text}"
        if block_type == "to_do":
            checked = "[x]" if content.get("checked") else "[ ]"
            return f"{checked} {text}"
        if block_type == "quote":
            return f"> {text}"
        if block_type == "code":
            return f"```{content.get('language', '')}\n{text}\n```"
        return text
    return "" # For blocks without rich_text like dividers, images, etc.

def simplify_block_children(response: Dict) -> str:
    """Simplifies a list of blocks from a Notion API response into a single string."""
    simplified_content = []
    for block in response.get("results", []):
        simplified_block = _simplify_block(block)
        if simplified_block:
            simplified_content.append(simplified_block)
    return "\n".join(simplified_content)

def _simplify_property(prop: Dict) -> Any:
    """Simplifies a single Notion database page property."""
    prop_type = prop.get("type")
    if not prop_type or not prop.get(prop_type):
        return None
    
    content = prop[prop_type]
    
    if prop_type == "title":
        return _simplify_rich_text(content)
    if prop_type == "rich_text":
        return _simplify_rich_text(content)
    if prop_type == "number":
        return content
    if prop_type == "select":
        return content.get("name") if content else None
    if prop_type == "multi_select":
        return [item.get("name") for item in content]
    if prop_type == "date":
        return content.get("start")
    if prop_type == "checkbox":
        return content
    if prop_type == "url":
        return content
    if prop_type == "email":
        return content
    # Add other types as needed
    return f"[{prop_type.upper()}]"


def simplify_database_pages(response: Dict) -> List[Dict]:
    """Simplifies a list of pages from a Notion database query response."""
    simplified_pages = []
    for page in response.get("results", []):
        properties = page.get("properties", {})
        simplified_props = {
            name: _simplify_property(prop_data)
            for name, prop_data in properties.items()
        }
        simplified_pages.append({
            "page_id": page.get("id"),
            "properties": simplified_props,
        })
    return simplified_pages