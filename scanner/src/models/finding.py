from dataclasses import dataclass, field
from typing import Optional
import uuid


@dataclass
class Finding:
    rule_id: str
    severity: str
    resource_name: str
    resource_type: str
    scan_job_id: str
    line_number: int = 0
    code_snippet: str = ""
    finding_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ai_explanation: str = ""
    ai_fix_code: str = ""
    dismissed: bool = False
    dismissed_at: Optional[str] = None

    def to_dynamodb_item(self) -> dict:
        item = {
            "scan_job_id": self.scan_job_id,
            "finding_id": self.finding_id,
            "rule_id": self.rule_id,
            "severity": self.severity,
            "resource_name": self.resource_name,
            "resource_type": self.resource_type,
            "line_number": self.line_number,
            "code_snippet": self.code_snippet[:500],
            "ai_explanation": self.ai_explanation,
            "ai_fix_code": self.ai_fix_code,
            "dismissed": self.dismissed,
        }
        if self.dismissed_at:
            item["dismissed_at"] = self.dismissed_at
        return item

    @classmethod
    def from_dynamodb_item(cls, item: dict) -> "Finding":
        return cls(
            scan_job_id=item["scan_job_id"],
            finding_id=item["finding_id"],
            rule_id=item["rule_id"],
            severity=item["severity"],
            resource_name=item["resource_name"],
            resource_type=item["resource_type"],
            line_number=int(item.get("line_number", 0)),
            code_snippet=item.get("code_snippet", ""),
            ai_explanation=item.get("ai_explanation", ""),
            ai_fix_code=item.get("ai_fix_code", ""),
            dismissed=item.get("dismissed", False),
            dismissed_at=item.get("dismissed_at"),
        )
