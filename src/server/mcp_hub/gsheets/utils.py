from typing import Dict, Any, List
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError

def create_spreadsheet_with_data(service: Resource, title: str, sheets_data: List[Dict]) -> Dict:
    """
    Synchronous function to create a Google Sheet, populate it with data, and apply basic formatting.
    """
    try:
        spreadsheet = {
            'properties': {'title': title}
        }
        spreadsheet = service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId,spreadsheetUrl,sheets').execute()
        spreadsheet_id = spreadsheet.get('spreadsheetId')
        
        requests = []
        default_sheet_id = spreadsheet['sheets'][0]['properties']['sheetId']

        for i, sheet_info in enumerate(sheets_data):
            sheet_title = sheet_info['title']
            table = sheet_info['table']
            headers = table['headers']
            rows = table['rows']
            values = [headers] + rows
            num_rows = len(rows) + 1
            num_columns = len(headers)

            if i == 0:
                # Rename the first default sheet
                requests.append({
                    "updateSheetProperties": {
                        "properties": {"sheetId": default_sheet_id, "title": sheet_title},
                        "fields": "title"
                    }
                })
                sheet_id = default_sheet_id
            else:
                # Add a new sheet for subsequent data
                add_sheet_request = {"addSheet": {"properties": {"title": sheet_title}}}
                # We need to execute this separately to get the new sheetId
                response = service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body={'requests': [add_sheet_request]}).execute()
                sheet_id = response['replies'][0]['addSheet']['properties']['sheetId']

            # Prepare data update request
            range_name = f"'{sheet_title}'!A1"
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id, range=range_name,
                valueInputOption="RAW", body={"values": values}
            ).execute()

            # Prepare formatting requests
            requests.extend([
                # Bold headers
                {
                    "repeatCell": {
                        "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": num_columns},
                        "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                        "fields": "userEnteredFormat.textFormat.bold"
                    }
                },
                # Add borders
                {
                    "updateBorders": {
                        "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": num_rows, "startColumnIndex": 0, "endColumnIndex": num_columns},
                        "top": {"style": "SOLID"}, "bottom": {"style": "SOLID"},
                        "left": {"style": "SOLID"}, "right": {"style": "SOLID"},
                        "innerHorizontal": {"style": "SOLID_THIN"}, "innerVertical": {"style": "SOLID_THIN"}
                    }
                }
            ])
        
        if requests:
            service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body={'requests': requests}).execute()

        return {
            "status": "success",
            "result": {
                "message": "Spreadsheet created and populated successfully.",
                "url": spreadsheet.get("spreadsheetUrl")
            }
        }
    except HttpError as e:
        return {"status": "failure", "error": f"Google API Error: {e.content.decode()}"}
    except Exception as e:
        return {"status": "failure", "error": str(e)}