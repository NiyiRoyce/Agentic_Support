# json validator guardrail
"""JSON validation and repair for LLM outputs."""

import json
import re
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel, ValidationError


class JSONValidator:
    """
    Validates and repairs JSON output from LLMs.
    """

    @staticmethod
    def extract_json(text: str) -> Optional[str]:
        """
        Extract JSON from text that may contain markdown code blocks or extra text.
        """
        # Try to find JSON in markdown code blocks
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            return json_match.group(1)

        # Try to find JSON in regular code blocks
        json_match = re.search(r'```\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            return json_match.group(1)

        # Try to find raw JSON object
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            return json_match.group(0)

        return None

    @staticmethod
    def validate_json(text: str) -> tuple[bool, Optional[Dict], Optional[str]]:
        """
        Validate JSON string.
        Returns (is_valid, parsed_json, error_message)
        """
        # First try to extract JSON
        json_str = JSONValidator.extract_json(text)
        if not json_str:
            return False, None, "No JSON found in text"

        try:
            parsed = json.loads(json_str)
            return True, parsed, None
        except json.JSONDecodeError as e:
            return False, None, f"JSON decode error: {str(e)}"

    @staticmethod
    def validate_with_schema(
        text: str,
        schema: Type[BaseModel],
    ) -> tuple[bool, Optional[BaseModel], Optional[str]]:
        """
        Validate JSON against Pydantic schema.
        Returns (is_valid, parsed_model, error_message)
        """
        is_valid, parsed_json, error = JSONValidator.validate_json(text)

        if not is_valid:
            return False, None, error

        try:
            model = schema(**parsed_json)
            return True, model, None
        except ValidationError as e:
            return False, None, f"Schema validation error: {str(e)}"

    @staticmethod
    def repair_json(text: str) -> Optional[str]:
        """
        Attempt to repair malformed JSON.
        """
        json_str = JSONValidator.extract_json(text)
        if not json_str:
            return None

        # Common repairs
        repairs = [
            # Add missing closing braces
            lambda s: s + '}' * (s.count('{') - s.count('}')),
            # Add missing closing brackets
            lambda s: s + ']' * (s.count('[') - s.count(']')),
            # Remove trailing commas
            lambda s: re.sub(r',\s*([}\]])', r'\1', s),
            # Fix unquoted keys
            lambda s: re.sub(r'(\w+):', r'"\1":', s),
        ]

        for repair_func in repairs:
            try:
                repaired = repair_func(json_str)
                json.loads(repaired)  # Test if valid
                return repaired
            except:
                continue

        return None

    @staticmethod
    def ensure_json_response(text: str, max_retries: int = 2) -> Optional[Dict]:
        """
        Ensure we get valid JSON from LLM response, with repair attempts.
        """
        # Try direct validation
        is_valid, parsed, _ = JSONValidator.validate_json(text)
        if is_valid:
            return parsed

        # Try repair
        for _ in range(max_retries):
            repaired = JSONValidator.repair_json(text)
            if repaired:
                try:
                    return json.loads(repaired)
                except:
                    continue

        return None