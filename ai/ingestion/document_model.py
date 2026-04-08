from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class Document:
    path: str
    title: str
    content: str
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)