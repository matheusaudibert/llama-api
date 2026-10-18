from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class DeviceLoginResponse(BaseModel):
    session_id: str = Field(description="ID opaco usado em todas as outras chamadas deste login.")
    verification_url: str = Field(description="Página da Epic Games onde o jogador autoriza o login.")
    expires_in: int = Field(description="Segundos até o link de verificação expirar.")


class LoginStatusResponse(BaseModel):
    status: Literal["pending", "completed", "expired", "error"] = Field(description="Estado atual do login.")
    account_id: str | None = Field(None, description="ID da conta Epic. Presente quando `completed`.")
    display_name: str | None = Field(None, description="Nome de exibição da conta. Presente quando `completed`.")
    error: str | None = Field(None, description="Mensagem de erro quando `error`.")


class ExternalAuth(BaseModel):
    type: str | None = Field(None, description="Plataforma, ex: psn, xbl, nintendo, github, steam.")
    display_name: str | None = Field(None, description="Nome do jogador na plataforma.")
    date_added: str | None = Field(None, description="Data em que a plataforma foi conectada (ISO 8601).")


class PastSeason(BaseModel):
    season: int | None = Field(None, description="Número da temporada.")
    level: int | None = Field(None, description="Nível alcançado na temporada.")
    battle_pass_purchased: bool = Field(False, description="Se o passe de batalha foi comprado.")
    wins: int = Field(0, description="Vitórias na temporada.")


class AccountSummary(BaseModel):
    account_id: str
    display_name: str
    email: str | None = Field(None, description="Email sem máscara. Mascare antes de exibir em canais públicos.")
    email_verified: bool
    name: str | None = None
    last_name: str | None = None
    country: str | None = Field(None, description="Código do país (ISO 3166-1 alpha-2).")
    tfa_enabled: bool = Field(description="Se a autenticação de dois fatores está ativa.")
    minor_verified: bool = Field(description="Se a conta tem controle parental / verificação de menor.")
    account_created: str | None = Field(None, description="Criação da conta Epic (ISO 8601).")
    profile_created: str | None = Field(None, description="Criação do perfil no Fortnite (ISO 8601).")
    vbucks: int = Field(description="Total de V-Bucks somando todas as fontes.")
    external_auths: list[ExternalAuth] = Field(description="Plataformas conectadas à conta.")
    account_level: int
    total_wins: int = Field(description="Soma das vitórias de todas as temporadas passadas.")
    total_matches: int = Field(description="Soma das partidas de todas as temporadas passadas.")
    last_match_end: str | None = Field(None, description="Fim da última partida jogada (ISO 8601).")
    past_seasons: list[PastSeason]


class CosmeticImages(BaseModel):
    icon: str | None = None
    small_icon: str | None = None
    featured: str | None = None


class Cosmetic(BaseModel):
    id: str = Field(description="ID do cosmético em minúsculas, ex: cid_028_athena_commando_f.")
    name: str = Field(description="Nome do item. Igual ao `id` quando o item não está no catálogo.")
    rarity: str = Field(description="Common, Uncommon, Rare, Epic, Legendary, Mythic ou uma série, como Icon Series.")
    series: str | None = Field(None, description="Série do item, quando houver.")
    type: str | None = Field(None, description="Tipo no fortnite-api, ex: outfit, backpack, pickaxe, emote, glider.")
    images: CosmeticImages
    owned_styles: list[str] = Field(description="Tags dos estilos que o jogador desbloqueou.")
    is_exclusive: bool = Field(description="Faz parte da lista de itens exclusivos (Renegade Raider, Ghoul Trooper…).")
    is_mythic: bool = Field(description="Item raro/OG: de uma lista de raros que não volta à loja há 2 anos, ou com o estilo exclusivo dos donos originais.")
    in_catalog: bool = Field(description="False quando o fortnite-api ainda não tem dados deste item.")


class LockerCounts(BaseModel):
    skins: int
    backpacks: int
    pickaxes: int
    emotes: int
    gliders: int
    wraps: int
    sprays: int
    others: int
    banners: int


class Locker(BaseModel):
    counts: LockerCounts = Field(description="Quantidade de itens por categoria.")
    skins: list[Cosmetic]
    backpacks: list[Cosmetic]
    pickaxes: list[Cosmetic]
    emotes: list[Cosmetic]
    gliders: list[Cosmetic]
    wraps: list[Cosmetic]
    sprays: list[Cosmetic]
    others: list[Cosmetic]
    banners: list[Cosmetic]


class RenderCategory(str, Enum):
    skins = "skins"
    backpacks = "backpacks"
    pickaxes = "pickaxes"
    gliders = "gliders"
    emotes = "emotes"
    mythics = "mythics"


class RenderItem(BaseModel):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$", description="ID do cosmético, como vem no `/locker`.")
    owned_styles: list[str] = Field(default_factory=list, description="Estilos desbloqueados. Usado para reconhecer os OGs.")


class RenderRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=64, description="Nick da conta, exibido no rodapé.")
    items: list[RenderItem] = Field(
        max_length=5000,
        description="Itens da conta. Pode mandar os itens do `/locker` direto: campos extras são ignorados e só entram os da categoria pedida.",
    )


class Health(BaseModel):
    status: Literal["ok"]
    cosmetics_loaded: int = Field(description="Cosméticos no catálogo em memória.")
    active_sessions: int = Field(description="Sessões de login em memória.")


class ErrorResponse(BaseModel):
    detail: str
