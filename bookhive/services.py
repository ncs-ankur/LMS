from __future__ import annotations
from datetime import datetime, timedelta
from typing import List, Optional
import uuid

from .domain import (
    Role,
    User,
    Book,
    Copy,
    CopyStatus,
    Loan,
    ReservationStatus,
    Reservation,
    Fine,
)
from .repositories import (
    UserRepo,
    BookRepo,
    LoanRepo,
    ReservationRepo,
    FineRepo,
)


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

    def add_book_with_copies(
        self,
        title: str,
        author: str,
        isbn: str,
        tags: Optional[List[str]] = None,
        copies: int = 1,
    ) -> Book:
        b = Book(
            book_id=_new_id("bk"),
            title=title,
            author=author,
            isbn=isbn,
            tags=tags or [],
        )
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
    def __init__(
        self,
        users: UserRepo,
        books: BookRepo,
        loans: LoanRepo,
        reservations: ReservationRepo,
        fines: FineService,
    ):
        self.users = users
        self.books = books
        self.loans = loans
        self.reservations = reservations
        self.fines = fines

        # simple per-user borrow limit (dummy)
        self.borrow_limit = 5
        self.default_loan_days = 14

    def checkout_first_available(
        self, user_id: str, book_id: str, now: Optional[datetime] = None
    ) -> Optional[Loan]:
        now = now or datetime.utcnow()
        user = self.users.get(user_id)
        if not user or not user.can_borrow():
            print("[checkout] user missing or not allowed")
            return None

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
            print(
                f"[return] notifying next in queue (user={next_user}) for book={book.title if book else '?'}"
            )

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
