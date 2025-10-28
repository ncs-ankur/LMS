from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import List, Optional


class Role(Enum):
    MEMBER = auto()
    LIBRARIAN = auto()
    ADMIN = auto()


@dataclass
class User:
    user_id: str
    name: str
    email: str
    role: Role = Role.MEMBER
    active: bool = True

    def can_borrow(self) -> bool:
        return self.active and self.role in (Role.MEMBER, Role.LIBRARIAN, Role.ADMIN)


@dataclass
class Book:
    book_id: str
    title: str
    author: str
    isbn: str
    tags: List[str] = field(default_factory=list)


class CopyStatus(Enum):
    AVAILABLE = auto()
    CHECKED_OUT = auto()
    LOST = auto()
    MAINTENANCE = auto()


@dataclass
class Copy:
    copy_id: str
    book_id: str
    status: CopyStatus = CopyStatus.AVAILABLE


@dataclass
class Loan:
    loan_id: str
    user_id: str
    copy_id: str
    checkout_at: datetime
    due_at: datetime
    returned_at: Optional[datetime] = None

    def is_overdue(self, now: Optional[datetime] = None) -> bool:
        now = now or datetime.utcnow()
        return self.returned_at is None and now > self.due_at

    def mark_returned(self, when: Optional[datetime] = None) -> None:
        self.returned_at = when or datetime.utcnow()


class ReservationStatus(Enum):
    ACTIVE = auto()
    FULFILLED = auto()
    CANCELLED = auto()


@dataclass
class Reservation:
    reservation_id: str
    user_id: str
    book_id: str
    placed_at: datetime
    status: ReservationStatus = ReservationStatus.ACTIVE


@dataclass
class Fine:
    fine_id: str
    user_id: str
    amount_cents: int
    reason: str
    created_at: datetime
    paid_at: Optional[datetime] = None

    def pay(self, when: Optional[datetime] = None) -> None:
        self.paid_at = when or datetime.utcnow()

    @property
    def is_paid(self) -> bool:
        return self.paid_at is not None

