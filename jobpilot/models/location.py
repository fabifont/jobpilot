from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class Country(Enum):
    AUSTRIA = ("austria", "at")
    BAHRAIN = ("bahrain", "bh")
    BELGIUM = ("belgium", "be")
    BRAZIL = ("brazil", "br")
    CANADA = ("canada", "ca")
    CHILE = ("chile", "cl")
    CHINA = ("china", "cn")
    COLOMBIA = ("colombia", "col")
    COSTARICA = ("costa rica", "cr")
    CZECHREPUBLIC = ("czech republic", "cz")
    DENMARK = ("denmark", "dk")
    ECUADOR = ("ecuador", "ec")
    EGYPT = ("egypt", "eg")
    FINLAND = ("finland", "fi")
    FRANCE = ("france", "fr")
    GERMANY = ("germany", "de")
    GREECE = ("greece", "gr")
    HONGKONG = ("hong kong", "hk")
    HUNGARY = ("hungary", "hu")
    INDIA = ("india", "in")
    INDONESIA = ("indonesia", "id")
    IRELAND = ("ireland", "ie")
    ISRAEL = ("israel", "il")
    ITALY = ("italy", "it")
    JAPAN = ("japan", "jp")
    KUWAIT = ("kuwait", "kw")
    LUXEMBOURG = ("luxembourg", "lu")
    MALAYSIA = ("malaysia", "my")
    MEXICO = ("mexico", "mx")
    MOROCCO = ("morocco", "ma")
    NETHERLANDS = ("netherlands", "nl")
    NEWZEALAND = ("new zealand", "nz")
    NIGERIA = ("nigeria", "ng")
    NORWAY = ("norway", "no")
    OMAN = ("oman", "om")
    PAKISTAN = ("pakistan", "pk")
    PANAMA = ("panama", "pa")
    PERU = ("peru", "pe")
    PHILIPPINES = ("philippines", "ph")
    POLAND = ("poland", "pl")
    PORTUGAL = ("portugal", "pt")
    QATAR = ("qatar", "qa")
    ROMANIA = ("romania", "ro")
    SAUDIARABIA = ("saudi arabia", "sa")
    SINGAPORE = ("singapore", "sg")
    SOUTHAFRICA = ("south africa", "za")
    SOUTHKOREA = ("south korea", "kr")
    SPAIN = ("spain", "es")
    SWEDEN = ("sweden", "se")
    SWITZERLAND = ("switzerland", "ch")
    TAIWAN = ("taiwan", "tw")
    THAILAND = ("thailand", "th")
    TURKEY = ("turkey", "tr")
    UKRAINE = ("ukraine", "ua")
    UNITEDARABEMIRATES = ("united arab emirates", "ae")
    UK = ("united kingdom", "uk")
    USA = ("united states", "us", "usa")
    URUGUAY = ("uruguay", "uy")
    VENEZUELA = ("venezuela", "ve")
    VIETNAM = ("vietnam", "vn")
    WORLDWIDE = ("worldwide", "ww")

    @staticmethod
    def from_alias(alias: str) -> Country:
        if alias in _ALIAS_TO_COUNTRY:
            return _ALIAS_TO_COUNTRY[alias]
        msg = f"country {alias} not found; please open an issue"
        raise ValueError(msg)

    def __str__(self) -> str:
        return self.value[0]


_ALIAS_TO_COUNTRY: dict[str, Country] = {}
for country in Country:
    for alias in country.value:
        _ALIAS_TO_COUNTRY[alias] = country


class Location(BaseModel):
    country: Country
    city: str | None
    region: str | None

    def __str__(self) -> str:
        city = f"{self.city}, " if self.city else ""
        region = f"{self.region}, " if self.region else ""
        return f"{city}{region}{self.country.value[0]}"

    def __hash__(self) -> int:
        return hash(str(self))
