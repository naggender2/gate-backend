from dataclasses import dataclass, asdict, field
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
    no_driver: Optional[int] = 0
    no_student: Optional[int] = 0
    no_visitor: Optional[int] = 0
    no_person: Optional[int] = field(init=False)
    remarks: Optional[str] = None

    def __post_init__(self):
        # Automatically calculate no_person after initialization
        self.update_no_person()
        
    def to_dict(self) -> dict:
        # Convert datetime to string for MongoDB compatibility
        gate_entry_dict = asdict(self)
        gate_entry_dict["in_time"] = self.in_time.strftime('%d-%m-%Y %a %H:%M:%S')
        if self.out_time:
            gate_entry_dict["out_time"] = self.out_time.strftime('%d-%m-%Y %a %H:%M:%S')
        return gate_entry_dict

    def update_no_person(self):
    # Automatically update the no_person based on no_driver, no_student, and no_visitor counts
        self.no_person = int(self.no_driver) + int(self.no_student) + int(self.no_visitor)

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