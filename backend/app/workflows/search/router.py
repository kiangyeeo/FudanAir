from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db
from app.workflows.search.schemas import (
    FlightSearchRequest,
    FlightSearchResponse,
    TransitCandidate,
)
from app.workflows.search.service import SearchService


router = APIRouter(tags=["search"])


@router.post("/flights", response_model=FlightSearchResponse)
def search_flights(
    payload: FlightSearchRequest,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return SearchService(db).search_flights(payload)


@router.post("/transit", response_model=list[TransitCandidate])
def search_transit(
    payload: FlightSearchRequest,
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    return SearchService(db).search_transit(payload)
