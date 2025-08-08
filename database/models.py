from datetime import datetime
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from enum import Enum as PyEnum
import uuid
import json

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, BigInteger, DateTime,
    JSON, Enum as SQLAEnum, ForeignKey, func, Index
)
from sqlalchemy.orm import relationship, validates, Session as SessionType
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.dialects.postgresql import UUID

from utils.logger import logger
from utils.helpers import get_utc_time

# Type checking imports
if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# Base class for all models
class BaseModel:
    """Base model class with common functionality."""
    
    @declared_attr
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
        return cls.__name__.lower() + 's'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
    
    def to_json(self) -> str:
        """Convert model instance to JSON string."""
        return json.dumps(self.to_dict(), default=str)
    
    def update(self, **kwargs) -> None:
        """Update model attributes."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

# Create base class with our custom base model
Base = declarative_base(cls=BaseModel)

class SessionType(PyEnum):
    """Types of user sessions in the system."""
    SETUP = 'setup'  # Initial setup/configuration
    SENDING_MESSAGE = 'sending_message'  # User is in the process of sending a message
    BROWSING_INBOX = 'browsing_inbox'  # User is viewing their received messages
    
    @classmethod
    def values(cls) -> List[str]:
        """Get all possible session type values."""
        return [member.value for member in cls]
    
    def __str__(self) -> str:
        return self.value


class ActionType(PyEnum):
    """Types of actions that can be logged in the system."""
    REGISTER = 'register'  # User registration
    SEND_MESSAGE = 'send_message'  # Sending an anonymous message
    READ_MESSAGE = 'read_message'  # Reading a received message
    SHARE_MESSAGE = 'share_message'  # Sharing a message link
    DELETE_ACCOUNT = 'delete_account'  # Account deletion
    LOGIN = 'login'  # User login
    LOGOUT = 'logout'  # User logout
    
    @classmethod
    def values(cls) -> List[str]:
        """Get all possible action type values."""
        return [member.value for member in cls]
    
    def __str__(self) -> str:
        return self.value

class User(Base):
    """User model representing a Telegram user in the system."""
    
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, comment='Primary key')
    telegram_id = Column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True,
        comment='Telegram user ID (from Telegram API)'
    )
    username = Column(
        String(50),
        nullable=False,
        index=True,
        comment='User-chosen display name'
    )
    telegram_username = Column(
        String(50),
        nullable=True,
        index=True,
        comment='Telegram username (with @), if available'
    )
    unique_code = Column(
        String(30),
        unique=True,
        nullable=False,
        index=True,
        comment='Unique code for sharing messages with this user'
    )
    total_messages_received = Column(
        Integer,
        default=0,
        nullable=False,
        comment='Total number of messages received by this user'
    )
    total_messages_sent = Column(
        Integer,
        default=0,
        nullable=False,
        comment='Total number of messages sent by this user'
    )
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        comment='Whether the user account is active'
    )
    created_at = Column(
        DateTime,
        default=get_utc_time,
        nullable=False,
        comment='When the user account was created'
    )
    updated_at = Column(
        DateTime,
        default=get_utc_time,
        onupdate=get_utc_time,
        nullable=False,
        comment='When the user record was last updated'
    )
    last_activity = Column(
        DateTime,
        default=get_utc_time,
        nullable=False,
        comment='Timestamp of last user activity'
    )
    
    # Relationships
    received_messages = relationship(
        "AnonymousMessage",
        back_populates="recipient",
        foreign_keys="[AnonymousMessage.recipient_id]",
        cascade="all, delete-orphan",
        lazy='dynamic',
        order_by="desc(AnonymousMessage.created_at)"
    )
    sessions = relationship(
        "UserSession",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy='dynamic'
    )
    activity_logs = relationship(
        "ActivityLog",
        primaryjoin="User.telegram_id==foreign(ActivityLog.telegram_id)",
        viewonly=True,
        lazy='dynamic',
        order_by="desc(ActivityLog.created_at)"
    )
    
    __table_args__ = (
        Index('ix_users_username_lower', func.lower(username), unique=False),
        {'comment': 'Stores user account information'}
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"
    
    @validates('username')
    def validate_username(self, key: str, username: str) -> str:
        """Validate and normalize username."""
        if not username or len(username.strip()) < 3:
            raise ValueError("Username must be at least 3 characters long")
        return username.strip()
    
    @classmethod
    def get_by_telegram_id(cls, session: SessionType, telegram_id: int) -> Optional['User']:
        """Get user by Telegram ID."""
        return session.query(cls).filter(cls.telegram_id == telegram_id).first()
    
    def increment_messages_received(self, session: SessionType) -> None:
        """Increment received messages counter and update last activity."""
        self.total_messages_received += 1
        self.last_activity = get_utc_time()
        session.add(self)
    
    def increment_messages_sent(self, session: SessionType) -> None:
        """Increment sent messages counter and update last activity."""
        self.total_messages_sent += 1
        self.last_activity = get_utc_time()
        session.add(self)
    
    def deactivate(self, session: SessionType) -> None:
        """Deactivate the user account."""
        self.is_active = False
        self.updated_at = get_utc_time()
        session.add(self)
    
    def update_activity(self, session: SessionType) -> None:
        """Update the last activity timestamp."""
        self.last_activity = get_utc_time()
        session.add(self)

class AnonymousMessage(Base):
    """Model representing an anonymous message between users."""
    
    __tablename__ = 'anonymous_messages'
    
    id = Column(Integer, primary_key=True, comment='Primary key')
    public_id = Column(
        String(36),
        unique=True,
        nullable=False,
        default=lambda: str(uuid.uuid4()),
        comment='Public unique identifier for sharing'
    )
    recipient_id = Column(
        Integer,
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        comment='Recipient user ID'
    )
    sender_telegram_id = Column(
        BigInteger,
        nullable=False,
        index=True,
        comment='Sender Telegram ID (remains anonymous to recipient)'
    )
    message_content = Column(
        Text,
        nullable=False,
        comment='The actual message content (encrypted in transit)'
    )
    is_read = Column(
        Boolean,
        default=False,
        nullable=False,
        comment='Whether the message has been read by the recipient'
    )
    shared_count = Column(
        Integer,
        default=0,
        nullable=False,
        comment='Number of times this message has been shared'
    )
    created_at = Column(
        DateTime,
        default=get_utc_time,
        nullable=False,
        index=True,
        comment='When the message was created'
    )
    read_at = Column(
        DateTime,
        nullable=True,
        comment='When the message was first read (if read)'
    )
    
    # Relationships
    recipient = relationship(
        "User",
        back_populates="received_messages",
        foreign_keys=[recipient_id]
    )
    
    __table_args__ = {
        'comment': 'Stores anonymous messages between users'
    }
    
    def __repr__(self) -> str:
        return f"<AnonymousMessage(id={self.id}, recipient_id={self.recipient_id})>"
    
    @validates('message_content')
    def validate_message_content(self, key: str, content: str) -> str:
        """Validate message content."""
        if not content or len(content.strip()) < 1:
            raise ValueError("Message content cannot be empty")
        if len(content) > 4000:  # Arbitrary limit, adjust as needed
            raise ValueError("Message is too long")
        return content.strip()
    
    def mark_as_read(self, session: SessionType) -> None:
        """Mark the message as read and update timestamps."""
        if not self.is_read:
            self.is_read = True
            self.read_at = self.read_at or get_utc_time()
            session.add(self)
    
    def increment_share_count(self, session: SessionType) -> None:
        """Increment the share count for this message."""
        self.shared_count += 1
        session.add(self)
    
    def get_share_link(self, bot_username: str) -> str:
        """Generate a share link for this message."""
        from utils.helpers import generate_share_link
        return generate_share_link(bot_username, self.public_id)
    
    def to_dict(self, include_content: bool = True) -> Dict[str, Any]:
        """Convert message to dictionary, optionally excluding content."""
        result = {
            'id': self.id,
            'public_id': self.public_id,
            'is_read': self.is_read,
            'shared_count': self.shared_count,
            'created_at': self.created_at.isoformat(),
            'read_at': self.read_at.isoformat() if self.read_at else None,
        }
        
        if include_content:
            result['message_content'] = self.message_content
            
        return result

class UserSession(Base):
    """Model representing a user's session state in the application."""
    
    __tablename__ = 'user_sessions'
    
    id = Column(Integer, primary_key=True, comment='Primary key')
    telegram_id = Column(
        BigInteger,
        nullable=False,
        index=True,
        comment='Telegram user ID this session belongs to'
    )
    session_type = Column(
        SQLAEnum(SessionType),
        nullable=False,
        comment='Type of session (e.g., setup, sending_message, etc.)'
    )
    target_user_id = Column(
        Integer,
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=True,
        index=True,
        comment='Target user ID for this session (if applicable)'
    )
    current_step = Column(
        String(50),
        nullable=True,
        comment='Current step in the session flow'
    )
    session_data = Column(
        JSON,
        nullable=True,
        comment='JSON-encoded session data (state)'
    )
    expires_at = Column(
        DateTime,
        nullable=False,
        index=True,
        comment='When this session expires'
    )
    created_at = Column(
        DateTime,
        default=get_utc_time,
        nullable=False,
        comment='When the session was created'
    )
    updated_at = Column(
        DateTime,
        default=get_utc_time,
        onupdate=get_utc_time,
        nullable=False,
        comment='When the session was last updated'
    )
    
    # Relationships
    user = relationship(
        "User",
        back_populates="sessions",
        foreign_keys=[target_user_id]
    )
    
    __table_args__ = {
        'comment': 'Stores user session data for multi-step interactions'
    }
    
    def __repr__(self) -> str:
        return f"<UserSession(id={self.id}, type={self.session_type}, user_id={self.telegram_id})>"
    
    @classmethod
    def get_active_session(
        cls,
        session: SessionType,
        telegram_id: int,
        session_type: Optional[SessionType] = None
    ) -> Optional['UserSession']:
        """Get the most recent active session for a user."""
        query = session.query(cls).filter(
            cls.telegram_id == telegram_id,
            cls.expires_at > get_utc_time()
        )
        
        if session_type:
            query = query.filter(cls.session_type == session_type)
            
        return query.order_by(cls.created_at.desc()).first()
    
    def update_data(self, data: Dict[str, Any], session: SessionType) -> None:
        """Update session data with new values."""
        if not self.session_data:
            self.session_data = {}
            
        self.session_data.update(data)
        self.updated_at = get_utc_time()
        session.add(self)
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """Get a value from session data."""
        if not self.session_data:
            return default
        return self.session_data.get(key, default)
    
    def clear_data(self, session: SessionType) -> None:
        """Clear all session data."""
        self.session_data = {}
        self.updated_at = get_utc_time()
        session.add(self)
    
    def is_expired(self) -> bool:
        """Check if the session has expired."""
        return self.expires_at < get_utc_time()
    
    def extend(self, session: SessionType, hours: float = 24.0) -> None:
        """Extend the session expiration time."""
        from datetime import timedelta
        self.expires_at = get_utc_time() + timedelta(hours=hours)
        self.updated_at = get_utc_time()
        session.add(self)

class GlobalStats(Base):
    """Model for storing global statistics about the application."""
    
    __tablename__ = 'global_stats'
    
    id = Column(Integer, primary_key=True, comment='Primary key')
    stat_date = Column(
        DateTime,
        nullable=False,
        unique=True,
        index=True,
        comment='The date these statistics are for (typically start of day)'
    )
    total_users = Column(
        Integer,
        default=0,
        nullable=False,
        comment='Total number of registered users'
    )
    active_users = Column(
        Integer,
        default=0,
        nullable=False,
        comment='Number of active users in the last 30 days'
    )
    messages_sent_today = Column(
        Integer,
        default=0,
        nullable=False,
        comment='Number of messages sent on this day'
    )
    new_registrations = Column(
        Integer,
        default=0,
        nullable=False,
        comment='Number of new user registrations on this day'
    )
    created_at = Column(
        DateTime,
        default=get_utc_time,
        nullable=False,
        comment='When this stats record was created'
    )
    
    __table_args__ = {
        'comment': 'Stores daily aggregated statistics about the application'
    }
    
    def __repr__(self) -> str:
        return f"<GlobalStats(date={self.stat_date.date()}, users={self.total_users})>"
    
    @classmethod
    def get_or_create_today(
        cls,
        session: SessionType,
        date: Optional[datetime] = None
    ) -> 'GlobalStats':
        """Get today's stats or create a new record if none exists."""
        from datetime import datetime, timedelta
        
        if date is None:
            date = get_utc_time()
            
        # Normalize to start of day
        stat_date = datetime(date.year, date.month, date.day)
        
        # Try to get existing stats for today
        stats = session.query(cls).filter(
            func.date(cls.stat_date) == stat_date.date()
        ).first()
        
        if not stats:
            # Get yesterday's stats as a base
            yesterday = stat_date - timedelta(days=1)
            yesterday_stats = session.query(cls).filter(
                func.date(cls.stat_date) == yesterday.date()
            ).first()
            
            # Create new stats with yesterday's total users as a starting point
            total_users = yesterday_stats.total_users if yesterday_stats else 0
            
            stats = cls(
                stat_date=stat_date,
                total_users=total_users,
                active_users=0,
                messages_sent_today=0,
                new_registrations=0
            )
            session.add(stats)
            session.commit()
            
        return stats
    
    def update_from_query(self, session: SessionType) -> None:
        """Update statistics by querying the database."""
        from sqlalchemy import func, and_
        
        # Update total users
        self.total_users = session.query(func.count(User.id)).scalar() or 0
        
        # Update active users (active in last 30 days)
        thirty_days_ago = get_utc_time() - timedelta(days=30)
        self.active_users = session.query(func.count(User.id)).filter(
            User.last_activity >= thirty_days_ago
        ).scalar() or 0
        
        # Update today's messages
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.messages_sent_today = session.query(func.count(AnonymousMessage.id)).filter(
            AnonymousMessage.created_at >= today_start
        ).scalar() or 0
        
        # Update today's registrations
        self.new_registrations = session.query(func.count(User.id)).filter(
            func.date(User.created_at) == func.current_date()
        ).scalar() or 0
        
        session.add(self)
        session.commit()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to a dictionary."""
        return {
            'date': self.stat_date.date().isoformat(),
            'total_users': self.total_users,
            'active_users': self.active_users,
            'messages_sent_today': self.messages_sent_today,
            'new_registrations': self.new_registrations,
            'created_at': self.created_at.isoformat()
        }

class ActivityLog(Base):
    """Model for logging user activities and actions in the system."""
    
    __tablename__ = 'activity_logs'
    
    id = Column(Integer, primary_key=True, comment='Primary key')
    telegram_id = Column(
        BigInteger,
        nullable=False,
        index=True,
        comment='Telegram user ID who performed the action'
    )
    action_type = Column(
        SQLAEnum(ActionType),
        nullable=False,
        comment='Type of action performed'
    )
    details = Column(
        JSON,
        nullable=True,
        comment='Additional details about the action in JSON format'
    )
    ip_info = Column(
        String(100),
        nullable=True,
        comment='IP address and other connection info'
    )
    user_agent = Column(
        String(255),
        nullable=True,
        comment='User agent string from the request'
    )
    created_at = Column(
        DateTime, 
        default=get_utc_time, 
        nullable=False, 
        index=True,
        comment='When the activity was logged'
    )
    
    # Relationships
    user = relationship(
        "User",
        primaryjoin="foreign(ActivityLog.telegram_id) == User.telegram_id",
        viewonly=True,
        uselist=False
    )
    
    __table_args__ = (
        Index('ix_activity_logs_telegram_id_created_at', 'telegram_id', 'created_at'),
        {'comment': 'Audit log of user activities and actions'}
    )
    
    def __repr__(self) -> str:
        return f"<ActivityLog(id={self.id}, telegram_id={self.telegram_id}, action={self.action_type})>"
    
    @classmethod
    def log_activity(
        cls,
        session: SessionType,
        telegram_id: int,
        action_type: ActionType,
        details: Optional[Dict[str, Any]] = None,
        ip_info: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> 'ActivityLog':
        """Helper method to log a new activity.
        
        Args:
            session: Database session
            telegram_id: ID of the user performing the action
            action_type: Type of action being logged
            details: Optional dictionary with additional details
            ip_info: Optional IP address information
            user_agent: Optional user agent string
            
        Returns:
            The created ActivityLog instance
        """
        log_entry = cls(
            telegram_id=telegram_id,
            action_type=action_type,
            details=details or {},
            ip_info=ip_info,
            user_agent=user_agent
        )
        session.add(log_entry)
        
        # Update user's last activity time
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            user.update_activity(session)
        
        return log_entry
    
    @classmethod
    def get_user_activities(
        cls,
        session: SessionType,
        telegram_id: int,
        limit: int = 100,
        offset: int = 0,
        action_type: Optional[ActionType] = None
    ) -> List['ActivityLog']:
        """Get activity logs for a specific user.
        
        Args:
            session: Database session
            telegram_id: ID of the user to get logs for
            limit: Maximum number of logs to return
            offset: Number of logs to skip
            action_type: Optional action type to filter by
            
        Returns:
            List of ActivityLog instances
        """
        query = session.query(cls).filter(
            cls.telegram_id == telegram_id
        ).order_by(
            cls.created_at.desc()
        )
        
        if action_type:
            query = query.filter(cls.action_type == action_type)
            
        return query.offset(offset).limit(limit).all()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to a dictionary."""
        return {
            'id': self.id,
            'telegram_id': self.telegram_id,
            'action_type': str(self.action_type.value),
            'details': self.details,
            'ip_info': self.ip_info,
            'user_agent': self.user_agent,
            'created_at': self.created_at.isoformat(),
            'username': self.user.username if self.user else None
        }
