from fastapi import APIRouter, HTTPException, Request, Response

from .. import storage
from ..models import Game, LikeResponse

router = APIRouter(prefix="/api", tags=["games"])

LIKED_COOKIE = "liked_games"
COOKIE_MAX_AGE = 10 * 365 * 24 * 60 * 60  # ~10 years


def _parse_liked_cookie(request: Request) -> set[str]:
    raw = request.cookies.get(LIKED_COOKIE, "")
    return {item for item in raw.split(",") if item}


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/games", response_model=list[Game])
def list_games() -> list[Game]:
    return storage.get_all_games()


@router.post("/games/{game_id}/like", response_model=LikeResponse)
def like_game(game_id: str, request: Request, response: Response) -> LikeResponse:
    liked = _parse_liked_cookie(request)

    if game_id in liked:
        game = storage.get_game(game_id)
        if game is None:
            raise HTTPException(status_code=404, detail="Game not found")
        return LikeResponse(id=game_id, likes=game.likes, already_liked=True)

    game = storage.like_game(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    liked.add(game_id)
    response.set_cookie(
        key=LIKED_COOKIE,
        value=",".join(liked),
        max_age=COOKIE_MAX_AGE,
        path="/",
        samesite="lax",
    )
    return LikeResponse(id=game_id, likes=game.likes, already_liked=False)
