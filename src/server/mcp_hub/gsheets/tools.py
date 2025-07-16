import asyncio
import json
from typing import Dict, Any, List, Optional

from googleapiclient.errors import HttpError
from fastmcp import FastMCP, Context

from . import auth

# ---------- helpers ----------

async def _get_service(ctx: Context):
    user_id = auth.get_user_id_from_context(ctx)
    creds = await auth.get_google_creds(user_id)
    return auth.authenticate_gsheets(creds)

async def _safe_call(coro):
    try:
        return {"status": "success", "result": await coro}
    except HttpError as e:
        return {"status": "failure", "error": e.content.decode()}
    except Exception as e:
        return {"status": "failure", "error": str(e)}


# ---------- 19 tools ----------

def register_tools(mcp: FastMCP):

    @mcp.tool()
    async def createSpreadsheet(ctx: Context, title: str) -> Dict[str, Any]:
        """Create a new Google spreadsheet."""
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
        """Return metadata about a spreadsheet."""
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
        """List all spreadsheets visible to the authenticated user."""
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
        """Delete a Google spreadsheet."""
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
        """Add a new sheet to an existing spreadsheet."""
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
        """Delete a sheet from a spreadsheet."""
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
        """Rename a sheet."""
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
        """Get values from a range."""
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
        """Update values in a range."""
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
        """Edit a single cell."""
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
        """Read specific rows from a sheet."""
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
        """Read specific columns from a sheet."""
        range_name = f"{sheet_title}!{start_col}:{end_col or ''}"
        return await getValues(ctx, spreadsheet_id, range_name)

    @mcp.tool()
    async def readHeadings(
        ctx: Context, spreadsheet_id: str, sheet_title: str
    ) -> Dict[str, Any]:
        """Read the header row (first row)."""
        return await getValues(ctx, spreadsheet_id, f"{sheet_title}!1:1")

    @mcp.tool()
    async def insertRow(
        ctx: Context,
        spreadsheet_id: str,
        sheet_id: int,
        row_data: List[str],
        row_index: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Insert a new row into a sheet."""
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
        """Edit an entire row."""
        range_name = f"{sheet_title}!{row_index}:{row_index}"
        return await updateValues(ctx, spreadsheet_id, range_name, [values])

    @mcp.tool()
    async def insertColumn(
        ctx: Context,
        spreadsheet_id: str,
        sheet_id: int,
        col_index: int,
    ) -> Dict[str, Any]:
        """Insert a new column."""
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
        """Edit an entire column."""
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
        """Share a spreadsheet with a user."""
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
        """Apply basic formatting to a cell range."""
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
