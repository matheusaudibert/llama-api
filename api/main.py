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
    get_vbucks,
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
    title="Fortnite Account API",
    description="Faz login numa conta Epic Games pelo device code flow e lê os dados do Fortnite.",
    version="1.0.0",
    lifespan=lifespan,
)
router = APIRouter(
    dependencies=[Depends(require_api_key)],
    responses={401: {"model": ErrorResponse, "description": "API key ausente ou inválida"}},
)

NOT_FOUND = {404: {"model": ErrorResponse, "description": "Sessão não encontrada ou já removida"}}
ACCOUNT_ERRORS = {
    **NOT_FOUND,
    409: {"model": ErrorResponse, "description": "Login não concluído (pending, expired ou error)"},
    410: {"model": ErrorResponse, "description": "Token da Epic expirou, inicie um novo login"},
    502: {"model": ErrorResponse, "description": "A Epic Games retornou um erro"},
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
    """Não exige API key. Use no healthcheck da hospedagem."""
    return {"status": "ok", "cosmetics_loaded": len(catalog.cosmetics), "active_sessions": len(store.sessions)}


@router.post(
    "/auth/device",
    response_model=DeviceLoginResponse,
    tags=["Autenticação"],
    summary="Iniciar login",
    responses={502: {"model": ErrorResponse, "description": "Não foi possível criar o device code na Epic"}},
)
async def start_device_login():
    """Cria um device code na Epic e começa a esperar a autorização em background. Mostre `verification_url` ao jogador."""
    try:
        session = await store.start_device_login()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not create Epic device code: {e}")
    return {
        "session_id": session.id,
        "verification_url": session.verification_url,
        "expires_in": session.expires_in,
    }


@router.get("/auth/{session_id}", response_model=LoginStatusResponse, tags=["Autenticação"], summary="Status do login", responses=NOT_FOUND)
async def login_status(session_id: str):
    """Consulte a cada ~3 s até o status sair de `pending`."""
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


@router.delete("/auth/{session_id}", status_code=204, tags=["Autenticação"], summary="Encerrar sessão", responses=NOT_FOUND)
async def logout(session_id: str):
    """Invalida o token na Epic e apaga a sessão da memória."""
    if not await store.remove(http, session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return Response(status_code=204)


@router.get(
    "/accounts/{session_id}/summary",
    response_model=AccountSummary,
    tags=["Conta"],
    summary="Resumo da conta",
    responses=ACCOUNT_ERRORS,
)
async def account_summary(session: Session = Depends(logged_session)):
    """Dados da conta Epic, V-Bucks, plataformas conectadas e estatísticas do Battle Royale."""
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
        "vbucks": get_vbucks(common_core),
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
    tags=["Conta"],
    summary="Locker",
    responses=ACCOUNT_ERRORS,
)
async def account_locker(session: Session = Depends(logged_session)):
    """Todos os cosméticos da conta, separados por categoria e ordenados por raridade."""
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
    tags=["Imagens"],
    summary="Imagem do locker",
    responses={
        200: {"content": {"image/png": {}}, "description": "PNG com os itens da categoria"},
        422: {"model": ErrorResponse, "description": "Nenhum item da categoria na lista enviada"},
    },
)
async def render_locker(category: RenderCategory, body: RenderRequest):
    """Gera um PNG com os itens de uma categoria, no estilo dos checkers. `mythics` junta os itens míticos de todas as categorias. Não exige sessão: envie os itens salvos do `/locker`."""
    owned = {}
    for item in body.items:
        owned.setdefault(item.id.lower(), []).extend(item.owned_styles)
    png = await render_category(http, catalog, category.value, owned, body.display_name)
    if png is None:
        raise HTTPException(status_code=422, detail=f"No {category.value} in the item list")
    return Response(content=png, media_type="image/png")


app.include_router(router)
