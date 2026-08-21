from fastapi import APIRouter, Depends, HTTPException, Response

from .. import storage
from ..deps import require_admin_token
from ..logging_setup import get_logger
from ..models import Game, GameCreate, GameUpdate

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin_token)],
)
log = get_logger(stream="internal")


@router.post("/games", response_model=Game, status_code=201)
def create_game(data: GameCreate) -> Game:
    game = storage.create_game(data)
    log.info("game_created", game_id=game.id, name=game.name)
    return game


@router.put("/games/{game_id}", response_model=Game)
def update_game(game_id: str, data: GameUpdate) -> Game:
    game = storage.update_game(game_id, data)
    if game is None:
        log.warning("game_not_found", game_id=game_id, action="update")
        raise HTTPException(status_code=404, detail="Game not found")
    log.info("game_updated", game_id=game.id, name=game.name)
    return game


@router.delete("/games/{game_id}", status_code=204)
def delete_game(game_id: str) -> Response:
    deleted = storage.delete_game(game_id)
    if not deleted:
        log.warning("game_not_found", game_id=game_id, action="delete")
        raise HTTPException(status_code=404, detail="Game not found")
    log.info("game_deleted", game_id=game_id)
    return Response(status_code=204)
