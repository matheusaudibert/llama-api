import asyncio
import logging
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import aiohttp

from .epic_auth import DeviceCodeExpired, EpicGenerator, EpicUser, kill_token

logger = logging.getLogger(__name__)

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
        return session

    async def _wait_login(self, session: Session, generator: EpicGenerator, device: dict) -> None:
        try:
            session.user = await generator.poll_device_code(
                device["device_code"], device["expires_in"], device["interval"]
            )
            session.status = "completed"
            session.last_used = time.monotonic()
            logger.info(f"Session {session.id[:6]}… logged in")
        except DeviceCodeExpired:
            session.status = "expired"
        except Exception as e:
            session.status = "error"
            session.error = str(e)
            logger.error(f"Login failed for session {session.id[:6]}…: {e}")
        finally:
            await generator.close()

    def get(self, session_id: str) -> Session | None:
        session = self.sessions.get(session_id)
        if session:
            session.last_used = time.monotonic()
        return session

    async def remove(self, http: aiohttp.ClientSession, session_id: str) -> bool:
        session = self.sessions.pop(session_id, None)
        if not session:
            return False
        if session.task and not session.task.done():
            session.task.cancel()
        if session.user:
            try:
                await kill_token(http, session.user.access_token)
            except Exception as e:
                logger.warning(f"Could not kill token: {e}")
        return True

    async def cleanup_forever(self, http: aiohttp.ClientSession) -> None:
        while True:
            await asyncio.sleep(60)
            now = time.monotonic()
            for sid, s in list(self.sessions.items()):
                if s.status == "pending":
                    continue
                if now - s.last_used > IDLE_TIMEOUT or s.token_expired():
                    await self.remove(http, sid)
