from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional

from .domain import (
    User,
    Book,
    Copy,
    CopyStatus,
    Loan,
    Reservation,
    ReservationStatus,
    Fine,
)


class UserRepo:
    def __init__(self) -> None:
        self._users: Dict[str, User] = {}

    def add(self, user: User) -> None:
        self._users[user.user_id] = user

    def get(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)

    def list_all(self) -> List[User]:
        return list(self._users.values())


class BookRepo:
    def __init__(self) -> None:
        self._books: Dict[str, Book] = {}
        self._copies: Dict[str, Copy] = {}

    # books
    def add_book(self, book: Book) -> None:
        self._books[book.book_id] = book

    def get_book(self, book_id: str) -> Optional[Book]:
        return self._books.get(book_id)

    def list_books(self) -> List[Book]:
        return list(self._books.values())

    def search(self, text: str) -> List[Book]:
        t = text.lower().strip()

        def matches(b: Book) -> bool:
            return (
                t in b.title.lower()
                or t in b.author.lower()
                or t in b.isbn.lower()
                or any(t in tag.lower() for tag in b.tags)
            )

        return [b for b in self._books.values() if matches(b)]

    # copies
    def add_copy(self, copy: Copy) -> None:
        self._copies[copy.copy_id] = copy

    def get_copy(self, copy_id: str) -> Optional[Copy]:
        return self._copies.get(copy_id)

    def list_copies_for_book(self, book_id: str) -> List[Copy]:
        return [c for c in self._copies.values() if c.book_id == book_id]

    def list_available_copy_ids(self, book_id: str) -> List[str]:
        return [
            c.copy_id
            for c in self.list_copies_for_book(book_id)
            if c.status == CopyStatus.AVAILABLE
        ]


class LoanRepo:
    def __init__(self) -> None:
        self._loans: Dict[str, Loan] = {}

    def add(self, loan: Loan) -> None:
        self._loans[loan.loan_id] = loan

    def get(self, loan_id: str) -> Optional[Loan]:
        return self._loans.get(loan_id)

    def list_by_user(self, user_id: str) -> List[Loan]:
        return [l for l in self._loans.values() if l.user_id == user_id]

    def list_active_by_copy(self, copy_id: str) -> List[Loan]:
        return [
            l
            for l in self._loans.values()
            if l.copy_id == copy_id and l.returned_at is None
        ]

    def list_overdue(self, now: Optional[datetime] = None) -> List[Loan]:
        return [l for l in self._loans.values() if l.is_overdue(now)]


class ReservationRepo:
    def __init__(self) -> None:
        self._reservations: Dict[str, Reservation] = {}

    def add(self, r: Reservation) -> None:
        self._reservations[r.reservation_id] = r

    def list_active_for_book(self, book_id: str) -> List[Reservation]:
        items = [
            r
            for r in self._reservations.values()
            if r.book_id == book_id and r.status == ReservationStatus.ACTIVE
        ]
        # FIFO by placed_at
        return sorted(items, key=lambda r: r.placed_at)

    def list_by_user(self, user_id: str) -> List[Reservation]:
        return [r for r in self._reservations.values() if r.user_id == user_id]


class FineRepo:
    def __init__(self) -> None:
        self._fines: Dict[str, Fine] = {}

    def add(self, fine: Fine) -> None:
        self._fines[fine.fine_id] = fine

    def list_unpaid_by_user(self, user_id: str) -> List[Fine]:
        return [f for f in self._fines.values() if f.user_id == user_id and not f.is_paid]

    def total_unpaid_cents(self, user_id: str) -> int:
        return sum(f.amount_cents for f in self.list_unpaid_by_user(user_id))

