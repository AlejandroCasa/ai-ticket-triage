from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Define the base class for ORM models
Base = declarative_base()


class Ticket(Base):
    """
    Represents an IT Service Ticket in the database.
    """

    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), nullable=False)

    # Architect Note: Always use timezone-aware datetimes.
    # 'utcnow' is deprecated. We use a lambda to ensure the function is called
    # at insertion time, not at module definition time.
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    description = Column(Text, nullable=False)
    urgency = Column(String(20), default="Medium")

    # Stores SHA256 hash of the description for O(1) deduplication lookup
    content_hash = Column(String(64), index=True, nullable=True)

    # This field will be filled by our AI
    category = Column(String(100), default=None, nullable=True)

    # Status tracking (New -> Classified -> Resolved)
    status = Column(String(20), default="New")

    def __repr__(self) -> str:
        """
        String representation for debugging and logging (Observability).
        """
        return f"<Ticket(id={self.id}, hash='{self.content_hash}' status='{self.status}')>"


def init_db(db_url: str = "sqlite:///tickets.db") -> sessionmaker:
    """
    Initializes the database engine and creates tables if they don't exist.

    Args:
        db_url (str): The database connection string. Defaults to local SQLite.

    Returns:
        sessionmaker: A factory for creating new database sessions.
    """
    # echo=False prevents SQL query spam in stdout, enabling cleaner JSON logs elsewhere
    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(engine)

    # Return a configured session factory
    return sessionmaker(bind=engine)