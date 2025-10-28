"""
Project: BookHive LMS
Single-file demo Library Management System with clear modules-in-a-file layout
for diagrams, RAG, or quick prototyping.

Layers (all in this file for simplicity):
- domain: Entities & value objects (User, Book, Copy, Loan, Reservation, Fine)
- services: Application logic (CatalogService, CirculationService, UserService, FineService)
- infra: In-memory repositories (UserRepo, BookRepo, LoanRepo, ReservationRepo, FineRepo)
- api: A tiny "facade" LibrarySystem with example usage in __main__

Notes for diagramming tools:
- Class relationships: User -> Loan/Reservation/Fine; Book -> Copy -> Loan
- Services depend on Repos, not vice versa.
- LibrarySystem composes all services.

This is *dummy* code: not production-ready; no persistence, auth, or concurrency.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Dict, List, Optional, Iterable
import itertools
import uuid


# =========================
# domain (entities & enums)
# =========================

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


# =========================
# infra (in-memory repos)
# =========================

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
        return [c.copy_id for c in self.list_copies_for_book(book_id) if c.status == CopyStatus.AVAILABLE]


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
        return [l for l in self._loans.values() if l.copy_id == copy_id and l.returned_at is None]

    def list_overdue(self, now: Optional[datetime] = None) -> List[Loan]:
        return [l for l in self._loans.values() if l.is_overdue(now)]


class ReservationRepo:
    def __init__(self) -> None:
        self._reservations: Dict[str, Reservation] = {}

    def add(self, r: Reservation) -> None:
        self._reservations[r.reservation_id] = r

    def list_active_for_book(self, book_id: str) -> List[Reservation]:
        items = [r for r in self._reservations.values() if r.book_id == book_id and r.status == ReservationStatus.ACTIVE]
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


# =========================
# services (application)
# =========================

def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


class UserService:
    def __init__(self, users: UserRepo, fines: FineRepo) -> None:
        self.users = users
        self.fines = fines

    def register_user(self, name: str, email: str, role: Role = Role.MEMBER) -> User:
        u = User(user_id=_new_id("usr"), name=name, email=email, role=role)
        self.users.add(u)
        return u

    def get(self, user_id: str) -> Optional[User]:
        return self.users.get(user_id)

    def block_if_unpaid_fines(self, user: User) -> bool:
        # dummy policy: > $10 unpaid blocks borrowing
        cents = self.fines.total_unpaid_cents(user.user_id)
        if cents > 1000:
            user.active = False
            return True
        return False


class CatalogService:
    def __init__(self, books: BookRepo) -> None:
        self.books = books

    def add_book_with_copies(self, title: str, author: str, isbn: str, tags: Optional[List[str]] = None, copies: int = 1) -> Book:
        b = Book(book_id=_new_id("bk"), title=title, author=author, isbn=isbn, tags=tags or [])
        self.books.add_book(b)
        for _ in range(copies):
            self.books.add_copy(Copy(copy_id=_new_id("cpy"), book_id=b.book_id))
        return b

    def search(self, text: str) -> List[Book]:
        return self.books.search(text)

    def available_copies(self, book_id: str) -> List[str]:
        return self.books.list_available_copy_ids(book_id)


class FineService:
    def __init__(self, fines: FineRepo) -> None:
        self.fines = fines

    def assess_overdue_fine(self, loan: Loan, now: Optional[datetime] = None) -> Optional[Fine]:
        """Dummy rule: $0.50/day overdue."""
        now = now or datetime.utcnow()
        if loan.returned_at and loan.returned_at > loan.due_at:
            days = (loan.returned_at.date() - loan.due_at.date()).days
        elif loan.is_overdue(now):
            days = (now.date() - loan.due_at.date()).days
        else:
            return None

        amount_cents = max(0, days) * 50
        if amount_cents <= 0:
            return None
        f = Fine(
            fine_id=_new_id("fine"),
            user_id=loan.user_id,
            amount_cents=amount_cents,
            reason=f"Overdue {days} day(s) for loan {loan.loan_id}",
            created_at=now,
        )
        self.fines.add(f)
        return f

    def pay_all(self, user_id: str) -> int:
        total = 0
        for f in self.fines.list_unpaid_by_user(user_id):
            total += f.amount_cents
            f.pay()
        return total


class CirculationService:
    def __init__(self, users: UserRepo, books: BookRepo, loans: LoanRepo, reservations: ReservationRepo, fines: FineService):
        self.users = users
        self.books = books
        self.loans = loans
        self.reservations = reservations
        self.fines = fines

        # simple per-user borrow limit (dummy)
        self.borrow_limit = 5
        self.default_loan_days = 14

    def checkout_first_available(self, user_id: str, book_id: str, now: Optional[datetime] = None) -> Optional[Loan]:
        now = now or datetime.utcnow()
        user = self.users.get(user_id)
        if not user or not user.can_borrow():
            print("[checkout] user missing or not allowed")
            return None

        # block if fines too high (dummy policy)
        # (FineService.pay_all can clear them)
        # In a real system, UserService would enforce; this is illustrative.
        # -- no-op here --

        # honor reservations: if queue exists and first is NOT this user, deny
        queue = self.reservations.list_active_for_book(book_id)
        if queue and queue[0].user_id != user_id:
            print("[checkout] book reserved by someone else first")
            return None

        # find an available copy
        for copy_id in self.books.list_available_copy_ids(book_id):
            # mark copy out
            copy = self.books.get_copy(copy_id)
            if copy is None:
                continue
            copy.status = CopyStatus.CHECKED_OUT

            loan = Loan(
                loan_id=_new_id("loan"),
                user_id=user_id,
                copy_id=copy_id,
                checkout_at=now,
                due_at=now + timedelta(days=self.default_loan_days),
            )
            self.loans.add(loan)

            # if the same user had an active reservation, fulfill it
            for r in queue:
                if r.user_id == user_id and r.status == ReservationStatus.ACTIVE:
                    r.status = ReservationStatus.FULFILLED
                    break

            return loan

        print("[checkout] no copies available")
        return None

    def return_copy(self, loan_id: str, now: Optional[datetime] = None) -> Optional[Loan]:
        now = now or datetime.utcnow()
        loan = self.loans.get(loan_id)
        if not loan or loan.returned_at is not None:
            print("[return] invalid loan")
            return None

        # mark loan
        loan.mark_returned(now)

        # free copy
        copy = self.books.get_copy(loan.copy_id)
        if copy:
            copy.status = CopyStatus.AVAILABLE

        # assess fine if overdue (demo rule)
        fine = self.fines.assess_overdue_fine(loan, now)
        if fine:
            print(f"[return] fine assessed: ${fine.amount_cents/100:.2f}")

        # notify next reservation holder (dummy print)
        book = self.books.get_book(copy.book_id) if copy else None
        queue = self.reservations.list_active_for_book(book.book_id) if book else []
        if queue:
            next_user = queue[0].user_id
            print(f"[return] notifying next in queue (user={next_user}) for book={book.title if book else '?'}")

        return loan

    def reserve_book(self, user_id: str, book_id: str) -> Reservation:
        r = Reservation(
            reservation_id=_new_id("res"),
            user_id=user_id,
            book_id=book_id,
            placed_at=datetime.utcnow(),
        )
        self.reservations.add(r)
        return r

    def list_user_loans(self, user_id: str) -> List[Loan]:
        return self.loans.list_by_user(user_id)

    def list_overdue_loans(self) -> List[Loan]:
        return self.loans.list_overdue()


# =========================
# api (facade)
# =========================

class LibrarySystem:
    """
    A simple facade that wires repos + services and offers a compact API.
    """

    def __init__(self) -> None:
        # repos
        self.users = UserRepo()
        self.books = BookRepo()
        self.loans = LoanRepo()
        self.reservations = ReservationRepo()
        self.fines = FineRepo()

        # services
        self.user_service = UserService(self.users, self.fines)
        self.catalog = CatalogService(self.books)
        self.fine_service = FineService(self.fines)
        self.circulation = CirculationService(self.users, self.books, self.loans, self.reservations, self.fine_service)

    # ---- user module
    def create_user(self, name: str, email: str, role: Role = Role.MEMBER) -> User:
        return self.user_service.register_user(name, email, role)

    # ---- book/catalog module
    def add_book(self, title: str, author: str, isbn: str, tags: Optional[List[str]] = None, copies: int = 1) -> Book:
        return self.catalog.add_book_with_copies(title, author, isbn, tags, copies)

    def search_books(self, text: str) -> List[Book]:
        return self.catalog.search(text)

    # ---- circulation module
    def checkout(self, user_id: str, book_id: str) -> Optional[Loan]:
        return self.circulation.checkout_first_available(user_id, book_id)

    def return_loan(self, loan_id: str) -> Optional[Loan]:
        return self.circulation.return_copy(loan_id)

    def reserve(self, user_id: str, book_id: str) -> Reservation:
        return self.circulation.reserve_book(user_id, book_id)

    # ---- fines
    def pay_all_fines(self, user_id: str) -> float:
        cents = self.fine_service.pay_all(user_id)
        return cents / 100.0

    # ---- reporting (dummy)
    def report_overdue(self) -> List[Loan]:
        return self.circulation.list_overdue_loans()

    def report_inventory(self) -> List[tuple[Book, int, int]]:
        """
        Returns tuples of (Book, total_copies, available_copies)
        """
        report = []
        for book in self.books.list_books():
            copies = self.books.list_copies_for_book(book.book_id)
            total = len(copies)
            available = sum(1 for c in copies if c.status == CopyStatus.AVAILABLE)
            report.append((book, total, available))
        return report


# =========================
# seed & demo
# =========================

def seed_demo_data(sys: LibrarySystem) -> None:
    # users
    alice = sys.create_user("Alice Reader", "alice@example.com")
    bob = sys.create_user("Bob Librarian", "bob@example.com", role=Role.LIBRARIAN)
    admin = sys.create_user("Ava Admin", "admin@example.com", role=Role.ADMIN)

    # books
    dune = sys.add_book("Dune", "Frank Herbert", "9780441172719", tags=["sci-fi", "classic"], copies=2)
    hp1 = sys.add_book("Harry Potter and the Sorcerer's Stone", "J.K. Rowling", "9780590353427", tags=["fantasy"], copies=1)
    clean_code = sys.add_book("Clean Code", "Robert C. Martin", "9780132350884", tags=["software", "craft"], copies=3)

    # checkouts
    l1 = sys.checkout(alice.user_id, dune.book_id)
    l2 = sys.checkout(alice.user_id, clean_code.book_id)
    l3 = sys.checkout(bob.user_id, hp1.book_id)

    # reservations
    sys.reserve(alice.user_id, hp1.book_id)   # Alice wants HP1 next
    sys.reserve(admin.user_id, dune.book_id)  # Admin in Dune queue

    # Simulate overdue (manually tweak due date for testing)
    if l1:
        l1.due_at = datetime.utcnow() - timedelta(days=3)  # already overdue by 3 days

    print("[seed] users:", [u.name for u in sys.users.list_all()])
    print("[seed] books:", [b.title for b in sys.books.list_books()])
    print("[seed] sample loans:", [l.loan_id for l in sys.loans.list_by_user(alice.user_id)])


def demo_flow() -> None:
    sys = LibrarySystem()
    seed_demo_data(sys)

    # Search
    print("\n[demo] search 'clean':", [b.title for b in sys.search_books("clean")])

    # Report inventory
    print("\n[demo] inventory:")
    for book, total, available in sys.report_inventory():
        print(f"  - {book.title}: total={total}, available={available}")

    # Return a loan (overdue -> fine)
    alice_loans = sys.circulation.list_user_loans(next(u.user_id for u in sys.users.list_all() if u.name == "Alice Reader"))
    overdue_loan = next((l for l in alice_loans if l.is_overdue()), None)
    if overdue_loan:
        print(f"\n[demo] returning overdue loan {overdue_loan.loan_id} (should assess fine)")
        sys.return_loan(overdue_loan.loan_id)

    # Pay fines
    alice = next(u for u in sys.users.list_all() if u.name == "Alice Reader")
    total_paid = sys.pay_all_fines(alice.user_id)
    if total_paid:
        print(f"[demo] Alice paid fines: ${total_paid:.2f}")

    # Try to checkout reserved book with wrong user (should be blocked by queue)
    dune = next(b for b in sys.books.list_books() if b.title == "Dune")
    bob = next(u for u in sys.users.list_all() if u.name == "Bob Librarian")
    attempt = sys.checkout(bob.user_id, dune.book_id)
    print("\n[demo] Bob tries checkout Dune while Admin is first in queue:", "SUCCESS" if attempt else "DENIED")

    # Show overdue report (should be empty if all returned)
    print("\n[demo] overdue loans:", [l.loan_id for l in sys.report_overdue()])


if __name__ == "__main__":
    demo_flow()
