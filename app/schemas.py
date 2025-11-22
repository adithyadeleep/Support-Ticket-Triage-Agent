from pydantic import BaseModel
from typing import List
from enum import Enum

class SeverityLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

class TriageSchema(BaseModel):
    summary: str
    category: str
    severity: SeverityLevel
    key_entities: List[str]
    reasoning: str

class KBEntry(BaseModel):
    id: str
    title: str
    category: str
    symptoms: List[str]
    recommended_action: str

class TriageResponse(BaseModel):
    analysis: TriageSchema
    similar_issues: List[KBEntry]
    suggested_action: str
    known_issue: bool
