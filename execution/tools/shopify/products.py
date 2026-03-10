# shopify products helper
v"""Shopify product tools"""
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from execution.tools.base import BaseTool
from execution.models import ToolResult, ToolStatus, ToolCategory
from execution.core.context import ExecutionContext
from .client import ShopifyClient

logger = logging.getLogger(__name__)


class ShopifySearchProductsTool(BaseTool):
    """Search Shopify products"""
    
    def __init__(self):
        super().__init__(
            name="shopify_search_products",
            description="Search for Shopify products by query",
            category=ToolCategory.ECOMMERCE,
            requires_auth=True,
            timeout_seconds=30,
            idempotent=True,
        )
    
    async def execute(
        self,
        params: Dict[str, Any],
        context: Optional[ExecutionContext] = None,
    ) -> ToolResult:
        start_time = datetime.utcnow()
        
        try:
            client = ShopifyClient(
                shop_name=params["shop_name"],
                access_token=params["access_token"],
            )
            
            query = params.get("query", "")
            limit = params.get("limit", 10)
            
            # Search products
            response = await client.get(
                "products",
                params={"title": query, "limit": limit}
            )
            
            products = response.get("products", [])
            
            await client.close()
            
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                data={
                    "products": products,
                    "count": len(products),
                },
                execution_time_ms=execution_time,
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"Failed to search Shopify products: {e}")
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=str(e),
                execution_time_ms=execution_time,
            )
    
    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "shop_name": {"type": "string"},
                "access_token": {"type": "string"},
                "query": {"type": "string", "description": "Search query"},
                "limit": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 250,
                },
            },
            "required": ["shop_name", "access_token"],
        }


class ShopifyGetProductTool(BaseTool):
    """Get Shopify product by ID"""
    
    def __init__(self):
        super().__init__(
            name="shopify_get_product",
            description="Retrieve a Shopify product by ID",
            category=ToolCategory.ECOMMERCE,
            requires_auth=True,
            timeout_seconds=30,
            idempotent=True,
        )
    
    async def execute(
        self,
        params: Dict[str, Any],
        context: Optional[ExecutionContext] = None,
    ) -> ToolResult:
        start_time = datetime.utcnow()
        
        try:
            client = ShopifyClient(
                shop_name=params["shop_name"],
                access_token=params["access_token"],
            )
            
            product_id = params["product_id"]
            
            # Get product
            response = await client.get(f"products/{product_id}")
            product = response.get("product", {})
            
            await client.close()
            
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                data={
                    "product": product,
                    "product_id": product.get("id"),
                    "title": product.get("title"),
                    "price": product.get("variants", [{}])[0].get("price"),
                    "inventory": product.get("variants", [{}])[0].get("inventory_quantity"),
                },
                execution_time_ms=execution_time,
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"Failed to get Shopify product: {e}")
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=str(e),
                execution_time_ms=execution_time,
            )
    
    def get_parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "shop_name": {"type": "string"},
                "access_token": {"type": "string"},
                "product_id": {"type": "string"},
            },
            "required": ["shop_name", "access_token", "product_id"],
        }