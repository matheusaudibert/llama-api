import asyncio
import logging
import os
from contextlib import asynccontextmanager

import aiohttp
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Response, Security
from fastapi.security import APIKeyHeader

from .cosmetics import Catalog, build_locker
from .epic_data import (
    EpicError,
    get_account_info,
    get_account_stats,
    get_banner_ids,
    get_external_auths,
    get_linkable_platforms,
    get_purchase_info,
    get_vbucks,
    get_vbucks_by_platform,
    query_profile,
)
from .models import (
    AccountSummary,
    DeviceLoginResponse,
    ErrorResponse,
    Health,
    Locker,
    LoginStatusResponse,
    RenderCategory,
    RenderRequest,
)
from .render import render_category
from .sessions import Session, SessionStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

API_KEY = os.environ.get("API_KEY")
CATALOG_REFRESH_SECONDS = int(os.environ.get("CATALOG_REFRESH_SECONDS", 6 * 60 * 60))

catalog = Catalog()
store = SessionStore()
http: aiohttp.ClientSession


@asynccontextmanager
async def lifespan(app: FastAPI):
    global http
    if not API_KEY:
        raise RuntimeError("Set the API_KEY environment variable before starting the API")

    http = aiohttp.ClientSession()
    await catalog.refresh(http)
    tasks = [
        asyncio.create_task(catalog.refresh_forever(http, CATALOG_REFRESH_SECONDS)),
        asyncio.create_task(store.cleanup_forever(http)),
    ]
    yield
    for t in tasks:
        t.cancel()
    for sid in list(store.sessions):
        await store.remove(http, sid)
    await http.close()


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(key: str | None = Security(api_key_header)):
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


app = FastAPI(
    title="Llama API",
    description="Logs in to an Epic Games account with the device code flow and reads the Fortnite data.",
    version="1.0.0",
    lifespan=lifespan,
)
router = APIRouter(
    dependencies=[Depends(require_api_key)],
    responses={401: {"model": ErrorResponse, "description": "Missing or invalid API key"}},
)

NOT_FOUND = {404: {"model": ErrorResponse, "description": "Session not found or already removed"}}
ACCOUNT_ERRORS = {
    **NOT_FOUND,
    409: {"model": ErrorResponse, "description": "Login not completed (pending, expired or error)"},
    410: {"model": ErrorResponse, "description": "Epic token expired, start a new login"},
    502: {"model": ErrorResponse, "description": "Epic Games returned an error"},
}


def logged_session(session_id: str) -> Session:
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "completed":
        raise HTTPException(status_code=409, detail=f"Session is {session.status}")
    if session.token_expired():
        raise HTTPException(status_code=410, detail="Epic token expired, log in again")
    return session


@app.get("/health", response_model=Health, tags=["Health"], summary="Health check")
async def health():
    """Does not require an API key. Use it as your host's healthcheck."""
    return {"status": "ok", "cosmetics_loaded": len(catalog.cosmetics), "active_sessions": len(store.sessions)}


@router.post(
    "/auth/device",
    response_model=DeviceLoginResponse,
    tags=["Authentication"],
    summary="Start login",
    responses={502: {"model": ErrorResponse, "description": "Could not create the Epic device code"}},
)
async def start_device_login():
    """Creates an Epic device code and waits for the authorization in the background. Show `verification_url` to the player."""
    try:
        session = await store.start_device_login()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not create Epic device code: {e}")
    return {
        "session_id": session.id,
        "verification_url": session.verification_url,
        "expires_in": session.expires_in,
    }


@router.get("/auth/{session_id}", response_model=LoginStatusResponse, tags=["Authentication"], summary="Login status", responses=NOT_FOUND)
async def login_status(session_id: str):
    """Poll every ~3 s until the status leaves `pending`."""
    session = store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    result = {"status": session.status}
    if session.user:
        result["account_id"] = session.user.account_id
        result["display_name"] = session.user.display_name
    if session.error:
        result["error"] = session.error
    return result


@router.delete("/auth/{session_id}", status_code=204, tags=["Authentication"], summary="End session", responses=NOT_FOUND)
async def logout(session_id: str):
    """Revokes the Epic token and deletes the session from memory."""
    if not await store.remove(http, session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return Response(status_code=204)


@router.get(
    "/accounts/{session_id}/summary",
    response_model=AccountSummary,
    tags=["Account"],
    summary="Account summary",
    responses=ACCOUNT_ERRORS,
)
async def account_summary(session: Session = Depends(logged_session)):
    """Epic account data, V-Bucks, connected platforms and Battle Royale stats."""
    user = session.user
    try:
        account, external_auths, common_core, athena = await asyncio.gather(
            get_account_info(http, user),
            get_external_auths(http, user),
            query_profile(http, user, "common_core"),
            query_profile(http, user, "athena"),
        )
    except EpicError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {
        "account_id": user.account_id,
        "display_name": user.display_name,
        "email": account.get("email"),
        "email_verified": account.get("emailVerified", False),
        "name": account.get("name"),
        "last_name": account.get("lastName"),
        "country": account.get("country"),
        "tfa_enabled": account.get("tfaEnabled", False),
        "minor_verified": account.get("minorVerified", False),
        "account_created": account.get("created"),
        "profile_created": common_core.get("created"),
        "last_login": account.get("lastLogin"),
        "can_change_display_name": account.get("canUpdateDisplayName", False),
        "display_name_changes": account.get("numberOfDisplayNameChanges", 0),
        "last_display_name_change": account.get("lastDisplayNameChange"),
        "vbucks": get_vbucks(common_core),
        "vbucks_by_platform": get_vbucks_by_platform(common_core),
        **get_purchase_info(common_core),
        "linkable_platforms": get_linkable_platforms(external_auths),
        "external_auths": [
            {
                "type": a.get("type"),
                "display_name": a.get("externalDisplayName"),
                "date_added": a.get("dateAdded"),
            }
            for a in external_auths
        ],
        **get_account_stats(athena),
    }


@router.get(
    "/accounts/{session_id}/locker",
    response_model=Locker,
    tags=["Account"],
    summary="Locker",
    responses=ACCOUNT_ERRORS,
)
async def account_locker(session: Session = Depends(logged_session)):
    """Every cosmetic on the account, split by category and sorted by rarity."""
    user = session.user
    try:
        athena, common_core = await asyncio.gather(
            query_profile(http, user, "athena"),
            query_profile(http, user, "common_core"),
        )
    except EpicError as e:
        raise HTTPException(status_code=502, detail=str(e))

    locker = await build_locker(http, catalog, athena, get_banner_ids(common_core))
    return {
        "counts": {k: len(v) for k, v in locker.items()},
        **locker,
    }


@router.post(
    "/render/{category}",
    response_class=Response,
    tags=["Images"],
    summary="Locker image",
    responses={
        200: {"content": {"image/png": {}}, "description": "PNG with the items of the category"},
        422: {"model": ErrorResponse, "description": "No item of the category in the list"},
    },
)
async def render_locker(category: RenderCategory, body: RenderRequest):
    """Renders a PNG with the items of one category, in skin checker style. `mythics` gathers the mythic items of every category. No session needed: send the items saved from `/locker`."""
    owned = {}
    for item in body.items:
        owned.setdefault(item.id.lower(), []).extend(item.owned_styles)
    png = await render_category(http, catalog, category.value, owned, body.display_name)
    if png is None:
        raise HTTPException(status_code=422, detail=f"No {category.value} in the item list")
    return Response(content=png, media_type="image/png")


app.include_router(router)
