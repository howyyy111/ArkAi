from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List

class ApiRequest(BaseModel):
    userId: Optional[str] = None
    sessionId: Optional[str] = None
    idToken: Optional[str] = None
    email: Optional[str] = None
    resetIdentity: Optional[bool] = False
    resetSession: Optional[bool] = False

class ChatDeleteRequest(ApiRequest):
    targetSessionId: Optional[str] = ""

class DiagnosticStartRequest(ApiRequest):
    topic: Optional[str] = ""
    assessmentType: Optional[str] = "diagnostic"
    level: Optional[str] = "beginner"
    goal: Optional[str] = ""
    availableTime: Optional[int] = None
    learningStyle: Optional[str] = "balanced"
    questionCount: Optional[int] = 5

class DiagnosticSubmitRequest(ApiRequest):
    assessmentId: Optional[str] = ""
    answers: Optional[Dict[str, Any]] = None
    confidenceByQuestion: Optional[Dict[str, Any]] = None

class RoadmapGenerateRequest(ApiRequest):
    topic: Optional[str] = ""
    goal: Optional[str] = ""
    level: Optional[str] = ""
    availableTime: Optional[int] = None
    deadlineDays: Optional[int] = 14
    startDate: Optional[str] = ""
    saveToCalendar: Optional[bool] = False
    calendarStartTime: Optional[str] = "09:00"
    timezone: Optional[str] = ""
    forceRebuild: Optional[bool] = False
    revisionReason: Optional[str] = ""

class RoadmapSessionUpdateRequest(ApiRequest):
    phaseId: Optional[str] = ""
    sessionId: Optional[str] = ""
    status: Optional[str] = ""

class RoadmapDeleteSavedRequest(ApiRequest):
    roadmapId: Optional[str] = ""

class SavedRoadmapSessionUpdateRequest(RoadmapDeleteSavedRequest):
    phaseId: Optional[str] = ""
    sessionId: Optional[str] = ""
    status: Optional[str] = ""

class RoadmapSaveCalendarRequest(ApiRequest):
    title: Optional[str] = ""
    focus: Optional[str] = ""
    phaseTitle: Optional[str] = ""
    phaseGoal: Optional[str] = ""
    startTime: Optional[str] = ""
    endTime: Optional[str] = ""

class MaterialsUploadRequest(ApiRequest):
    name: Optional[str] = ""
    mimeType: Optional[str] = ""
    dataBase64: Optional[str] = ""
    pastedText: Optional[str] = ""

class MaterialsTutorRequest(ApiRequest):
    query: Optional[str] = ""
    materialIds: Optional[List[str]] = None

class MaterialsMockTestRequest(ApiRequest):
    materialIds: Optional[List[str]] = None
    topic: Optional[str] = ""
    level: Optional[str] = "beginner"
    goal: Optional[str] = ""
    questionCount: Optional[int] = 5
    structure: Optional[str] = ""
    sampleStyle: Optional[str] = ""

class MaterialDeleteRequest(ApiRequest):
    materialId: Optional[str] = ""

class HistoryDeleteRequest(ApiRequest):
    recordId: Optional[str] = ""

class ReportSaveDocRequest(ApiRequest):
    title: Optional[str] = ""

class AssessmentSaveDocRequest(ApiRequest):
    assessmentId: Optional[str] = ""
    title: Optional[str] = ""

class ChatRequest(ApiRequest):
    message: Optional[str] = ""
    timezone: Optional[str] = ""
    selectedMaterialIds: Optional[List[str]] = None
    inputMode: Optional[str] = ""
    temporaryAttachments: Optional[List[Dict[str, Any]]] = None
    clientMessages: Optional[List[Dict[str, Any]]] = None

class GoogleConnectRequest(ApiRequest):
    forceReconnect: Optional[bool] = False

class GoogleTokenConnectRequest(ApiRequest):
    accessToken: Optional[str] = ""
    expiresIn: Optional[int] = None
