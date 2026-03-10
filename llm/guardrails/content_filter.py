# content filter guardrail
"""Content filtering and safety checks for LLM outputs."""

import re
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class ContentFilterResult:
    """Result of content filtering."""
    is_safe: bool
    violations: List[str]
    sanitized_content: Optional[str] = None


class ContentFilter:
    """
    Filters and validates LLM outputs for safety and policy compliance.
    """

    def __init__(self):
        # Patterns for PII detection
        self.pii_patterns = {
            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "phone": r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
            "ssn": r'\b\d{3}-\d{2}-\d{4}\b',
            "credit_card": r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
        }

        # Prohibited content keywords (customize based on your policy)
        self.prohibited_keywords = [
            "password",
            "secret_key",
            "api_key",
            "private_key",
        ]

    def check_content(self, content: str) -> ContentFilterResult:
        """
        Check content for policy violations.
        """
        violations = []

        # Check for PII
        for pii_type, pattern in self.pii_patterns.items():
            if re.search(pattern, content, re.IGNORECASE):
                violations.append(f"Contains {pii_type}")

        # Check for prohibited keywords
        for keyword in self.prohibited_keywords:
            if keyword.lower() in content.lower():
                violations.append(f"Contains prohibited keyword: {keyword}")

        # Check content length
        if len(content) > 10000:
            violations.append("Content exceeds maximum length")

        is_safe = len(violations) == 0

        return ContentFilterResult(
            is_safe=is_safe,
            violations=violations,
            sanitized_content=self.sanitize_content(content) if not is_safe else None,
        )

    def sanitize_content(self, content: str) -> str:
        """
        Remove or mask sensitive information from content.
        """
        sanitized = content

        # Mask emails
        sanitized = re.sub(
            self.pii_patterns["email"],
            "[EMAIL_REDACTED]",
            sanitized,
        )

        # Mask phone numbers
        sanitized = re.sub(
            self.pii_patterns["phone"],
            "[PHONE_REDACTED]",
            sanitized,
        )

        # Mask SSN
        sanitized = re.sub(
            self.pii_patterns["ssn"],
            "[SSN_REDACTED]",
            sanitized,
        )

        # Mask credit cards
        sanitized = re.sub(
            self.pii_patterns["credit_card"],
            "[CARD_REDACTED]",
            sanitized,
        )

        return sanitized

    def check_for_hallucination_markers(self, content: str) -> bool:
        """
        Check for common hallucination markers in LLM outputs.
        """
        hallucination_markers = [
            "I don't have access to",
            "I cannot verify",
            "I don't have real-time",
            "as of my knowledge cutoff",
            "I'm not sure",
            "I cannot confirm",
        ]

        return any(marker.lower() in content.lower() for marker in hallucination_markers)

    def validate_output_format(self, content: str, expected_format: str) -> bool:
        """
        Validate that output matches expected format.
        """
        if expected_format == "json":
            try:
                import json
                json.loads(content)
                return True
            except:
                return False

        elif expected_format == "markdown":
            # Basic markdown validation
            return bool(re.search(r'[#*\-\[\]]', content))

        return True  # Default to true for unknown formats


class OutputValidator:
    """
    Validates LLM outputs meet business requirements.
    """

    @staticmethod
    def validate_customer_support_response(content: str) -> tuple[bool, List[str]]:
        """
        Validate customer support response quality.
        """
        issues = []

        # Check minimum length
        if len(content) < 20:
            issues.append("Response too short")

        # Check for helpful indicators
        helpful_phrases = [
            "help",
            "assist",
            "support",
            "information",
            "let me",
            "I can",
        ]
        if not any(phrase in content.lower() for phrase in helpful_phrases):
            issues.append("Response may not be helpful")

        # Check for politeness
        polite_phrases = ["please", "thank you", "sorry", "apologize"]
        has_politeness = any(phrase in content.lower() for phrase in polite_phrases)

        # Check for negative tone (optional warning)
        negative_words = ["can't", "cannot", "won't", "unable", "impossible"]
        negative_count = sum(1 for word in negative_words if word in content.lower())

        if negative_count > 2 and not has_politeness:
            issues.append("Response may be too negative without polite framing")

        return len(issues) == 0, issues