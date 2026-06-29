import os
import sqlite3
import time
from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP
import ratelimit
from audit import audited
from whatsapp import (
    search_contacts as whatsapp_search_contacts,
    list_messages as whatsapp_list_messages,
    list_chats as whatsapp_list_chats,
    get_chat as whatsapp_get_chat,
    get_message_context as whatsapp_get_message_context,
    send_message as whatsapp_send_message,
    send_file as whatsapp_send_file,
    download_media as whatsapp_download_media
)
from allowlist import (
    load_allowlist,
    filter_chats,
    filter_messages,
    filter_contacts,
    is_allowed,
    check_send,
    AllowlistError,
)

ALLOWLIST_PATH = os.environ.get(
    "WHATSAPP_ALLOWLIST_PATH",
    os.path.join(os.path.dirname(__file__), "allowed_chats.json"),
)
# Fail-closed: if this raises, the server does not start.
ALLOWLIST = load_allowlist(ALLOWLIST_PATH)

# Global kill-switch: disables all sends when set (reads still work).
READ_ONLY = os.environ.get("WHATSAPP_READ_ONLY", "").strip().lower() in (
    "1", "true", "yes", "on",
)
RATE_LIMITER = ratelimit.from_env()

# Initialize FastMCP server
mcp = FastMCP("whatsapp")

@mcp.tool()
@audited
def search_contacts(query: str) -> List[Dict[str, Any]]:
    """Search WhatsApp contacts by name or phone number.

    Args:
        query: Search term to match against contact names or phone numbers
    """
    contacts = whatsapp_search_contacts(query)
    return filter_contacts(contacts, ALLOWLIST)

@mcp.tool()
@audited
def list_messages(
    after: Optional[str] = None,
    before: Optional[str] = None,
    sender_phone_number: Optional[str] = None,
    chat_jid: Optional[str] = None,
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_context: bool = True,
    context_before: int = 1,
    context_after: int = 1
) -> Any:
    """Get WhatsApp messages for an allowlisted chat.

    A chat_jid is required. Call list_allowed_chats to see permitted chats,
    then pass one here. The bridge returns a pre-formatted string scoped to
    the single allowlisted chat, so no further filtering is needed.

    Args:
        after: Optional ISO-8601 formatted string to only return messages after this date
        before: Optional ISO-8601 formatted string to only return messages before this date
        sender_phone_number: Optional phone number to filter messages by sender
        chat_jid: Required chat JID to scope the query (must be in the allowlist)
        query: Optional search term to filter messages by content
        limit: Maximum number of messages to return (default 20)
        page: Page number for pagination (default 0)
        include_context: Whether to include messages before and after matches (default True)
        context_before: Number of messages to include before each match (default 1)
        context_after: Number of messages to include after each match (default 1)
    """
    if chat_jid is None:
        return {
            "error": (
                "list_messages requires a chat_jid. "
                "Call list_allowed_chats to see permitted chats, then pass one."
            )
        }
    if not is_allowed(chat_jid, ALLOWLIST):
        return {"error": f"{chat_jid} is not in the allowlist."}
    return whatsapp_list_messages(
        after=after,
        before=before,
        sender_phone_number=sender_phone_number,
        chat_jid=chat_jid,
        query=query,
        limit=limit,
        page=page,
        include_context=include_context,
        context_before=context_before,
        context_after=context_after
    )

@mcp.tool()
@audited
def list_chats(
    query: Optional[str] = None,
    limit: int = 20,
    page: int = 0,
    include_last_message: bool = True,
    sort_by: str = "last_active"
) -> List[Dict[str, Any]]:
    """Get WhatsApp chats matching specified criteria.
    
    Args:
        query: Optional search term to filter chats by name or JID
        limit: Maximum number of chats to return (default 20)
        page: Page number for pagination (default 0)
        include_last_message: Whether to include the last message in each chat (default True)
        sort_by: Field to sort results by, either "last_active" or "name" (default "last_active")
    """
    chats = whatsapp_list_chats(
        query=query,
        limit=limit,
        page=page,
        include_last_message=include_last_message,
        sort_by=sort_by
    )
    return filter_chats(chats, ALLOWLIST)

@mcp.tool()
@audited
def get_chat(chat_jid: str, include_last_message: bool = True) -> Dict[str, Any]:
    """Get WhatsApp chat metadata by JID.
    
    Args:
        chat_jid: The JID of the chat to retrieve
        include_last_message: Whether to include the last message (default True)
    """
    if not is_allowed(chat_jid, ALLOWLIST):
        return {"error": f"{chat_jid} is not in the allowlist."}
    return whatsapp_get_chat(chat_jid, include_last_message)

@mcp.tool()
@audited
def get_message_context(
    message_id: str,
    before: int = 5,
    after: int = 5
) -> Dict[str, Any]:
    """Get context around a specific WhatsApp message.

    Args:
        message_id: The ID of the message to get context for
        before: Number of messages to include before the target message (default 5)
        after: Number of messages to include after the target message (default 5)
    """
    try:
        ctx = whatsapp_get_message_context(message_id, before, after)
    except (ValueError, sqlite3.Error) as e:
        return {"error": f"Message not found or not retrievable: {e}"}
    if not is_allowed(ctx.message.chat_jid, ALLOWLIST):
        return {"error": "Message not found or not in the allowlist."}
    # Defense-in-depth: the bridge already scopes context to the target chat,
    # so these are normally no-ops — kept in case a future bridge change returns
    # cross-chat context.
    ctx.before = filter_messages(ctx.before, ALLOWLIST)
    ctx.after = filter_messages(ctx.after, ALLOWLIST)
    return ctx

@mcp.tool()
@audited
def send_message(recipient: str, message: str) -> Dict[str, Any]:
    """Send a text message to an allowlisted person or group."""
    if READ_ONLY:
        return {"success": False, "message": "sends disabled (read-only mode)"}
    try:
        jid = check_send(recipient, ALLOWLIST)
    except AllowlistError as e:
        return {"success": False, "message": str(e)}
    allowed, reason = RATE_LIMITER.try_send(time.time())
    if not allowed:
        return {"success": False, "message": f"rate limited: {reason}"}
    success, status = whatsapp_send_message(jid, message)
    return {"success": success, "message": status}

@mcp.tool()
@audited
def send_file(recipient: str, media_path: str) -> Dict[str, Any]:
    """Send an image, video, or document to an allowlisted person or group."""
    if READ_ONLY:
        return {"success": False, "message": "sends disabled (read-only mode)"}
    try:
        jid = check_send(recipient, ALLOWLIST)
    except AllowlistError as e:
        return {"success": False, "message": str(e)}
    allowed, reason = RATE_LIMITER.try_send(time.time())
    if not allowed:
        return {"success": False, "message": f"rate limited: {reason}"}
    success, status = whatsapp_send_file(jid, media_path)
    return {"success": success, "message": status}

@mcp.tool()
@audited
def download_media(message_id: str, chat_jid: str) -> Dict[str, Any]:
    """Download media from a WhatsApp message and get the local file path.
    
    Args:
        message_id: The ID of the message containing the media
        chat_jid: The JID of the chat containing the message
    
    Returns:
        The underlying bridge result on success, or {"error": ...} if chat_jid is not in the allowlist.
    """
    if not is_allowed(chat_jid, ALLOWLIST):
        return {"error": f"{chat_jid} is not in the allowlist."}
    return whatsapp_download_media(message_id, chat_jid)

@mcp.tool()
@audited
def list_allowed_chats():
    """Return the chats the agent may access, each with its mode (read / read+send)."""
    return [{"jid": jid, "label": v["label"], "mode": v["mode"]}
            for jid, v in ALLOWLIST.items()]


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
