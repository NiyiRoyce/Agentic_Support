# validators for execution inputs
"""Input and output validation"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, ValidationError as PydanticValidationError
import jsonschema
from jsonschema import validate, ValidationError as JsonSchemaValidationError

from execution.models import ValidationError
from execution.tools.base import BaseTool


class ValidationResult(BaseModel):
    """Result of validation"""
    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []


class ExecutionValidator:
    """Validates tool parameters and outputs"""
    
    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode
    
    async def validate_params(
        self,
        tool: BaseTool,
        params: Dict[str, Any],
    ) -> ValidationResult:
        """
        Validate tool parameters against schema
        
        Args:
            tool: Tool to validate for
            params: Parameters to validate
            
        Returns:
            ValidationResult with errors/warnings
        """
        errors = []
        warnings = []
        
        try:
            # Get parameter schema
            schema = tool.get_parameter_schema()
            
            # Validate against JSON schema
            validate(instance=params, schema=schema)
            
            # Run tool-specific validation
            is_valid = await tool.validate(params)
            if not is_valid:
                errors.append("Tool-specific validation failed")
            
        except JsonSchemaValidationError as e:
            errors.append(f"Schema validation failed: {e.message}")
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
        
        # Check for missing required params
        if "required" in schema:
            missing = set(schema["required"]) - set(params.keys())
            if missing:
                errors.append(f"Missing required parameters: {missing}")
        
        # Check for unexpected params (warning only)
        if "properties" in schema:
            unexpected = set(params.keys()) - set(schema["properties"].keys())
            if unexpected:
                warnings.append(f"Unexpected parameters: {unexpected}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
    
    async def validate_result(
        self,
        tool: BaseTool,
        result: Dict[str, Any],
    ) -> ValidationResult:
        """
        Validate tool result against response schema
        
        Args:
            tool: Tool that produced result
            result: Result data to validate
            
        Returns:
            ValidationResult
        """
        errors = []
        warnings = []
        
        response_schema = tool.get_response_schema()
        if not response_schema:
            # No schema to validate against
            return ValidationResult(is_valid=True)
        
        try:
            validate(instance=result, schema=response_schema)
        except JsonSchemaValidationError as e:
            errors.append(f"Response schema validation failed: {e.message}")
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
    
    def validate_execution_plan(
        self,
        tool_calls: List[Dict[str, Any]],
        available_tools: List[str],
    ) -> ValidationResult:
        """
        Validate execution plan
        
        Args:
            tool_calls: List of tool call dicts
            available_tools: List of available tool names
            
        Returns:
            ValidationResult
        """
        errors = []
        warnings = []
        
        for i, call in enumerate(tool_calls):
            # Check required fields
            if "tool_name" not in call:
                errors.append(f"Tool call {i}: missing 'tool_name'")
                continue
            
            if "params" not in call:
                errors.append(f"Tool call {i}: missing 'params'")
                continue
            
            # Check tool exists
            tool_name = call["tool_name"]
            if tool_name not in available_tools:
                errors.append(
                    f"Tool call {i}: unknown tool '{tool_name}'. "
                    f"Available: {available_tools}"
                )
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )