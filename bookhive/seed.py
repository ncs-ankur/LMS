from __future__ import annotations
from datetime import datetime, timedelta

from .api import LibrarySystem
from .domain import Role


def seed_demo_data(sys: LibrarySystem) -> None:
    # users
    alice = sys.create_user("Alice Reader", "alice@example.com")
    bob = sys.create_user("Bob Librarian", "bob@example.com", role=Role.LIBRARIAN)
    admin = sys.create_user("Ava Admin", "admin@example.com", role=Role.ADMIN)

    # books
    dune = sys.add_book(
        "Dune",
        "Frank Herbert",
        "9780441172719",
        tags=["sci-fi", "classic"],
        copies=2,
    )
    hp1 = sys.add_book(
        "Harry Potter and the Sorcerer's Stone",
        "J.K. Rowling",
        "9780590353427",
        tags=["fantasy"],
        copies=1,
    )
    clean_code = sys.add_book(
        "Clean Code",
        "Robert C. Martin",
        "9780132350884",
        tags=["software", "craft"],
        copies=3,
    )

    # checkouts
    l1 = sys.checkout(alice.user_id, dune.book_id)
    l2 = sys.checkout(alice.user_id, clean_code.book_id)
    l3 = sys.checkout(bob.user_id, hp1.book_id)

    # reservations
    sys.reserve(alice.user_id, hp1.book_id)  # Alice wants HP1 next
    sys.reserve(admin.user_id, dune.book_id)  # Admin in Dune queue

    # Simulate overdue (manually tweak due date for testing)
    if l1:
        l1.due_at = datetime.utcnow() - timedelta(days=3)  # already overdue by 3 days

    print("[seed] users:", [u.name for u in sys.users.list_all()])
    print("[seed] books:", [b.title for b in sys.books.list_books()])
    print("[seed] sample loans:", [l.loan_id for l in sys.loans.list_by_user(alice.user_id)])

