from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


# --- Document Parsing Models ---

class DocumentSection(BaseModel):
    heading: str
    content: str

class ParsedDocument(BaseModel):
    doc_id: str
    title: str
    version: Optional[str] = None
    sections: List[DocumentSection] = Field(default_factory=list)
    full_text: str = ""


# --- Agent 1: Requirement Extraction ---

class Requirement(BaseModel):
    id: str
    text: str
    category: str = ""  # functional, non_functional, business_rule

class ExtractedRequirements(BaseModel):
    functional: List[Requirement] = Field(default_factory=list)
    non_functional: List[Requirement] = Field(default_factory=list)
    business_rules: List[Requirement] = Field(default_factory=list)


# --- Agent 2: User Stories ---

class UserStory(BaseModel):
    requirement_id: str
    role: str
    action: str
    benefit: str
    story: str  # "As a {role}, I want to {action} so that {benefit}"


# --- Agent 3: Stakeholders ---

class Stakeholder(BaseModel):
    name: str
    role: str
    description: str


# --- Agent 4: Priority ---

class PrioritizedRequirement(BaseModel):
    requirement_id: str
    text: str
    priority: str  # must_have, should_have, nice_to_have
    reason: str


# --- Agent 5: Ambiguity ---

class AmbiguityIssue(BaseModel):
    requirement_id: str
    original_text: str
    issue: str
    suggestion: str


# --- Agent 6: Missing Requirements ---

class MissingRequirement(BaseModel):
    category: str
    suggestion: str
    reason: str


# --- Agent 7: Conflicts ---

class ConflictItem(BaseModel):
    requirement_a_id: str
    requirement_a_text: str
    requirement_b_id: str
    requirement_b_text: str
    conflict_description: str


# --- Agent 8: Dependencies ---

class DependencyLink(BaseModel):
    from_requirement: str
    to_requirement: str
    relationship: str  # depends_on, blocks, related_to


# --- Agent 9: Summary ---

class AnalysisSummary(BaseModel):
    executive_summary: str
    developer_summary: str
    business_summary: str
    quality_score: int = Field(ge=0, le=100, description="Requirement quality 0-100")


# --- Agent 10: Final Output ---

class AnalysisResult(BaseModel):
    project_id: str
    title: str
    requirements: ExtractedRequirements
    user_stories: List[UserStory] = Field(default_factory=list)
    stakeholders: List[Stakeholder] = Field(default_factory=list)
    priorities: List[PrioritizedRequirement] = Field(default_factory=list)
    ambiguities: List[AmbiguityIssue] = Field(default_factory=list)
    missing_requirements: List[MissingRequirement] = Field(default_factory=list)
    conflicts: List[ConflictItem] = Field(default_factory=list)
    dependencies: List[DependencyLink] = Field(default_factory=list)
    summary: Optional[AnalysisSummary] = None


# --- Job Tracking ---

class AnalysisJob(BaseModel):
    job_id: str
    project_id: str
    status: str = "pending"  # pending, running, completed, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Optional[AnalysisResult] = None
