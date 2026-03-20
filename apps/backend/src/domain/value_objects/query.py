import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Query:
    raw: str
    normalized: str
    
    @classmethod
    def from_raw(cls, raw: str) -> "Query":
        normalized = cls._normalize(raw)
        return cls(raw=raw.strip(), normalized=normalized)
    
    @staticmethod
    def _normalize(text: str) -> str:
        text = text.strip()
        text = text.lower()
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s\-]', '', text)
        return text.strip()
    
    def __hash__(self) -> int:
        return hash(self.normalized)
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Query):
            return False
        return self.normalized == other.normalized
