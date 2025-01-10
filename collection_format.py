from dataclasses import dataclass, asdict
from typing import Optional
from datetime import datetime

@dataclass
class GateEntry:
    entry_id: str  # String ID with format YYYYMMDDXXXX
    name: str
    contact_no: str
    destination: str
    reason: str
    in_time: datetime
    vehicle_type: str  # e.g., "car", "bike", "none"
    vehicle_no: Optional[str] = None
    out_time: Optional[datetime] = None
    remarks: Optional[str] = None

    def to_dict(self) -> dict:
        # Convert datetime to string for MongoDB compatibility
        gate_entry_dict = asdict(self)
        gate_entry_dict["in_time"] = self.in_time.isoformat()
        if self.out_time:
            gate_entry_dict["out_time"] = self.out_time.isoformat()
        return gate_entry_dict

@dataclass
class User:
    username: str
    password: str
    shift: Optional[str]
    role: str

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class Session:
    username: str   
    password: str
    session_login_time: datetime
    session_logout_time: Optional[datetime]
    ip_address: str
    def to_dict(self) -> dict:
        # Convert datetime to string for MongoDB compatibility
        session_dict = asdict(self)
        session_dict["session_login_time"] = self.session_login_time.isoformat()
        if self.session_logout_time:
            session_dict["session_logout_time"] = self.session_logout_time.isoformat()
        return session_dict