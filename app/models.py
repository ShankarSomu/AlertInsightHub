from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class SeverityLevel(str, Enum):
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class Alert(BaseModel):
    id: str
    account_id: str
    service: str
    resource_id: str
    alert_type: str
    severity: SeverityLevel
    timestamp: datetime
    message: Optional[str] = None
    region: str = "us-east-1"

class AlertDetail(BaseModel):
    id: str
    account_id: str
    service: str
    resource_id: str
    alert_type: str
    severity: SeverityLevel
    timestamp: datetime
    message: Optional[str] = None
    remediation: Optional[str] = None
    region: str = "us-east-1"

class AlertSummary(BaseModel):
    account_id: str
    service: str
    region: str = "us-east-1"
    total_alerts: int
    medium_alerts: int = 0
    high_alerts: int = 0
    critical_alerts: int = 0

class ResourceSummary(BaseModel):
    resource_id: str
    service: str
    region: str = "us-east-1"
    total_alerts: int
    medium_alerts: int = 0
    high_alerts: int = 0
    critical_alerts: int = 0

class AlertTypeSummary(BaseModel):
    alert_type: str
    total_alerts: int
    medium_alerts: int = 0
    high_alerts: int = 0
    critical_alerts: int = 0