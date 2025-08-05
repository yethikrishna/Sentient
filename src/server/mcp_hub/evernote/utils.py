from typing import Dict, Any, Optional, List
import httpx
from evernote.api.client import EvernoteClient
from evernote.edam.notestore import NoteStore
from evernote.edam.type import ttypes as Types
import asyncio

# Use production by default, as requested.
EVERNOTE_IS_SANDBOX = os.getenv("EVERNOTE_SANDBOX", "False").lower() in ('true', '1', 't')

class EvernoteApiClient:
    def __init__(self, token_info: Dict[str, Any]):
        self._token_info = token_info
        self._client = EvernoteClient(
            token=self._token_info.get('oauth_token'),
            sandbox=EVERNOTE_IS_SANDBOX,
            china=False
        )
        self._note_store = self._client.get_note_store()

    async def _run_sync(self, func, *args, **kwargs):
        """Runs a synchronous SDK call in a thread pool."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    async def list_notebooks(self) -> List[Dict[str, Any]]:
        notebooks = await self._run_sync(self._note_store.listNotebooks)
        return [{"guid": nb.guid, "name": nb.name} for nb in notebooks]

    async def create_note(self, notebook_guid: str, title: str, content: str) -> Dict[str, Any]:
        note = Types.Note()
        note.title = title
        note.notebookGuid = notebook_guid

        note.content = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">'
            f'<en-note><div>{content}</div></en-note>'
        )

        created_note = await self._run_sync(self._note_store.createNote, note)
        return {"guid": created_note.guid, "title": created_note.title}
