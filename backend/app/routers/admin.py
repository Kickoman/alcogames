from fastapi import APIRouter, Depends, HTTPException, Response

from .. import storage
from ..deps import require_admin_token
from ..models import Game, GameCreate, GameUpdate

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin_token)],
)


@router.post("/games", response_model=Game, status_code=201)
def create_game(data: GameCreate) -> Game:
    return storage.create_game(data)


@router.put("/games/{game_id}", response_model=Game)
def update_game(game_id: str, data: GameUpdate) -> Game:
    game = storage.update_game(game_id, data)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


@router.delete("/games/{game_id}", status_code=204)
def delete_game(game_id: str) -> Response:
    deleted = storage.delete_game(game_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Game not found")
    return Response(status_code=204)
