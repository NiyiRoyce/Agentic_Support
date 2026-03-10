# summarizer
"""Conversation summarization for memory compression."""

from typing import List, Optional
from datetime import datetime

from memory.store import ConversationMessage, ConversationSession
from llm import LLMRouter, LLMMessage, LLMConfig


class ConversationSummarizer:
    """
    Summarizes conversations to reduce memory footprint.
    
    Useful for:
    - Long conversations that exceed context windows
    - Reducing token costs
    - Preserving conversation history efficiently
    """
    
    def __init__(
        self,
        llm_router: LLMRouter,
        summary_trigger_threshold: int = 20,  # Messages before summarizing
        preserve_recent_messages: int = 5,    # Recent messages to keep
    ):
        """
        Initialize summarizer.
        
        Args:
            llm_router: LLM router for generating summaries
            summary_trigger_threshold: Number of messages before triggering summary
            preserve_recent_messages: Number of recent messages to preserve
        """
        self.llm_router = llm_router
        self.summary_trigger_threshold = summary_trigger_threshold
        self.preserve_recent_messages = preserve_recent_messages
    
    async def should_summarize(self, session: ConversationSession) -> bool:
        """
        Determine if session should be summarized.
        
        Args:
            session: Conversation session
            
        Returns:
            True if summarization needed
        """
        return session.get_message_count() >= self.summary_trigger_threshold
    
    async def summarize_session(
        self,
        session: ConversationSession,
        include_metadata: bool = True,
    ) -> str:
        """
        Generate summary of conversation session.
        
        Args:
            session: Conversation session to summarize
            include_metadata: Include metadata in summary
            
        Returns:
            Summary text
        """
        # Format conversation for summarization
        conversation_text = self._format_conversation(session.messages)
        
        # Build prompt
        prompt = self._build_summary_prompt(
            conversation_text,
            session.metadata if include_metadata else {}
        )
        
        # Generate summary
        messages = [
            LLMMessage(role="system", content=self._get_system_prompt()),
            LLMMessage(role="user", content=prompt),
        ]
        
        config = LLMConfig(
            model="gpt-4o-mini",
            temperature=0.3,  # Lower temperature for consistent summaries
            max_tokens=500,
        )
        
        response = await self.llm_router.complete(messages, config)
        
        if response.success:
            return response.content.strip()
        else:
            # Fallback to basic summary
            return self._create_basic_summary(session)
    
    async def summarize_and_compress(
        self,
        session: ConversationSession,
    ) -> ConversationSession:
        """
        Summarize conversation and compress by removing old messages.
        
        Args:
            session: Conversation session
            
        Returns:
            Compressed session with summary
        """
        # Generate summary
        summary = await self.summarize_session(session)
        
        # Keep only recent messages
        recent_messages = session.get_recent_messages(self.preserve_recent_messages)
        
        # Create compressed session
        compressed = ConversationSession(
            session_id=session.session_id,
            user_id=session.user_id,
            messages=recent_messages,
            created_at=session.created_at,
            updated_at=datetime.now(),
            metadata=session.metadata,
            summary=summary,
        )
        
        return compressed
    
    async def summarize_partial(
        self,
        messages: List[ConversationMessage],
        context: Optional[str] = None,
    ) -> str:
        """
        Summarize a portion of conversation.
        
        Args:
            messages: Messages to summarize
            context: Optional context from previous summaries
            
        Returns:
            Summary text
        """
        conversation_text = self._format_conversation(messages)
        
        prompt = f"""Summarize this conversation segment concisely:

{conversation_text}

Previous context: {context or 'None'}

Provide a brief summary focusing on:
1. Main topics discussed
2. Key decisions or actions
3. Outstanding questions or issues

Keep it under 150 words."""
        
        messages_llm = [
            LLMMessage(role="system", content=self._get_system_prompt()),
            LLMMessage(role="user", content=prompt),
        ]
        
        config = LLMConfig(
            model="gpt-4o-mini",
            temperature=0.3,
            max_tokens=300,
        )
        
        response = await self.llm_router.complete(messages_llm, config)
        
        return response.content.strip() if response.success else "Conversation segment"
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for summarization."""
        return """You are a conversation summarizer for a customer support system.

Your job is to create concise, accurate summaries of customer conversations.

Guidelines:
1. Focus on key information: issues, questions, resolutions
2. Preserve important details (order numbers, product names, dates)
3. Note customer sentiment if relevant
4. Keep it factual and objective
5. Be concise but complete (150-200 words)

Format:
- Start with a one-sentence overview
- List key points as bullet points
- End with current status or next steps if applicable"""
    
    def _build_summary_prompt(
        self,
        conversation: str,
        metadata: dict,
    ) -> str:
        """Build prompt for conversation summarization."""
        return f"""Summarize this customer support conversation:

CONVERSATION:
{conversation}

SESSION METADATA:
{metadata}

Provide a comprehensive summary that captures:
- Customer's main concern or question
- Key information exchanged
- Any issues or problems mentioned
- Resolution or current status
- Important details (IDs, dates, etc.)

Keep the summary concise but complete."""
    
    def _format_conversation(
        self,
        messages: List[ConversationMessage],
    ) -> str:
        """Format messages for summarization."""
        formatted = []
        for msg in messages:
            timestamp = msg.timestamp.strftime("%Y-%m-%d %H:%M")
            formatted.append(f"[{timestamp}] {msg.role.upper()}: {msg.content}")
        return "\n".join(formatted)
    
    def _create_basic_summary(self, session: ConversationSession) -> str:
        """Create basic summary without LLM."""
        msg_count = session.get_message_count()
        user_messages = [m for m in session.messages if m.role == "user"]
        
        summary_parts = [
            f"Conversation with {msg_count} messages.",
        ]
        
        if user_messages:
            first_msg = user_messages[0].content[:100]
            summary_parts.append(f"Started with: {first_msg}...")
        
        return " ".join(summary_parts)


class ProgressiveSummarizer:
    """
    Progressive summarization that maintains hierarchical summaries.
    
    Useful for very long conversations where multiple levels of
    summarization are needed.
    """
    
    def __init__(
        self,
        llm_router: LLMRouter,
        chunk_size: int = 10,  # Messages per chunk
    ):
        self.llm_router = llm_router
        self.chunk_size = chunk_size
        self.summarizer = ConversationSummarizer(llm_router)
    
    async def summarize_progressive(
        self,
        session: ConversationSession,
    ) -> dict:
        """
        Create progressive summary with multiple levels.
        
        Args:
            session: Conversation session
            
        Returns:
            Dict with summaries at different levels
        """
        messages = session.messages
        
        # Level 1: Chunk summaries
        chunk_summaries = []
        for i in range(0, len(messages), self.chunk_size):
            chunk = messages[i:i + self.chunk_size]
            if len(chunk) > 0:
                summary = await self.summarizer.summarize_partial(chunk)
                chunk_summaries.append(summary)
        
        # Level 2: Summary of summaries (if many chunks)
        meta_summary = None
        if len(chunk_summaries) > 3:
            # Create meta-summary from chunk summaries
            combined = "\n\n".join([
                f"Segment {i+1}: {s}"
                for i, s in enumerate(chunk_summaries)
            ])
            
            messages_llm = [
                LLMMessage(
                    role="system",
                    content="Summarize these conversation segment summaries into a cohesive overview."
                ),
                LLMMessage(role="user", content=combined),
            ]
            
            response = await self.llm_router.complete(
                messages_llm,
                LLMConfig(model="gpt-4o-mini", temperature=0.3, max_tokens=400)
            )
            
            if response.success:
                meta_summary = response.content.strip()
        
        return {
            "chunk_summaries": chunk_summaries,
            "meta_summary": meta_summary or "\n\n".join(chunk_summaries),
            "total_chunks": len(chunk_summaries),
            "total_messages": len(messages),
        }


class SummaryCache:
    """
    Cache for conversation summaries to avoid regeneration.
    """
    
    def __init__(self):
        self._cache: dict = {}
    
    def get_summary(
        self,
        session_id: str,
        message_count: int,
    ) -> Optional[str]:
        """
        Get cached summary if available and fresh.
        
        Args:
            session_id: Session ID
            message_count: Current message count
            
        Returns:
            Cached summary or None
        """
        key = f"{session_id}:{message_count}"
        return self._cache.get(key)
    
    def set_summary(
        self,
        session_id: str,
        message_count: int,
        summary: str,
    ):
        """
        Cache a summary.
        
        Args:
            session_id: Session ID
            message_count: Message count at time of summary
            summary: Summary text
        """
        key = f"{session_id}:{message_count}"
        self._cache[key] = summary
    
    def invalidate(self, session_id: str):
        """Invalidate all summaries for a session."""
        keys_to_remove = [
            k for k in self._cache.keys()
            if k.startswith(f"{session_id}:")
        ]
        for key in keys_to_remove:
            del self._cache[key]
    
    def clear(self):
        """Clear entire cache."""
        self._cache.clear()