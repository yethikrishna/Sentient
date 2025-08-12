import asyncio
import json
from typing import Dict, Any, List, Optional

from googleapiclient.errors import HttpError
from fastmcp import FastMCP, Context
from fastmcp.utilities.logging import get_logger

from . import auth

logger = get_logger(__name__)

# ---------- helpers ----------

async def _get_service(ctx: Context):
    user_id = auth.get_user_id_from_context(ctx)
    creds = await auth.get_google_creds(user_id)
    return auth.authenticate_gsheets(creds)

async def _safe_call(coro):
    try:
        return {"status": "success", "result": await coro}
    except HttpError as e:
        logger.error(f"Google API Error: {e.content.decode()}", exc_info=True)
        return {"status": "failure", "error": e.content.decode()}
    except Exception as e:
        logger.error(f"Tool execution failed: {e}", exc_info=True)
        return {"status": "failure", "error": str(e)}


# ---------- 19 tools ----------

def register_tools(mcp: FastMCP):

    @mcp.tool()
    async def createSpreadsheet(ctx: Context, title: str) -> Dict[str, Any]:
        """
        Creates a new, empty Google Spreadsheet with a given title.
        """
        logger.info(f"Executing tool: createSpreadsheet with title='{title}'")
        service = await _get_service(ctx)
        return await _safe_call(
            asyncio.to_thread(
                lambda: service.spreadsheets()
                .create(body={"properties": {"title": title}})
                .execute()
            )
        )

    @mcp.tool()
    async def getSpreadsheet(ctx: Context, spreadsheet_id: str) -> Dict[str, Any]:
        """
        Retrieves metadata for a specific spreadsheet, such as its ID, title, and sheet names.
        """
        logger.info(f"Executing tool: getSpreadsheet with spreadsheet_id='{spreadsheet_id}'")
        service = await _get_service(ctx)
        return await _safe_call(
            asyncio.to_thread(
                lambda: service.spreadsheets()
                .get(spreadsheetId=spreadsheet_id)
                .execute()
            )
        )

    @mcp.tool()
    async def listSpreadsheets(ctx: Context) -> Dict[str, Any]:
        """
        Lists all Google Sheets files in the user's Google Drive.
        """
        logger.info("Executing tool: listSpreadsheets")
        from googleapiclient.discovery import build

        service = await _get_service(ctx)
        drive = build("drive", "v3", credentials=service._http.credentials)
        return await _safe_call(
            asyncio.to_thread(
                lambda: drive.files()
                .list(
                    q="mimeType='application/vnd.google-apps.spreadsheet'",
                    fields="files(id,name,webViewLink)",
                )
                .execute()
            )
        )

    @mcp.tool()
    async def deleteSpreadsheet(ctx: Context, spreadsheet_id: str) -> Dict[str, Any]:
        """
        Permanently deletes a spreadsheet file from Google Drive.
        """
        logger.info(f"Executing tool: deleteSpreadsheet with spreadsheet_id='{spreadsheet_id}'")
        from googleapiclient.discovery import build

        service = await _get_service(ctx)
        drive = build("drive", "v3", credentials=service._http.credentials)
        return await _safe_call(
            asyncio.to_thread(lambda: drive.files().delete(fileId=spreadsheet_id).execute())
        )

    # ---- Sheet-level ----

    @mcp.tool()
    async def addSheet(
        ctx: Context, spreadsheet_id: str, sheet_title: str
    ) -> Dict[str, Any]:
        """
        Adds a new sheet (tab) to an existing spreadsheet.
        """
        logger.info(f"Executing tool: addSheet with spreadsheet_id='{spreadsheet_id}', title='{sheet_title}'")
        service = await _get_service(ctx)
        body = {"requests": [{"addSheet": {"properties": {"title": sheet_title}}}]}
        return await _safe_call(
            asyncio.to_thread(
                lambda: service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body=body)
                .execute()
            )
        )

    @mcp.tool()
    async def deleteSheet(ctx: Context, spreadsheet_id: str, sheet_id: int) -> Dict[str, Any]:
        """
        Deletes a sheet (tab) from a spreadsheet, given its `sheet_id`.
        """
        logger.info(f"Executing tool: deleteSheet with spreadsheet_id='{spreadsheet_id}', sheet_id={sheet_id}")
        service = await _get_service(ctx)
        body = {"requests": [{"deleteSheet": {"sheetId": sheet_id}}]}
        return await _safe_call(
            asyncio.to_thread(
                lambda: service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body=body)
                .execute()
            )
        )

    @mcp.tool()
    async def renameSheet(
        ctx: Context, spreadsheet_id: str, sheet_id: int, new_title: str
    ) -> Dict[str, Any]:
        """
        Renames a specific sheet (tab) within a spreadsheet.
        """
        logger.info(f"Executing tool: renameSheet with spreadsheet_id='{spreadsheet_id}', sheet_id={sheet_id}")
        service = await _get_service(ctx)
        body = {
            "requests": [
                {
                    "updateSheetProperties": {
                        "properties": {"sheetId": sheet_id, "title": new_title},
                        "fields": "title",
                    }
                }
            ]
        }
        return await _safe_call(
            asyncio.to_thread(
                lambda: service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body=body)
                .execute()
            )
        )

    # ---- Cell / Range ----

    @mcp.tool()
    async def getValues(
        ctx: Context,
        spreadsheet_id: str,
        range_name: str,
        major_dimension: str = "ROWS",
    ) -> Dict[str, Any]:
        """
        Retrieves cell values from a specified range (e.g., 'Sheet1!A1:B5').
        """
        logger.info(f"Executing tool: getValues for spreadsheet_id='{spreadsheet_id}', range='{range_name}'")
        service = await _get_service(ctx)
        return await _safe_call(
            asyncio.to_thread(
                lambda: service.spreadsheets()
                .values()
                .get(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    majorDimension=major_dimension,
                )
                .execute()
            )
        )

    @mcp.tool()
    async def updateValues(
        ctx: Context,
        spreadsheet_id: str,
        range_name: str,
        values: List[List[str]],
        value_input_option: str = "RAW",
    ) -> Dict[str, Any]:
        """
        Writes new values to a specified cell range (e.g., 'Sheet1!A1:B5').
        """
        logger.info(f"Executing tool: updateValues for spreadsheet_id='{spreadsheet_id}', range='{range_name}'")
        service = await _get_service(ctx)
        body = {"values": values}
        return await _safe_call(
            asyncio.to_thread(
                lambda: service.spreadsheets()
                .values()
                .update(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueInputOption=value_input_option,
                    body=body,
                )
                .execute()
            )
        )

    @mcp.tool()
    async def editCell(
        ctx: Context,
        spreadsheet_id: str,
        cell: str,
        value: str,
    ) -> Dict[str, Any]:
        """
        Writes a single value to a single cell (e.g., 'Sheet1!A1').
        """
        logger.info(f"Executing tool: editCell for spreadsheet_id='{spreadsheet_id}', cell='{cell}'")
        return await updateValues(ctx, spreadsheet_id, cell, [[value]])

    # ---- Row / Column ----

    @mcp.tool()
    async def readRows(
        ctx: Context,
        spreadsheet_id: str,
        sheet_title: str,
        start_row: int = 1,
        end_row: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Reads all data from one or more specified rows.
        """
        logger.info(f"Executing tool: readRows for spreadsheet_id='{spreadsheet_id}', sheet='{sheet_title}'")
        range_name = f"{sheet_title}!{start_row}:{end_row or ''}"
        return await getValues(ctx, spreadsheet_id, range_name)

    @mcp.tool()
    async def readColumns(
        ctx: Context,
        spreadsheet_id: str,
        sheet_title: str,
        start_col: str = "A",
        end_col: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Reads all data from one or more specified columns.
        """
        logger.info(f"Executing tool: readColumns for spreadsheet_id='{spreadsheet_id}', sheet='{sheet_title}'")
        range_name = f"{sheet_title}!{start_col}:{end_col or ''}"
        return await getValues(ctx, spreadsheet_id, range_name)

    @mcp.tool()
    async def readHeadings(
        ctx: Context, spreadsheet_id: str, sheet_title: str
    ) -> Dict[str, Any]:
        """
        Reads only the first row of a sheet, which typically contains the headers.
        """
        logger.info(f"Executing tool: readHeadings for spreadsheet_id='{spreadsheet_id}', sheet='{sheet_title}'")
        return await getValues(ctx, spreadsheet_id, f"{sheet_title}!1:1")

    @mcp.tool()
    async def insertRow(
        ctx: Context,
        spreadsheet_id: str,
        sheet_id: int,
        row_data: List[str],
        row_index: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Inserts a new row with specified data into a sheet.
        """
        logger.info(f"Executing tool: insertRow for spreadsheet_id='{spreadsheet_id}', sheet_id={sheet_id}")
        service = await _get_service(ctx)
        body = {
            "requests": [
                {
                    "insertDimension": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "ROWS",
                            "startIndex": row_index or 0,
                            "endIndex": (row_index or 0) + 1,
                        }
                    }
                }
            ]
        }
        await _safe_call(
            asyncio.to_thread(
                lambda: service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body=body)
                .execute()
            )
        )
        # Now write the data
        if row_index is None:
            # Append at the end
            range_name = f"Sheet1!A:A"
            return await updateValues(
                ctx, spreadsheet_id, range_name, [row_data], value_input_option="RAW"
            )
        else:
            # Write at specific index
            range_name = f"Sheet1!A{row_index + 1}"
            return await updateValues(
                ctx, spreadsheet_id, range_name, [row_data], value_input_option="RAW"
            )

    @mcp.tool()
    async def editRow(
        ctx: Context,
        spreadsheet_id: str,
        sheet_title: str,
        row_index: int,
        values: List[str],
    ) -> Dict[str, Any]:
        """
        Overwrites an entire existing row with new data.
        """
        logger.info(f"Executing tool: editRow for spreadsheet_id='{spreadsheet_id}', sheet='{sheet_title}', row={row_index}")
        range_name = f"{sheet_title}!{row_index}:{row_index}"
        return await updateValues(ctx, spreadsheet_id, range_name, [values])

    @mcp.tool()
    async def insertColumn(
        ctx: Context,
        spreadsheet_id: str,
        sheet_id: int,
        col_index: int,
    ) -> Dict[str, Any]:
        """
        Inserts a new, empty column into a sheet at a specific index.
        """
        logger.info(f"Executing tool: insertColumn for spreadsheet_id='{spreadsheet_id}', sheet_id={sheet_id}")
        service = await _get_service(ctx)
        body = {
            "requests": [
                {
                    "insertDimension": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": col_index,
                            "endIndex": col_index + 1,
                        }
                    }
                }
            ]
        }
        return await _safe_call(
            asyncio.to_thread(
                lambda: service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body=body)
                .execute()
            )
        )

    @mcp.tool()
    async def editColumn(
        ctx: Context,
        spreadsheet_id: str,
        sheet_title: str,
        col_letter: str,
        values: List[str],
    ) -> Dict[str, Any]:
        """
        Overwrites an entire existing column with new data.
        """
        logger.info(f"Executing tool: editColumn for spreadsheet_id='{spreadsheet_id}', sheet='{sheet_title}', col='{col_letter}'")
        range_name = f"{sheet_title}!{col_letter}:{col_letter}"
        return await updateValues(
            ctx, spreadsheet_id, range_name, [[v] for v in values]
        )

    # ---- Sharing ----

    @mcp.tool()
    async def shareSpreadsheet(
        ctx: Context,
        spreadsheet_id: str,
        email: str,
        role: str = "reader",
    ) -> Dict[str, Any]:
        """
        Shares the spreadsheet with a user via their email address, specifying a role ('reader', 'commenter', 'writer').
        """
        logger.info(f"Executing tool: shareSpreadsheet for spreadsheet_id='{spreadsheet_id}' with email='{email}'")
        from googleapiclient.discovery import build

        service = await _get_service(ctx)
        drive = build("drive", "v3", credentials=service._http.credentials)
        body = {"role": role, "type": "user", "emailAddress": email}
        return await _safe_call(
            asyncio.to_thread(
                lambda: drive.permissions()
                .create(fileId=spreadsheet_id, body=body)
                .execute()
            )
        )

    # ---- Formatting ----

    @mcp.tool()
    async def formatCells(
        ctx: Context,
        spreadsheet_id: str,
        sheet_id: int,
        start_row: int,
        end_row: int,
        start_col: int,
        end_col: int,
        background_color: Optional[Dict[str, float]] = None,
        bold: bool = False,
        font_size: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Applies formatting (like bold, font size, background color) to a range of cells.
        """
        logger.info(f"Executing tool: formatCells for spreadsheet_id='{spreadsheet_id}', sheet_id={sheet_id}")
        service = await _get_service(ctx)
        requests = []
        cell_format = {}
        if background_color:
            cell_format["backgroundColor"] = background_color
        if bold:
            cell_format.setdefault("textFormat", {})["bold"] = True
        if font_size:
            cell_format.setdefault("textFormat", {})["fontSize"] = font_size

        requests.append(
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": start_row,
                        "endRowIndex": end_row,
                        "startColumnIndex": start_col,
                        "endColumnIndex": end_col,
                    },
                    "cell": {"userEnteredFormat": cell_format},
                    "fields": ",".join(
                        ["userEnteredFormat." + k for k in cell_format.keys()]
                    ),
                }
            }
        )
        body = {"requests": requests}
        return await _safe_call(
            asyncio.to_thread(
                lambda: service.spreadsheets()
                .batchUpdate(spreadsheetId=spreadsheet_id, body=body)
                .execute()
            )
        )
