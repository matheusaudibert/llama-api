import asyncio
import logging
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import aiohttp

from .epic_auth import DeviceCodeExpired, EpicGenerator, EpicUser, kill_token
from .logs import fields, session_ref

logger = logging.getLogger("api.sessions")

IDLE_TIMEOUT = 30 * 60


@dataclass
class Session:
    id: str
    verification_url: str
    expires_in: int
    status: str = "pending"  # pending | completed | expired | error
    user: EpicUser | None = None
    error: str | None = None
    last_used: float = field(default_factory=time.monotonic)
    task: asyncio.Task | None = None
    eos_token: str | None = None
    eos_expires_at: str | None = None

    def token_expired(self) -> bool:
        if not self.user or not self.user.expires_at:
            return False
        expires_at = datetime.fromisoformat(self.user.expires_at.replace("Z", "+00:00"))
        return expires_at <= datetime.now(timezone.utc)

    def eos_token_valid(self) -> bool:
        if not self.eos_token or not self.eos_expires_at:
            return False
        expires_at = datetime.fromisoformat(self.eos_expires_at.replace("Z", "+00:00"))
        return expires_at - timedelta(minutes=1) > datetime.now(timezone.utc)


class SessionStore:
    def __init__(self) -> None:
        self.sessions: dict[str, Session] = {}

    async def start_device_login(self) -> Session:
        generator = EpicGenerator()
        await generator.start()
        try:
            device = await generator.create_device_code()
        except Exception:
            await generator.close()
            raise

        session = Session(
            id=secrets.token_urlsafe(24),
            verification_url=device["verification_url"],
            expires_in=device["expires_in"],
        )
        self.sessions[session.id] = session
        session.task = asyncio.create_task(self._wait_login(session, generator, device))
        logger.info("Login started", extra=fields(session=session_ref(session.id), expires_in=session.expires_in, active=len(self.sessions)))
        return session

    async def _wait_login(self, session: Session, generator: EpicGenerator, device: dict) -> None:
        ref = session_ref(session.id)
        started = time.monotonic()
        try:
            session.user = await generator.poll_device_code(
                device["device_code"], device["expires_in"], device["interval"]
            )
            session.status = "completed"
            session.last_used = time.monotonic()
            logger.info("Login completed", extra=fields(session=ref, wait_s=round(time.monotonic() - started)))
        except DeviceCodeExpired as e:
            session.status = "expired"
            logger.info("Login expired", extra=fields(session=ref, reason=str(e)))
        except asyncio.CancelledError:
            raise
        except Exception as e:
            session.status = "error"
            session.error = str(e)
            logger.exception("Login failed", extra=fields(session=ref))
        finally:
            await generator.close()

    def get(self, session_id: str) -> Session | None:
        session = self.sessions.get(session_id)
        if session:
            session.last_used = time.monotonic()
        return session

    async def remove(self, http: aiohttp.ClientSession, session_id: str, reason: str) -> bool:
        """reason: logout, idle, token_expired or shutdown. Only goes to the logs."""
        session = self.sessions.pop(session_id, None)
        if not session:
            return False
        if session.task and not session.task.done():
            session.task.cancel()
        token_revoked = None
        if session.user:
            try:
                status = await kill_token(http, session.user.access_token)
                token_revoked = status in (200, 204)
                if not token_revoked:
                    logger.warning("Epic refused to revoke the token", extra=fields(session=session_ref(session_id), status=status))
            except Exception as e:
                token_revoked = False
                logger.warning("Could not revoke the token", extra=fields(session=session_ref(session_id), error=repr(e)))
        logger.info("Session removed", extra=fields(
            session=session_ref(session_id), reason=reason, status=session.status, token_revoked=token_revoked, active=len(self.sessions),
        ))
        return True

    async def cleanup_forever(self, http: aiohttp.ClientSession) -> None:
        while True:
            await asyncio.sleep(60)
            now = time.monotonic()
            for sid, s in list(self.sessions.items()):
                if s.status == "pending":
                    continue
                if s.token_expired():
                    await self.remove(http, sid, reason="token_expired")
                elif now - s.last_used > IDLE_TIMEOUT:
                    await self.remove(http, sid, reason="idle")
