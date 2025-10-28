"""
BookHive LMS package.

Exports key modules for convenient imports.
"""

from .domain import (
    Role,
    User,
    Book,
    CopyStatus,
    Copy,
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

from .services import (
    UserService,
    CatalogService,
    FineService,
    CirculationService,
)

from .api import LibrarySystem
from .seed import seed_demo_data

__all__ = [
    # domain
    "Role",
    "User",
    "Book",
    "CopyStatus",
    "Copy",
    "Loan",
    "ReservationStatus",
    "Reservation",
    "Fine",
    # repos
    "UserRepo",
    "BookRepo",
    "LoanRepo",
    "ReservationRepo",
    "FineRepo",
    # services
    "UserService",
    "CatalogService",
    "FineService",
    "CirculationService",
    # api
    "LibrarySystem",
    # seed
    "seed_demo_data",
]

