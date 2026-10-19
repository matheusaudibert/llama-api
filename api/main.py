import asyncio
import logging
import os
import secrets
import time
from contextlib import asynccontextmanager

import aiohttp
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response, Security
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import APIKeyHeader

from .cosmetics import Catalog, build_equipped, build_locker
from .epic_data import (
    EpicError,
    get_account_info,
    get_account_stats,
    get_active_loadouts,
    get_banner_ids,
    get_email_info,
    get_eos_token,
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
    Equipped,
    ErrorResponse,
    Health,
    Locker,
    LoginStatusResponse,
    RenderCategory,
    RenderRequest,
)
from .logs import fields, request_id, session_ref, setup_logging
from .rarities import BACKGROUNDS, square_file
from .render import render_category
from .sessions import Session, SessionStore

setup_logging()
logger = logging.getLogger("api")

API_KEY = os.environ.get("API_KEY")
# the Epic client credentials are read in epic_auth and epic_data
REQUIRED_ENV = ["API_KEY", "EPIC_SWITCH_CLIENT", "EPIC_IOS_CLIENT", "EPIC_EOS_CLIENT"]
CATALOG_REFRESH_SECONDS = int(os.environ.get("CATALOG_REFRESH_SECONDS", 6 * 60 * 60))
# public base URL for the links this API serves (images.background); defaults to the request's host
PUBLIC_URL = os.environ.get("PUBLIC_URL", "").rstrip("/")

catalog = Catalog()
store = SessionStore()
http: aiohttp.ClientSession


@asynccontextmanager
async def lifespan(app: FastAPI):
    global http
    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"Set these environment variables before starting the API: {', '.join(missing)}")

    logger.info("Starting", extra=fields(version=app.version, catalog_refresh_s=CATALOG_REFRESH_SECONDS))
    http = aiohttp.ClientSession()
    await catalog.refresh(http)
    tasks = [
        asyncio.create_task(catalog.refresh_forever(http, CATALOG_REFRESH_SECONDS)),
        asyncio.create_task(store.cleanup_forever(http)),
    ]
    logger.info("Ready")
    yield
    logger.info("Shutting down", extra=fields(sessions=len(store.sessions)))
    for t in tasks:
        t.cancel()
    for sid in list(store.sessions):
        await store.remove(http, sid, reason="shutdown")
    await http.close()


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_api_key(key: str | None = Security(api_key_header)):
    if key != API_KEY:
        logger.warning("Rejected API key", extra=fields(reason="missing" if not key else "wrong"))
        raise HTTPException(status_code=401, detail="Invalid API key")


app = FastAPI(
    title="Llama API",
    description="Logs in to an Epic Games account with the device code flow and reads the Fortnite data.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    # keep a caller's id so a bot can match its own logs, but cap it: it is client input
    rid = (request.headers.get("x-request-id") or secrets.token_hex(6))[:64]
    token = request_id.set(rid)
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled error", extra=fields(method=request.method, route=request.url.path))
        response = JSONResponse({"detail": "Internal server error"}, status_code=500)

    # the route template (/auth/{session_id}), never the raw path with the session id
    route = request.scope.get("route")
    sid = request.path_params.get("session_id")
    level = logging.ERROR if response.status_code >= 500 else logging.DEBUG if request.url.path == "/health" else logging.INFO
    logger.log(level, "Request", extra=fields(
        method=request.method,
        route=getattr(route, "path", request.url.path),
        status=response.status_code,
        ms=round((time.perf_counter() - start) * 1000),
        session=sid and session_ref(sid),
    ))
    response.headers["X-Request-ID"] = rid
    request_id.reset(token)
    return response


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


def public_url(request: Request) -> str:
    return PUBLIC_URL or str(request.base_url).rstrip("/")


def absolute_background(item: dict, base: str) -> None:
    item["images"]["background"] = base + item["images"]["background"]


@app.get(
    "/backgrounds/{name}.png",
    response_class=FileResponse,
    tags=["Images"],
    summary="Rarity background",
    responses={200: {"content": {"image/png": {}}, "description": "PNG of the rarity background"}, 404: {"model": ErrorResponse, "description": "Unknown rarity background"}},
)
async def rarity_background(name: str):
    """The square drawn behind an item of that rarity, as linked in `images.background`. Does not require an API key."""
    if name not in BACKGROUNDS:
        raise HTTPException(status_code=404, detail="Unknown rarity background")
    return FileResponse(square_file(name), media_type="image/png", headers={"Cache-Control": "public, max-age=604800"})


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
        logger.warning("Could not create device code", extra=fields(error=repr(e)))
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
    if not await store.remove(http, session_id, reason="logout"):
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
        account, external_auths, email_info, common_core, athena = await asyncio.gather(
            get_account_info(http, user),
            get_external_auths(http, user),
            get_email_info(http, user),
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
        # Epic does not send the account creation date to this client; the Fortnite profile date is the closest
        "profile_created": common_core.get("created"),
        "last_login": account.get("lastLogin"),
        "can_change_display_name": account.get("canUpdateDisplayName", False),
        "display_name_changes": account.get("numberOfDisplayNameChanges", 0),
        "last_display_name_change": account.get("lastDisplayNameChange"),
        "display_name_change_available_at": None if account.get("canUpdateDisplayName") else account.get("canUpdateDisplayNameNext"),
        "can_change_email": email_info.get("canUpdateEmail"),
        "last_email_change": email_info.get("lastEmailUpdate"),
        # Epic only locks the email for a while after a change; no date when it can be changed now
        "email_change_available_at": None if email_info.get("canUpdateEmail") else email_info.get("canUpdateNext"),
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
async def account_locker(request: Request, session: Session = Depends(logged_session)):
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
    base = public_url(request)
    for items in locker.values():
        for item in items:
            absolute_background(item, base)
    return {
        "counts": {k: len(v) for k, v in locker.items()},
        "shop": {
            "counts": {k: sum(i["from_shop"] for i in v) for k, v in locker.items()},
            "estimated_vbucks": sum(i["estimated_price"] or 0 for v in locker.values() for i in v),
        },
        **locker,
    }


@router.get(
    "/accounts/{session_id}/equipped",
    response_model=Equipped,
    tags=["Account"],
    summary="Equipped items",
    responses=ACCOUNT_ERRORS,
)
async def account_equipped(request: Request, session: Session = Depends(logged_session)):
    """The items equipped in the player's active loadout: skin, backpack, pickaxe, glider, emotes, wraps and more. Saved presets are not included."""
    try:
        if not session.eos_token_valid():
            eos = await get_eos_token(http, session.user)
            session.eos_token, session.eos_expires_at = eos["access_token"], eos["expires_at"]
            logger.info("EOS token issued", extra=fields(session=session_ref(session.id)))
        loadouts = await get_active_loadouts(http, session.user, session.eos_token)
    except EpicError as e:
        raise HTTPException(status_code=502, detail=str(e))
    equipped = await build_equipped(http, catalog, loadouts)
    base = public_url(request)
    for value in equipped.values():
        for item in value if isinstance(value, list) else [value]:
            if item:
                absolute_background(item, base)
    return equipped


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
    start = time.perf_counter()
    png = await render_category(http, catalog, category.value, owned, body.display_name, body.language)
    logger.info("Image rendered", extra=fields(
        category=category.value,
        items=len(owned),
        language=body.language,
        kb=png and len(png) // 1024,
        ms=round((time.perf_counter() - start) * 1000),
    ))
    if png is None:
        raise HTTPException(status_code=422, detail=f"No {category.value} in the item list")
    return Response(content=png, media_type="image/png")


app.include_router(router)
