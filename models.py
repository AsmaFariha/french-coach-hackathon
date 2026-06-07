from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class Page:
    id: str
    user_id: str
    title: str
    date: date
    raw_text: str
    annotations: dict = field(default_factory=dict)
    created_at: Optional[datetime] = None


@dataclass
class Exercise:
    id: str
    user_id: str
    page_id: Optional[str]
    kind: str          # 'text' | 'dialogue' | 'visual' | 'pronunciation'
    prompt: Optional[str] = None
    model_answer: Optional[str] = None
    content: dict = field(default_factory=dict)
    created_at: Optional[datetime] = None
