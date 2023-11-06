from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from jobpilot.models import Company, Location


class EmploymentType(Enum):
    FULLTIME = (
        "fulltime",
        "períodointegral",
        "estágio/trainee",
        "cunormăîntreagă",
        "tiempocompleto",
        "vollzeit",
        "voltijds",
        "tempointegral",
        "全职",
        "plnýúvazek",
        "fuldtid",
        "دوامكامل",
        "kokopäivätyö",
        "tempsplein",
        "vollzeit",
        "πλήρηςαπασχόληση",
        "teljesmunkaidő",
        "tempopieno",
        "tempsplein",
        "heltid",
        "jornadacompleta",
        "pełnyetat",
        "정규직",
        "100%",
        "全職",
        "งานประจำ",
        "tamzamanli",
        "повназайнятість",
        "toànthờigian",
    )
    PARTTIME = ("parttime", "teilzeit", "částečnýúvazek", "deltid")
    INTERNSHIP = (
        "internship",
        "prácticas",
        "ojt(onthejobtraining)",
        "praktikum",
        "praktik",
    )
    PER_DIEM = ("perdiem",)
    NIGHTS = ("nights",)
    OTHER = ("other",)
    SUMMER = ("summer",)
    VOLUNTEER = ("volunteer",)
    SELFEMPLOYED = ("contract",)

    @staticmethod
    def from_alias(alias: str) -> EmploymentType:
        if alias in _ALIAS_TO_EMPLOYMENT_TYPE:
            return _ALIAS_TO_EMPLOYMENT_TYPE[alias]
        msg = f"employment_type {alias} not found; please open an issue"
        raise ValueError(msg)

    def __str__(self) -> str:
        return self.value[0]


_ALIAS_TO_EMPLOYMENT_TYPE: dict[str, EmploymentType] = {}
for employment_type in EmploymentType:
    for alias in employment_type.value:
        _ALIAS_TO_EMPLOYMENT_TYPE[alias] = employment_type


class JobDetails(BaseModel):
    description: str | None = None
    employment_type: EmploymentType | None = None
    seniority_level: str | None = None
    job_function: str | None = None
    industries: str | None = None


class Job(BaseModel):
    title: str
    link: str
    location: Location
    company: Company
    details: JobDetails | None = None

    def __hash__(self) -> int:
        return hash(self.link)
