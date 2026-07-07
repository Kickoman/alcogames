from pydantic import BaseModel, Field, model_validator


class GameBase(BaseModel):
    name: str = Field(min_length=1)
    min_players: int = Field(ge=1)
    max_players: int | None = Field(default=None, ge=1)
    description: str = Field(min_length=1)
    source: str | None = None

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


class ParsedGameFields(BaseModel):
    name: str
    min_players: int = Field(ge=1)
    max_players: int | None = Field(default=None, ge=1)
    description: str
    source: str | None = None


class LikeResponse(BaseModel):
    id: str
    likes: int
    already_liked: bool
