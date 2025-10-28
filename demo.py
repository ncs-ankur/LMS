from __future__ import annotations

from bookhive import LibrarySystem, seed_demo_data
from bookhive.domain import CopyStatus


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
    alice_loans = sys.circulation.list_user_loans(
        next(u.user_id for u in sys.users.list_all() if u.name == "Alice Reader")
    )
    overdue_loan = next((l for l in alice_loans if l.is_overdue()), None)
    if overdue_loan:
        print(
            f"\n[demo] returning overdue loan {overdue_loan.loan_id} (should assess fine)"
        )
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
    print(
        "\n[demo] Bob tries checkout Dune while Admin is first in queue:",
        "SUCCESS" if attempt else "DENIED",
    )

    # Show overdue report (should be empty if all returned)
    print("\n[demo] overdue loans:", [l.loan_id for l in sys.report_overdue()])


if __name__ == "__main__":
    demo_flow()

