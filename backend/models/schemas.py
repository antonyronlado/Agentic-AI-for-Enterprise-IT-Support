from typing import Optional, Any, List
from pydantic import BaseModel, Field, ConfigDict


class TicketCreate(BaseModel):
    title: str
    description: str
    userId: str
    userEmail: str


class TicketFeedback(BaseModel):
    rating: str
    comment: Optional[str] = None


class TicketOut(BaseModel):
    id: str = Field(alias="_id")
    title: str
    description: str
    status: str
    priority: str
    category: str
    createdAt: int
    updatedAt: int
    userId: str
    userEmail: str
    history: List[dict]
    analysis: Optional[Any] = None
    riskAssessment: Optional[Any] = None
    resolution: Optional[Any] = None
    employee_response: Optional[str] = None
    admin_response: Optional[str] = None
    risk_level: Optional[str] = None
    confidence_score: Optional[int] = None
    low_confidence: Optional[bool] = None
    ai_explanation: Optional[Any] = None
    confidence_map: Optional[Any] = None
    duplicate_of: Optional[str] = None
    affected_users: Optional[List[str]] = None
    linked_count: Optional[int] = None
    dedup_confidence: Optional[float] = None
    master_incident_id: Optional[str] = None
    remediation_action: Optional[Any] = None
    feedback: Optional[Any] = None
    attachments: Optional[List[str]] = None

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class CopilotRequest(BaseModel):
    ticket_id: str
    title: str
    description: str
    analysis: Optional[Any] = None
    risk: Optional[Any] = None


class RemediationApproveRequest(BaseModel):
    approved_by: str


class FeedbackRequest(BaseModel):
    rating: str
    comment: Optional[str] = None


class UploadAnalysisResult(BaseModel):
    extracted_text: str
    detected_errors: List[str]
    probable_cause: str
    confidence: int
    file_type: str


class IncidentCluster(BaseModel):
    id: str
    title: str
    probable_root_cause: str
    affected_ticket_ids: List[str]
    affected_user_count: int
    category: str
    severity: str
    cluster_confidence: int
    created_at: int
    status: str


class KBArticle(BaseModel):
    id: str = Field(alias="_id")
    title: str
    problem_statement: str
    solution_steps: List[str]
    tags: List[str]
    related_ticket_ids: List[str]
    source_ticket_id: str
    effectiveness_score: Optional[float] = None
    positive_feedback: int = 0
    negative_feedback: int = 0
    created_at: int
    updated_at: int

    model_config = ConfigDict(populate_by_name=True)
