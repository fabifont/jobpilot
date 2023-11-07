from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from httpx import AsyncClient
from pydantic import BaseModel

if TYPE_CHECKING:
    from jobpilot.models.job import Job


class ScraperInput(BaseModel):
    keywords: str
    location: str
    limit: int

    def __hash__(self) -> int:
        return hash((self.keywords, self.location, self.limit))


class BaseScraper(ABC):
    def __init__(self) -> None:
        super().__init__()
        self._client = AsyncClient()

    @abstractmethod
    async def scrape(self, scraper_input: ScraperInput) -> list[Job]: ...
