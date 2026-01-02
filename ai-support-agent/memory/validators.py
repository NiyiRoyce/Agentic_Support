# validators for memory inputs
"""Validators for memory operations."""

from typing import List, Optional, Tuple
from datetime import datetime, timedelta

from memory.store import ConversationMessage, ConversationSession


class MemoryValidator:
    """
    Validates memory operations and data integrity.
    """
    
    def __init__(
        self,
        max_message_length: int = 10000,
        max_session_messages: int = 1000,
        max_session_age_days: int = 30,
    ):
        """
        Initialize validator.
        
        Args:
            max_message_length: Maximum characters per message
            max_session_messages: Maximum messages per session
            max_session_age_days: Maximum age for active sessions
        """
        self.max_message_length = max_message_length
        self.max_session_messages = max_session_messages
        self.max_session_age_days = max_session_age_days
    
    def validate_message(
        self,
        message: ConversationMessage,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a conversation message.
        
        Args:
            message: Message to validate
            
        Returns:
            (is_valid, error_message)
        """
        # Check role
        valid_roles = ["user", "assistant", "system"]
        if message.role not in valid_roles:
            return False, f"Invalid role: {message.role}. Must be one of {valid_roles}"
        
        # Check content
        if not message.content or not message.content.strip():
            return False, "Message content cannot be empty"
        
        if len(message.content) > self.max_message_length:
            return False, f"Message exceeds maximum length of {self.max_message_length} characters"
        
        # Check timestamp
        if message.timestamp > datetime.now():
            return False, "Message timestamp cannot be in the future"
        
        # Check for potential injection attacks
        if self._contains_suspicious_content(message.content):
            return False, "Message contains suspicious content"
        
        return True, None
    
    def validate_session(
        self,
        session: ConversationSession,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a conversation session.
        
        Args:
            session: Session to validate
            
        Returns:
            (is_valid, error_message)
        """
        # Check session ID
        if not session.session_id or not session.session_id.strip():
            return False, "Session ID cannot be empty"
        
        # Check message count
        if len(session.messages) > self.max_session_messages:
            return False, f"Session exceeds maximum of {self.max_session_messages} messages"
        
        # Check timestamps
        if session.created_at > datetime.now():
            return False, "Created timestamp cannot be in the future"
        
        if session.updated_at < session.created_at:
            return False, "Updated timestamp cannot be before created timestamp"
        
        # Check session age
        age = datetime.now() - session.created_at
        if age.days > self.max_session_age_days:
            return False, f"Session is older than {self.max_session_age_days} days"
        
        # Validate all messages
        for i, message in enumerate(session.messages):
            is_valid, error = self.validate_message(message)
            if not is_valid:
                return False, f"Invalid message at index {i}: {error}"
        
        return True, None
    
    def validate_message_sequence(
        self,
        messages: List[ConversationMessage],
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate message sequence for logical consistency.
        
        Args:
            messages: List of messages
            
        Returns:
            (is_valid, error_message)
        """
        if not messages:
            return True, None
        
        # Check timestamps are sequential
        for i in range(1, len(messages)):
            if messages[i].timestamp < messages[i-1].timestamp:
                return False, f"Message timestamps not sequential at index {i}"
        
        # Check for alternating user/assistant pattern (optional warning)
        user_assistant_count = sum(
            1 for m in messages
            if m.role in ["user", "assistant"]
        )
        
        if user_assistant_count >= 4:
            # Check if messages alternate properly
            last_role = None
            violations = 0
            
            for msg in messages:
                if msg.role in ["user", "assistant"]:
                    if last_role == msg.role:
                        violations += 1
                    last_role = msg.role
            
            # Allow some violations but warn if excessive
            if violations > len(messages) * 0.3:  # More than 30% violations
                return True, "Warning: Message sequence has unusual role pattern"
        
        return True, None
    
    def _contains_suspicious_content(self, content: str) -> bool:
        """
        Check for suspicious content patterns.
        
        Args:
            content: Message content
            
        Returns:
            True if suspicious
        """
        # Check for SQL injection attempts
        sql_patterns = ["DROP TABLE", "DELETE FROM", "INSERT INTO", "UPDATE SET"]
        if any(pattern in content.upper() for pattern in sql_patterns):
            return True
        
        # Check for script injection
        script_patterns = ["<script", "javascript:", "onerror=", "onclick="]
        if any(pattern in content.lower() for pattern in script_patterns):
            return True
        
        # Check for excessive special characters (possible encoding attack)
        special_char_ratio = sum(
            1 for c in content
            if not c.isalnum() and not c.isspace()
        ) / max(len(content), 1)
        
        if special_char_ratio > 0.5:  # More than 50% special characters
            return True
        
        return False


class ContentSanitizer:
    """
    Sanitizes content before storage.
    """
    
    @staticmethod
    def sanitize_message(content: str) -> str:
        """
        Sanitize message content.
        
        Args:
            content: Raw content
            
        Returns:
            Sanitized content
        """
        # Remove null bytes
        sanitized = content.replace('\x00', '')
        
        # Normalize whitespace
        sanitized = ' '.join(sanitized.split())
        
        # Remove control characters (except newlines and tabs)
        sanitized = ''.join(
            char for char in sanitized
            if char >= ' ' or char in ['\n', '\t']
        )
        
        # Trim to reasonable length
        max_length = 10000
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length] + "... [truncated]"
        
        return sanitized.strip()
    
    @staticmethod
    def sanitize_metadata(metadata: dict) -> dict:
        """
        Sanitize metadata dictionary.
        
        Args:
            metadata: Raw metadata
            
        Returns:
            Sanitized metadata
        """
        sanitized = {}
        
        for key, value in metadata.items():
            # Sanitize key
            clean_key = str(key).strip()
            if not clean_key or len(clean_key) > 100:
                continue
            
            # Sanitize value
            if isinstance(value, str):
                clean_value = ContentSanitizer.sanitize_message(value)
            elif isinstance(value, (int, float, bool)):
                clean_value = value
            elif isinstance(value, (list, dict)):
                # Limit nested structure depth
                clean_value = value  # Could add recursive sanitization
            else:
                clean_value = str(value)
            
            sanitized[clean_key] = clean_value
        
        return sanitized


class SessionHealthChecker:
    """
    Checks health and quality of conversation sessions.
    """
    
    def check_session_health(
        self,
        session: ConversationSession,
    ) -> dict:
        """
        Check overall session health.
        
        Args:
            session: Session to check
            
        Returns:
            Health report dictionary
        """
        report = {
            "is_healthy": True,
            "issues": [],
            "warnings": [],
            "metrics": {},
        }
        
        # Check message count
        msg_count = len(session.messages)
        report["metrics"]["message_count"] = msg_count
        
        if msg_count == 0:
            report["is_healthy"] = False
            report["issues"].append("Session has no messages")
        elif msg_count > 100:
            report["warnings"].append("Session has many messages (>100)")
        
        # Check session age
        age = datetime.now() - session.created_at
        report["metrics"]["age_hours"] = age.total_seconds() / 3600
        
        if age.days > 7:
            report["warnings"].append("Session older than 7 days")
        
        # Check activity
        last_update = datetime.now() - session.updated_at
        report["metrics"]["hours_since_update"] = last_update.total_seconds() / 3600
        
        if last_update.days > 1:
            report["warnings"].append("No activity in over 24 hours")
        
        # Check message balance (user vs assistant)
        user_messages = sum(1 for m in session.messages if m.role == "user")
        assistant_messages = sum(1 for m in session.messages if m.role == "assistant")
        
        report["metrics"]["user_messages"] = user_messages
        report["metrics"]["assistant_messages"] = assistant_messages
        
        if user_messages > 0:
            ratio = assistant_messages / user_messages
            if ratio < 0.5:
                report["warnings"].append("Low assistant response rate")
            elif ratio > 2.0:
                report["warnings"].append("High assistant response rate")
        
        # Check for errors in metadata
        if "error_count" in session.metadata:
            error_count = session.metadata["error_count"]
            report["metrics"]["error_count"] = error_count
            
            if error_count > 5:
                report["is_healthy"] = False
                report["issues"].append("High error count in session")
        
        return report
    
    def should_archive(
        self,
        session: ConversationSession,
        inactivity_hours: int = 24,
    ) -> bool:
        """
        Determine if session should be archived.
        
        Args:
            session: Session to check
            inactivity_hours: Hours of inactivity before archiving
            
        Returns:
            True if should be archived
        """
        last_update = datetime.now() - session.updated_at
        return last_update.total_seconds() / 3600 > inactivity_hours
    
    def should_summarize(
        self,
        session: ConversationSession,
        message_threshold: int = 20,
    ) -> bool:
        """
        Determine if session should be summarized.
        
        Args:
            session: Session to check
            message_threshold: Message count threshold
            
        Returns:
            True if should be summarized
        """
        return (
            len(session.messages) >= message_threshold
            and session.summary is None
        )