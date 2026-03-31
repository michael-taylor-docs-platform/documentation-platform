from dataclasses import dataclass
from typing import List


@dataclass
class Document:
    path: str
    title: str
    content: str
    tags: List[str] = None