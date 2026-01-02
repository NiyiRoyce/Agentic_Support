# memory manager
"""Memory manager for conversation state management."""

from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from memory.store import (
    BaseMemoryStore,
    ConversationMessage,
    ConversationSession,
    InMemoryStore,
)
from memory.summarizer import ConversationSummarizer, SummaryCache
from memory.validators import (
    MemoryValidator,
    ContentSanitizer,
    SessionHealthChecker,
)
from llm import LLMRouter


class MemoryManager:
    """
    Central manager for conversation memory.
    
    Handles:
    - Creating and managing sessions
    - Adding messages with validation
    - Automatic summarization
    - Session retrieval and cleanup
    - Memory optimization
    """
    
    def __init__(
        self,
        store: BaseMemoryStore,
        llm_router: Optional[LLMRouter] = None,
        enable_summarization: bool = True,
        enable_validation: bool = True,
        auto_summarize_threshold: int = 20,
    ):
        """
        Initialize memory manager.
        
        Args:
            store: Storage backend
            llm_router: LLM router for summarization
            enable_summarization: Enable automatic summarization
            enable_validation: Enable content validation
            auto_summarize_threshold: Messages before auto-summarization
        """
        self.store = store
        self.llm_router = llm_router
        self.enable_summarization = enable_summarization
        self.enable_validation = enable_validation
        
        # Initialize components
        self.validator = MemoryValidator() if enable_validation else None
        self.sanitizer = ContentSanitizer()
        self.health_checker = SessionHealthChecker()
        
        # Summarization (requires LLM)
        self.summarizer = None
        self.summary_cache = SummaryCache()
        if enable_summarization and llm_router:
            self.summarizer = ConversationSummarizer(
                llm_router=llm_router,
                summary_trigger_threshold=auto_summarize_threshold,
            )
    
    async def create_session(
        self,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ConversationSession:
        """
        Create new conversation session.
        
        Args:
            user_id: Optional user identifier
            session_id: Optional session ID (auto-generated if not provided)
            metadata: Optional session metadata
            
        Returns:
            New conversation session
        """
        session_id = session_id or self._generate_session_id()
        now = datetime.now()
        
        # Sanitize metadata
        clean_metadata = self.sanitizer.sanitize_metadata(metadata or {})
        
        session = ConversationSession(
            session_id=session_id,
            user_id=user_id,
            messages=[],
            created_at=now,
            updated_at=now,
            metadata=clean_metadata,
        )
        
        # Save to store
        await self.store.save_session(session)
        
        return session
    
    async def get_session(
        self,
        session_id: str,
    ) -> Optional[ConversationSession]:
        """
        Retrieve conversation session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session or None if not found
        """
        return await self.store.load_session(session_id)
    
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ConversationMessage:
        """
        Add message to conversation session.
        
        Args:
            session_id: Session identifier
            role: Message role (user/assistant/system)
            content: Message content
            metadata: Optional message metadata
            
        Returns:
            Created message
            
        Raises:
            ValueError: If validation fails
        """
        # Load session
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Sanitize content
        clean_content = self.sanitizer.sanitize_message(content)
        clean_metadata = self.sanitizer.sanitize_metadata(metadata or {})
        
        # Create message
        message = ConversationMessage(
            role=role,
            content=clean_content,
            timestamp=datetime.now(),
            metadata=clean_metadata,
        )
        
        # Validate if enabled
        if self.enable_validation:
            is_valid, error = self.validator.validate_message(message)
            if not is_valid:
                raise ValueError(f"Message validation failed: {error}")
        
        # Add to session
        session.add_message(message)
        
        # Check if summarization needed
        if self.summarizer and await self.summarizer.should_summarize(session):
            session = await self.summarizer.summarize_and_compress(session)
        
        # Save session
        await self.store.save_session(session)
        
        return message
    
    async def get_conversation_history(
        self,
        session_id: str,
        limit: Optional[int] = None,
        include_summary: bool = True,
    ) -> List[ConversationMessage]:
        """
        Get conversation history for a session.
        
        Args:
            session_id: Session identifier
            limit: Maximum number of messages (None for all)
            include_summary: Include summary if available
            
        Returns:
            List of messages
        """
        session = await self.get_session(session_id)
        if not session:
            return []
        
        messages = session.messages if limit is None else session.messages[-limit:]
        
        # Optionally prepend summary as system message
        if include_summary and session.summary:
            summary_msg = ConversationMessage(
                role="system",
                content=f"Previous conversation summary: {session.summary}",
                timestamp=session.created_at,
                metadata={"is_summary": True},
            )
            messages = [summary_msg] + messages
        
        return messages
    
    async def update_session_metadata(
        self,
        session_id: str,
        metadata: Dict[str, Any],
        merge: bool = True,
    ):
        """
        Update session metadata.
        
        Args:
            session_id: Session identifier
            metadata: New metadata
            merge: If True, merge with existing; if False, replace
        """
        session = await self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        clean_metadata = self.sanitizer.sanitize_metadata(metadata)
        
        if merge:
            session.metadata.update(clean_metadata)
        else:
            session.metadata = clean_metadata
        
        session.updated_at = datetime.now()
        await self.store.save_session(session)
    
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete conversation session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if deleted successfully
        """
        # Invalidate summary cache
        self.summary_cache.invalidate(session_id)
        
        return await self.store.delete_session(session_id)
    
    async def list_user_sessions(
        self,
        user_id: str,
        limit: int = 10,
    ) -> List[ConversationSession]:
        """
        List sessions for a user.
        
        Args:
            user_id: User identifier
            limit: Maximum sessions to return
            
        Returns:
            List of sessions
        """
        return await self.store.list_user_sessions(user_id, limit)
    
    async def get_session_health(
        self,
        session_id: str,
    ) -> Optional[dict]:
        """
        Get health report for session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Health report or None if session not found
        """
        session = await self.get_session(session_id)
        if not session:
            return None
        
        return self.health_checker.check_session_health(session)
    
    async def cleanup_inactive_sessions(
        self,
        inactivity_hours: int = 24,
        dry_run: bool = False,
    ) -> List[str]:
        """
        Clean up inactive sessions.
        
        Args:
            inactivity_hours: Hours of inactivity before cleanup
            dry_run: If True, don't actually delete
            
        Returns:
            List of deleted session IDs
        """
        # This requires store to support listing all sessions
        # For now, return empty list
        # TODO: Implement when store supports iteration
        return []
    
    async def force_summarize(
        self,
        session_id: str,
    ) -> Optional[str]:
        """
        Force summarization of a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Summary text or None if failed
        """
        if not self.summarizer:
            return None
        
        session = await self.get_session(session_id)
        if not session:
            return None
        
        # Check cache first
        cached = self.summary_cache.get_summary(
            session_id,
            len(session.messages)
        )
        if cached:
            return cached
        
        # Generate summary
        summary = await self.summarizer.summarize_session(session)
        
        # Update session
        session.summary = summary
        session.updated_at = datetime.now()
        await self.store.save_session(session)
        
        # Cache it
        self.summary_cache.set_summary(
            session_id,
            len(session.messages),
            summary
        )
        
        return summary
    
    async def get_context_for_llm(
        self,
        session_id: str,
        max_messages: int = 10,
        include_summary: bool = True,
    ) -> List[Dict[str, str]]:
        """
        Get conversation context formatted for LLM.
        
        Args:
            session_id: Session identifier
            max_messages: Maximum recent messages
            include_summary: Include summary if available
            
        Returns:
            List of message dicts with role and content
        """
        messages = await self.get_conversation_history(
            session_id,
            limit=max_messages,
            include_summary=include_summary,
        )
        
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        return f"session_{uuid.uuid4().hex[:16]}"
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get memory manager statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            "summarization_enabled": self.enable_summarization,
            "validation_enabled": self.enable_validation,
            "cache_size": len(self.summary_cache._cache),
        }


class SessionContextBuilder:
    """
    Builds context for agents from conversation sessions.
    """
    
    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
    
    async def build_agent_context(
        self,
        session_id: str,
        include_metadata: bool = True,
        max_history: int = 5,
    ) -> Dict[str, Any]:
        """
        Build context dictionary for agents.
        
        Args:
            session_id: Session identifier
            include_metadata: Include session metadata
            max_history: Max messages in history
            
        Returns:
            Context dictionary
        """
        from agents.base import AgentContext
        
        session = await self.memory_manager.get_session(session_id)
        if not session:
            return AgentContext(session_id=session_id)
        
        # Get recent messages
        messages = session.get_recent_messages(max_history)
        
        # Format history
        history = [
            {"role": msg.role, "content": msg.content, "timestamp": msg.timestamp.isoformat()}
            for msg in messages
        ]
        
        return AgentContext(
            user_id=session.user_id,
            session_id=session_id,
            conversation_history=history,
            user_metadata=session.metadata if include_metadata else {},
        )