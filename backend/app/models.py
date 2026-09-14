import re

from pydantic import BaseModel, Field, field_validator, model_validator


def _clean_tags(tags: list[str] | None) -> list[str]:
    out: list[str] = []
    for t in tags or []:
        t = str(t).strip().lower().strip("[]#")
        if t and t not in out:
            out.append(t)
    return out[:6]


class GameBase(BaseModel):
    name: str = Field(min_length=1)
    min_players: int = Field(ge=1)
    max_players: int | None = Field(default=None, ge=1)
    description: str = Field(min_length=1)
    source: str | None = None
    # Catalogue metadata, usually filled by the LLM: a one-line teaser for the
    # list, rough duration, keyword tags and what you need to bring.
    summary: str | None = None
    minutes: int | None = Field(default=None, ge=1, le=600)
    tags: list[str] = Field(default_factory=list)
    props: str | None = None

    @field_validator("tags", mode="before")
    @classmethod
    def normalise_tags(cls, v: list[str] | None) -> list[str]:
        return _clean_tags(v)

    @model_validator(mode="after")
    def check_player_range(self) -> "GameBase":
        if self.max_players is not None and self.max_players < self.min_players:
            raise ValueError("max_players must be >= min_players")
        return self


class GameCreate(GameBase):
    pass


class GameUpdate(GameBase):
    pass


class Game(GameBase):
    id: str
    date_added: str
    likes: int = 0


class ParseRequest(BaseModel):
    text: str = Field(min_length=1)


class GameMeta(BaseModel):
    """What the LLM adds on top of the rules: list teaser, duration, tags, props."""

    summary: str | None = None
    minutes: int | None = Field(default=None, ge=1, le=600)
    tags: list[str] = Field(default_factory=list)
    props: str | None = None

    @field_validator("tags", mode="before")
    @classmethod
    def normalise_tags(cls, v: list[str] | None) -> list[str]:
        return _clean_tags(v)

    @field_validator("minutes", mode="before")
    @classmethod
    def coerce_minutes(cls, v):  # models sometimes answer "20 мин" or "15-20"
        if isinstance(v, str):
            m = re.search(r"\d+", v)
            v = int(m.group()) if m else None
        return v


class ParsedGameFields(GameMeta):
    name: str
    min_players: int = Field(ge=1)
    max_players: int | None = Field(default=None, ge=1)
    description: str
    source: str | None = None


class LikeResponse(BaseModel):
    id: str
    likes: int
    already_liked: bool


class LLMSettingsOut(BaseModel):
    """Admin view of the LLM settings. Keys are never returned, only their last 4 chars."""

    provider: str
    ready: bool
    model: str
    deepseek_key_tail: str
    deepseek_base_url: str
    deepseek_model: str
    yandex_key_tail: str
    yandex_folder_id: str
    yandex_model: str


class LLMSettingsIn(BaseModel):
    """Partial update. Omitted fields are untouched; an empty key keeps the stored one,
    `clear_*` removes it."""

    provider: str | None = Field(default=None, pattern=r"^(none|deepseek|yandex)$")
    deepseek_api_key: str | None = Field(default=None, max_length=500)
    deepseek_base_url: str | None = Field(default=None, max_length=200)
    deepseek_model: str | None = Field(default=None, max_length=80)
    yandex_api_key: str | None = Field(default=None, max_length=500)
    yandex_folder_id: str | None = Field(default=None, max_length=64)
    yandex_model: str | None = Field(default=None, max_length=80)
    clear_deepseek_api_key: bool = False
    clear_yandex_api_key: bool = False


class LLMTestOut(BaseModel):
    ok: bool
    detail: str
    provider: str
    model: str
