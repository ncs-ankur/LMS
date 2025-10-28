from __future__ import annotations
from typing import List, Optional, Tuple

from .domain import Book, CopyStatus, Loan, Reservation, Role
from .repositories import BookRepo, FineRepo, LoanRepo, ReservationRepo, UserRepo
from .services import CatalogService, CirculationService, FineService, UserService


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
        self.circulation = CirculationService(
            self.users, self.books, self.loans, self.reservations, self.fine_service
        )

    # ---- user module
    def create_user(self, name: str, email: str, role: Role = Role.MEMBER):
        return self.user_service.register_user(name, email, role)

    # ---- book/catalog module
    def add_book(
        self,
        title: str,
        author: str,
        isbn: str,
        tags: Optional[list[str]] = None,
        copies: int = 1,
    ) -> Book:
        return self.catalog.add_book_with_copies(title, author, isbn, tags, copies)

    def search_books(self, text: str) -> list[Book]:
        return self.catalog.search(text)

    # ---- circulation module
    def checkout(self, user_id: str, book_id: str):
        return self.circulation.checkout_first_available(user_id, book_id)

    def return_loan(self, loan_id: str):
        return self.circulation.return_copy(loan_id)

    def reserve(self, user_id: str, book_id: str) -> Reservation:
        return self.circulation.reserve_book(user_id, book_id)

    # ---- fines
    def pay_all_fines(self, user_id: str) -> float:
        cents = self.fine_service.pay_all(user_id)
        return cents / 100.0

    # ---- reporting (dummy)
    def report_overdue(self) -> list[Loan]:
        return self.circulation.list_overdue_loans()

    def report_inventory(self) -> list[tuple[Book, int, int]]:
        """
        Returns tuples of (Book, total_copies, available_copies)
        """
        report: list[tuple[Book, int, int]] = []
        for book in self.books.list_books():
            copies = self.books.list_copies_for_book(book.book_id)
            total = len(copies)
            available = sum(1 for c in copies if c.status == CopyStatus.AVAILABLE)
            report.append((book, total, available))
        return report

