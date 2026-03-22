"""Pydantic v2 schemas for Estate Executor OS API."""

from .ai import (
    AIAnomalyResponse,
    AIClassifyResponse,
    AIExtractResponse,
    AILetterDraftRequest,
    AILetterDraftResponse,
    AISuggestTasksResponse,
    Anomaly,
    TaskSuggestion,
)
from .assets import (
    AssetCreate,
    AssetDetailResponse,
    AssetLinkDocument,
    AssetListItem,
    AssetListResponse,
    AssetUpdate,
    AssetValuation,
    EntityBrief,
    ValuationEntry,
)
from .auth import CurrentUser, FirmMembershipBrief, TokenPayload
from .common import APIResponse, ErrorDetail, PaginationMeta, PaginationParams
from .communications import (
    CommunicationCreate,
    CommunicationListResponse,
    CommunicationResponse,
    DisputeFlagCreate,
)
from .deadlines import (
    CalendarDeadline,
    CalendarMonth,
    CalendarResponse,
    DeadlineCreate,
    DeadlineListResponse,
    DeadlineResponse,
    DeadlineUpdate,
    TaskBrief,
)
from .documents import (
    DocumentConfirmType,
    DocumentRegister,
    DocumentRequestCreate,
    DocumentResponse,
    DocumentUploadURL,
)
from .entities import (
    AssetBrief,
    EntityCreate,
    EntityMapResponse,
    EntityResponse,
    EntityUpdate,
)
from .events import EventListResponse, EventResponse
from .firms import FirmCreate, FirmListResponse, FirmResponse, FirmUpdate
from .matters import (
    AssetSummary,
    MatterCreate,
    MatterDashboard,
    MatterListResponse,
    MatterResponse,
    MatterUpdate,
    TaskSummary,
)
from .stakeholders import (
    StakeholderInvite,
    StakeholderListResponse,
    StakeholderResponse,
    StakeholderUpdate,
)
from .tasks import (
    DocumentBrief,
    TaskComplete,
    TaskCreate,
    TaskGenerateRequest,
    TaskListResponse,
    TaskResponse,
    TaskUpdate,
    TaskWaive,
)

__all__ = [
    # Common
    "APIResponse",
    "ErrorDetail",
    "PaginationMeta",
    "PaginationParams",
    # Auth
    "CurrentUser",
    "FirmMembershipBrief",
    "TokenPayload",
    # Firms
    "FirmCreate",
    "FirmListResponse",
    "FirmResponse",
    "FirmUpdate",
    # Matters
    "AssetSummary",
    "MatterCreate",
    "MatterDashboard",
    "MatterListResponse",
    "MatterResponse",
    "MatterUpdate",
    "TaskSummary",
    # Stakeholders
    "StakeholderInvite",
    "StakeholderListResponse",
    "StakeholderResponse",
    "StakeholderUpdate",
    # Tasks
    "DocumentBrief",
    "TaskComplete",
    "TaskCreate",
    "TaskGenerateRequest",
    "TaskListResponse",
    "TaskResponse",
    "TaskUpdate",
    "TaskWaive",
    # Assets
    "AssetCreate",
    "AssetDetailResponse",
    "AssetLinkDocument",
    "AssetListItem",
    "AssetListResponse",
    "AssetUpdate",
    "AssetValuation",
    "EntityBrief",
    "ValuationEntry",
    # Entities
    "AssetBrief",
    "EntityCreate",
    "EntityMapResponse",
    "EntityResponse",
    "EntityUpdate",
    # Documents
    "DocumentConfirmType",
    "DocumentRegister",
    "DocumentRequestCreate",
    "DocumentResponse",
    "DocumentUploadURL",
    # Deadlines
    "CalendarDeadline",
    "CalendarMonth",
    "CalendarResponse",
    "DeadlineCreate",
    "DeadlineListResponse",
    "DeadlineResponse",
    "DeadlineUpdate",
    "TaskBrief",
    # Communications
    "CommunicationCreate",
    "CommunicationListResponse",
    "CommunicationResponse",
    "DisputeFlagCreate",
    # Events
    "EventListResponse",
    "EventResponse",
    # AI
    "AIAnomalyResponse",
    "AIClassifyResponse",
    "AIExtractResponse",
    "AILetterDraftRequest",
    "AILetterDraftResponse",
    "AISuggestTasksResponse",
    "Anomaly",
    "TaskSuggestion",
]
