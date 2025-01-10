from dataclasses import dataclass, asdict
from typing import Optional
from datetime import datetime

@dataclass
class GateEntry:
    entry_id: str  # String ID with format YYYYMMDDXXXX
    name: str
    contact_no: str
    vehicle_no: Optional[str] = None
    destination: str
    reason: str
    in_time: datetime
    out_time: Optional[datetime] = None
    vehicle_type: str  # e.g., "car", "bike", "none"
    remarks: Optional[str] = None

    def to_dict(self) -> dict:
        # Convert datetime to string for MongoDB compatibility
        gate_entry_dict = asdict(self)
        gate_entry_dict["in_time"] = self.in_time.isoformat()
        if self.out_time:
            gate_entry_dict["out_time"] = self.out_time.isoformat()
        return gate_entry_dict

