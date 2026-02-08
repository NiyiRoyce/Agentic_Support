# Tool discovery and registration
"""Tool registry for discovery and management"""
from typing import Dict, List, Optional, Set
import logging
from collections import defaultdict

from execution.tools.base import BaseTool
from execution.models import ToolMetadata, ToolCategory

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Central registry for all tools"""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._metadata: Dict[str, ToolMetadata] = {}
        self._categories: Dict[ToolCategory, Set[str]] = defaultdict(set)
        self._tags: Dict[str, Set[str]] = defaultdict(set)
    
    def register(self, tool: BaseTool):
        """
        Register a tool
        
        Args:
            tool: Tool instance to register
            
        Raises:
            ValueError: If tool with same name already registered
        """
        if tool.name in self._tools:
            logger.warning(f"Tool '{tool.name}' already registered, overwriting")
        
        self._tools[tool.name] = tool
        metadata = tool.get_metadata()
        self._metadata[tool.name] = metadata
        
        # Index by category
        self._categories[tool.category].add(tool.name)
        
        # Index by tags
        for tag in metadata.tags:
            self._tags[tag].add(tool.name)
        
        logger.info(f"Registered tool: {tool.name} ({tool.category.value})")
    
    def register_many(self, tools: List[BaseTool]):
        """Register multiple tools"""
        for tool in tools:
            self.register(tool)
    
    def unregister(self, tool_name: str):
        """
        Unregister a tool
        
        Args:
            tool_name: Name of tool to unregister
        """
        if tool_name not in self._tools:
            logger.warning(f"Tool '{tool_name}' not registered")
            return
        
        tool = self._tools[tool_name]
        metadata = self._metadata[tool_name]
        
        # Remove from indices
        self._categories[tool.category].discard(tool_name)
        for tag in metadata.tags:
            self._tags[tag].discard(tool_name)
        
        # Remove from main registry
        del self._tools[tool_name]
        del self._metadata[tool_name]
        
        logger.info(f"Unregistered tool: {tool_name}")
    
    def get(self, tool_name: str) -> Optional[BaseTool]:
        """
        Get tool by name
        
        Args:
            tool_name: Name of tool
            
        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(tool_name)
    
    def get_metadata(self, tool_name: str) -> Optional[ToolMetadata]:
        """
        Get tool metadata
        
        Args:
            tool_name: Name of tool
            
        Returns:
            ToolMetadata or None if not found
        """
        return self._metadata.get(tool_name)
    
    def exists(self, tool_name: str) -> bool:
        """Check if tool is registered"""
        return tool_name in self._tools
    
    def list_all(self) -> List[str]:
        """List all registered tool names"""
        return list(self._tools.keys())
    
    def list_by_category(self, category: ToolCategory) -> List[str]:
        """
        List tools by category
        
        Args:
            category: Tool category
            
        Returns:
            List of tool names in category
        """
        return list(self._categories.get(category, set()))
    
    def list_by_tag(self, tag: str) -> List[str]:
        """
        List tools by tag
        
        Args:
            tag: Tag to filter by
            
        Returns:
            List of tool names with tag
        """
        return list(self._tags.get(tag, set()))
    
    def search(
        self,
        query: Optional[str] = None,
        category: Optional[ToolCategory] = None,
        tags: Optional[List[str]] = None,
        requires_auth: Optional[bool] = None,
    ) -> List[BaseTool]:
        """
        Search for tools by criteria
        
        Args:
            query: Search query (matches name or description)
            category: Filter by category
            tags: Filter by tags (tool must have all tags)
            requires_auth: Filter by auth requirement
            
        Returns:
            List of matching tools
        """
        results = list(self._tools.values())
        
        # Filter by category
        if category:
            results = [t for t in results if t.category == category]
        
        # Filter by tags
        if tags:
            results = [
                t for t in results
                if all(tag in self._metadata[t.name].tags for tag in tags)
            ]
        
        # Filter by auth
        if requires_auth is not None:
            results = [t for t in results if t.requires_auth == requires_auth]
        
        # Filter by query
        if query:
            query_lower = query.lower()
            results = [
                t for t in results
                if query_lower in t.name.lower()
                or query_lower in t.description.lower()
            ]
        
        return results
    
    def get_all_metadata(self) -> List[ToolMetadata]:
        """Get metadata for all registered tools"""
        return list(self._metadata.values())
    
    def get_statistics(self) -> Dict:
        """Get registry statistics"""
        return {
            "total_tools": len(self._tools),
            "by_category": {
                category.value: len(tools)
                for category, tools in self._categories.items()
            },
            "total_tags": len(self._tags),
            "tools_requiring_auth": sum(
                1 for t in self._tools.values() if t.requires_auth
            ),
        }
    
    def validate_tool_calls(self, tool_calls: List[Dict]) -> List[str]:
        """
        Validate that all tool calls reference registered tools
        
        Args:
            tool_calls: List of tool call dicts
            
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        for i, call in enumerate(tool_calls):
            tool_name = call.get("tool_name")
            if not tool_name:
                errors.append(f"Tool call {i}: missing 'tool_name'")
                continue
            
            if not self.exists(tool_name):
                errors.append(
                    f"Tool call {i}: unknown tool '{tool_name}'. "
                    f"Available tools: {self.list_all()}"
                )
        
        return errors