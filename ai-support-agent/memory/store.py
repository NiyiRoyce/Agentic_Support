# memory store
"""Memory store implementations for conversation persistence."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import json


@dataclass
class ConversationMessage:
    """Single message in a conversation."""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ConversationMessage':
        """Create from dictionary."""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class ConversationSession:
    """Complete conversation session with metadata."""
    session_id: str
    user_id: Optional[str]
    messages: List[ConversationMessage]
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = None
    summary: Optional[str] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def add_message(self, message: ConversationMessage):
        """Add message to session."""
        self.messages.append(message)
        self.updated_at = datetime.now()
    
    def get_recent_messages(self, n: int = 10) -> List[ConversationMessage]:
        """Get n most recent messages."""
        return self.messages[-n:] if self.messages else []
    
    def get_message_count(self) -> int:
        """Get total message count."""
        return len(self.messages)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'messages': [msg.to_dict() for msg in self.messages],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'metadata': self.metadata,
            'summary': self.summary,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ConversationSession':
        """Create from dictionary."""
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        data['messages'] = [
            ConversationMessage.from_dict(msg)
            for msg in data['messages']
        ]
        return cls(**data)


class BaseMemoryStore(ABC):
    """Abstract base class for memory storage backends."""
    
    @abstractmethod
    async def save_session(self, session: ConversationSession) -> bool:
        """Save conversation session."""
        pass
    
    @abstractmethod
    async def load_session(self, session_id: str) -> Optional[ConversationSession]:
        """Load conversation session."""
        pass
    
    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """Delete conversation session."""
        pass
    
    @abstractmethod
    async def list_user_sessions(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[ConversationSession]:
        """List sessions for a user."""
        pass
    
    @abstractmethod
    async def session_exists(self, session_id: str) -> bool:
        """Check if session exists."""
        pass


class InMemoryStore(BaseMemoryStore):
    """
    In-memory storage for development and testing.
    Not suitable for production - data lost on restart.
    """
    
    def __init__(self):
        self._sessions: Dict[str, ConversationSession] = {}
        self._user_sessions: Dict[str, List[str]] = {}  # user_id -> [session_ids]
    
    async def save_session(self, session: ConversationSession) -> bool:
        """Save session to memory."""
        self._sessions[session.session_id] = session
        
        # Track user sessions
        if session.user_id:
            if session.user_id not in self._user_sessions:
                self._user_sessions[session.user_id] = []
            if session.session_id not in self._user_sessions[session.user_id]:
                self._user_sessions[session.user_id].append(session.session_id)
        
        return True
    
    async def load_session(self, session_id: str) -> Optional[ConversationSession]:
        """Load session from memory."""
        return self._sessions.get(session_id)
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session from memory."""
        if session_id in self._sessions:
            session = self._sessions[session_id]
            
            # Remove from user sessions
            if session.user_id and session.user_id in self._user_sessions:
                if session_id in self._user_sessions[session.user_id]:
                    self._user_sessions[session.user_id].remove(session_id)
            
            del self._sessions[session_id]
            return True
        return False
    
    async def list_user_sessions(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[ConversationSession]:
        """List user sessions."""
        session_ids = self._user_sessions.get(user_id, [])
        sessions = [
            self._sessions[sid]
            for sid in session_ids[-limit:]
            if sid in self._sessions
        ]
        return sorted(sessions, key=lambda s: s.updated_at, reverse=True)
    
    async def session_exists(self, session_id: str) -> bool:
        """Check if session exists."""
        return session_id in self._sessions
    
    def clear_all(self):
        """Clear all sessions (useful for testing)."""
        self._sessions.clear()
        self._user_sessions.clear()


class RedisStore(BaseMemoryStore):
    """
    Redis-based storage for production use.
    Provides persistence and scalability.
    """
    
    def __init__(self, redis_url: str, ttl_seconds: int = 86400):
        """
        Initialize Redis store.
        
        Args:
            redis_url: Redis connection URL
            ttl_seconds: Time-to-live for sessions (default 24 hours)
        """
        self.redis_url = redis_url
        self.ttl_seconds = ttl_seconds
        self._client = None
    
    async def _get_client(self):
        """Get or create Redis client."""
        if self._client is None:
            import aioredis
            self._client = await aioredis.create_redis_pool(self.redis_url)
        return self._client
    
    async def save_session(self, session: ConversationSession) -> bool:
        """Save session to Redis."""
        client = await self._get_client()
        
        # Serialize session
        session_data = json.dumps(session.to_dict())
        
        # Save to Redis with TTL
        await client.setex(
            f"session:{session.session_id}",
            self.ttl_seconds,
            session_data
        )
        
        # Track user sessions
        if session.user_id:
            await client.sadd(
                f"user_sessions:{session.user_id}",
                session.session_id
            )
            await client.expire(
                f"user_sessions:{session.user_id}",
                self.ttl_seconds
            )
        
        return True
    
    async def load_session(self, session_id: str) -> Optional[ConversationSession]:
        """Load session from Redis."""
        client = await self._get_client()
        
        data = await client.get(f"session:{session_id}")
        if not data:
            return None
        
        session_dict = json.loads(data)
        return ConversationSession.from_dict(session_dict)
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session from Redis."""
        client = await self._get_client()
        
        # Load session to get user_id
        session = await self.load_session(session_id)
        
        # Delete session
        deleted = await client.delete(f"session:{session_id}")
        
        # Remove from user sessions
        if session and session.user_id:
            await client.srem(
                f"user_sessions:{session.user_id}",
                session_id
            )
        
        return deleted > 0
    
    async def list_user_sessions(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[ConversationSession]:
        """List user sessions from Redis."""
        client = await self._get_client()
        
        # Get session IDs
        session_ids = await client.smembers(f"user_sessions:{user_id}")
        
        # Load sessions
        sessions = []
        for sid in session_ids:
            session = await self.load_session(sid.decode())
            if session:
                sessions.append(session)
        
        # Sort by updated_at and limit
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions[:limit]
    
    async def session_exists(self, session_id: str) -> bool:
        """Check if session exists in Redis."""
        client = await self._get_client()
        return await client.exists(f"session:{session_id}")
    
    async def close(self):
        """Close Redis connection."""
        if self._client:
            self._client.close()
            await self._client.wait_closed()


class FileStore(BaseMemoryStore):
    """
    File-based storage for simple persistence.
    Good for small-scale or development use.
    """
    
    def __init__(self, storage_dir: str = "./memory_storage"):
        """
        Initialize file store.
        
        Args:
            storage_dir: Directory to store session files
        """
        self.storage_dir = storage_dir
        self._ensure_directory()
    
    def _ensure_directory(self):
        """Ensure storage directory exists."""
        import os
        os.makedirs(self.storage_dir, exist_ok=True)
        os.makedirs(f"{self.storage_dir}/sessions", exist_ok=True)
        os.makedirs(f"{self.storage_dir}/users", exist_ok=True)
    
    def _session_path(self, session_id: str) -> str:
        """Get file path for session."""
        return f"{self.storage_dir}/sessions/{session_id}.json"
    
    def _user_index_path(self, user_id: str) -> str:
        """Get file path for user session index."""
        return f"{self.storage_dir}/users/{user_id}.json"
    
    async def save_session(self, session: ConversationSession) -> bool:
        """Save session to file."""
        try:
            # Save session
            with open(self._session_path(session.session_id), 'w') as f:
                json.dump(session.to_dict(), f, indent=2)
            
            # Update user index
            if session.user_id:
                await self._update_user_index(session.user_id, session.session_id)
            
            return True
        except Exception:
            return False
    
    async def load_session(self, session_id: str) -> Optional[ConversationSession]:
        """Load session from file."""
        try:
            with open(self._session_path(session_id), 'r') as f:
                data = json.load(f)
            return ConversationSession.from_dict(data)
        except FileNotFoundError:
            return None
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session file."""
        import os
        try:
            session = await self.load_session(session_id)
            
            # Delete file
            os.remove(self._session_path(session_id))
            
            # Update user index
            if session and session.user_id:
                await self._remove_from_user_index(session.user_id, session_id)
            
            return True
        except FileNotFoundError:
            return False
    
    async def list_user_sessions(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[ConversationSession]:
        """List user sessions from files."""
        try:
            with open(self._user_index_path(user_id), 'r') as f:
                session_ids = json.load(f)
        except FileNotFoundError:
            return []
        
        # Load sessions
        sessions = []
        for sid in session_ids[-limit:]:
            session = await self.load_session(sid)
            if session:
                sessions.append(session)
        
        return sorted(sessions, key=lambda s: s.updated_at, reverse=True)
    
    async def session_exists(self, session_id: str) -> bool:
        """Check if session file exists."""
        import os
        return os.path.exists(self._session_path(session_id))
    
    async def _update_user_index(self, user_id: str, session_id: str):
        """Update user session index."""
        try:
            with open(self._user_index_path(user_id), 'r') as f:
                session_ids = json.load(f)
        except FileNotFoundError:
            session_ids = []
        
        if session_id not in session_ids:
            session_ids.append(session_id)
        
        with open(self._user_index_path(user_id), 'w') as f:
            json.dump(session_ids, f)
    
    async def _remove_from_user_index(self, user_id: str, session_id: str):
        """Remove session from user index."""
        try:
            with open(self._user_index_path(user_id), 'r') as f:
                session_ids = json.load(f)
            
            if session_id in session_ids:
                session_ids.remove(session_id)
            
            with open(self._user_index_path(user_id), 'w') as f:
                json.dump(session_ids, f)
        except FileNotFoundError:
            pass