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
    geoid: str = "" # it's a specific linkedin parameter to localize ip, using an italian geoid you can write country and city names in Italian
    out_language: str = "en_US"
    workplace: str = "" # f_WT it's to filter for workplace type: "1" for On-site, "2" for Remote , "3" for Hybrid, "" for all types
    experience: str = "" # f_E it's to filter for senority type: "1" for Internship, "2" for Entry level, "3" for Associate, "4" for Mid-Senior, "5" for Director, "6" for Executive, "" for all types

    def __hash__(self) -> int:
        return hash((self.keywords, self.location, self.limit, self.geoid, self.out_language, self.workplace, self.experience))


class BaseScraper(ABC):
    def __init__(self) -> None:
        super().__init__()
        self._client = AsyncClient()

    @abstractmethod
    async def scrape(self, scraper_input: ScraperInput) -> list[Job]: ...
