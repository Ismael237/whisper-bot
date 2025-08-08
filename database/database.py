from contextlib import contextmanager
from typing import Generator
import time

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine, Connection
from sqlalchemy.orm import sessionmaker, scoped_session, Session as SessionType
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from config import DATABASE_URL, DEBUG
from .models import Base
from utils.logger import logger, sqlalchemy_logger
from utils.helpers import retry

# Configure SQLAlchemy engine with connection pooling and timeouts
engine = create_engine(
    DATABASE_URL,
    echo=False,
)

# Configure SQLAlchemy session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)

# Create a scoped session factory
Session = scoped_session(SessionLocal)

# Configure SQLAlchemy logging
if DEBUG:
    @event.listens_for(Engine, 'before_cursor_execute')
    def before_cursor_execute(conn, cursor, statement, params, context, executemany):
        conn.info.setdefault('query_start_time', []).append(time.time())
        sqlalchemy_logger.debug("Query: %s", statement)
        if params:
            sqlalchemy_logger.debug("Parameters: %r", params)

    @event.listens_for(Engine, 'after_cursor_execute')
    def after_cursor_execute(conn, cursor, statement, params, context, executemany):
        total = time.time() - conn.info['query_start_time'].pop(-1)
        sqlalchemy_logger.debug("Query completed in %fms", (total * 1000))

def init_db() -> None:
    """Initialize the database by creating all tables."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise

def get_db() -> Generator[SessionType, None, None]:
    """
    Dependency function to get DB session.
    Use this in FastAPI path operations or other contexts.
    
    Yields:
        Session: A database session
        
    Example:
        >>> def some_function():
        ...     with get_db() as db:
        ...         # Use db session here
        ...         pass
    """
    db = Session()
    try:
        yield db
    except Exception as e:
        db.rollback()
        logger.error(f"Database error in get_db: {str(e)}")
        raise
    finally:
        db.close()

@contextmanager
def get_db_session() -> Generator[SessionType, None, None]:
    """
    Context manager for database sessions with automatic transaction handling.
    
    Yields:
        Session: A database session
        
    Example:
        >>> with get_db_session() as db:
        ...     # Use db session here
        ...     pass
    """
    db = Session()
    try:
        yield db
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"SQLAlchemy error in get_db_session: {str(e)}")
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"General error in get_db_session: {str(e)}")
        raise
    finally:
        db.close()

@retry(
    exceptions=(OperationalError,),
    max_retries=3,
    initial_delay=1.0,
    backoff_factor=2.0,
    logger=logger
)
def get_db_connection() -> Connection:
    """
    Get a raw database connection with retry logic.
    
    Returns:
        Connection: A raw database connection
        
    Raises:
        OperationalError: If connection cannot be established after retries
    """
    try:
        return engine.connect()
    except OperationalError as e:
        logger.error(f"Failed to establish database connection: {str(e)}")
        raise

def close_db_connection() -> None:
    """Close all database connections and clean up resources."""
    try:
        Session.remove()
        engine.dispose()
        logger.info("Database connections closed successfully")
    except Exception as e:
        logger.error(f"Error closing database connections: {str(e)}")
        raise

def execute_in_transaction(func, *args, **kwargs):
    """
    Execute a function within a database transaction.
    
    Args:
        func: The function to execute
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        The result of the function call
        
    Raises:
        Exception: Any exception raised by the function
    """
    with get_db_session() as session:
        return func(session, *args, **kwargs)
