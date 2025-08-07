from typing import Dict, List

def _simplify_document_list_entry(file: Dict) -> Dict:
    """Simplifies a Drive file object for a document list."""
    return {
        "id": file.get("id"),
        "name": file.get("name"),
        "url": file.get("webViewLink")
    }

def _parse_document_content(doc: Dict) -> str:
    """Parses the content of a Google Doc into a simple text string."""
    content_str = ""
    content = doc.get("body", {}).get("content", [])
    for element in content:
        if "paragraph" in element:
            para = element["paragraph"]
            for run in para.get("elements", []):
                if "textRun" in run:
                    content_str += run["textRun"]["content"]
    return content_str