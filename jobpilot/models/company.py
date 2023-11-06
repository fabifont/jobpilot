from pydantic import BaseModel


class Company(BaseModel):
    name: str
    link: str

    def __hash__(self) -> int:
        return hash(self.link)
