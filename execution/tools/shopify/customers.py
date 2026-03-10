# shopify customers helper
"""Shopify customer tools"""
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from execution.tools.base import BaseTool
from execution.models import ToolResult, ToolStatus, ToolCategory
from execution.core.context import ExecutionContext
from .client import ShopifyClient

logger = logging.getLogger(__name__)


class ShopifyGetCustomerTool(BaseTool):
    """Get Shopify customer by ID or email"""
    
    def __init__(self):
        super().__init__(
            name="shopify_get_customer",
            description="Retrieve a Shopify customer by ID or email",
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
            
            # Search by customer_id or email
            if "customer_id" in params:
                customer_id = params["customer_id"]
                response = await client.get(f"customers/{customer_id}")
                customer = response.get("customer", {})
            elif "email" in params:
                email = params["email"]
                response = await client.get("customers/search", params={"query": f"email:{email}"})
                customers = response.get("customers", [])
                customer = customers[0] if customers else {}
            else:
                raise ValueError("Either customer_id or email must be provided")
            
            await client.close()
            
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                data={
                    "customer": customer,
                    "customer_id": customer.get("id"),
                    "email": customer.get("email"),
                    "first_name": customer.get("first_name"),
                    "last_name": customer.get("last_name"),
                    "total_spent": customer.get("total_spent"),
                    "orders_count": customer.get("orders_count"),
                },
                execution_time_ms=execution_time,
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"Failed to get Shopify customer: {e}")
            
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
                "customer_id": {"type": "string"},
                "email": {"type": "string", "format": "email"},
            },
            "required": ["shop_name", "access_token"],
            "oneOf": [
                {"required": ["customer_id"]},
                {"required": ["email"]},
            ],
        }


class ShopifyUpdateCustomerTool(BaseTool):
    """Update Shopify customer information"""
    
    def __init__(self):
        super().__init__(
            name="shopify_update_customer",
            description="Update a Shopify customer's information",
            category=ToolCategory.ECOMMERCE,
            requires_auth=True,
            timeout_seconds=30,
            idempotent=False,
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
            
            customer_id = params["customer_id"]
            updates = params["updates"]
            
            # Update customer
            response = await client.put(
                f"customers/{customer_id}",
                data={"customer": updates}
            )
            
            await client.close()
            
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                data=response,
                execution_time_ms=execution_time,
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"Failed to update Shopify customer: {e}")
            
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
                "customer_id": {"type": "string"},
                "updates": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string", "format": "email"},
                        "first_name": {"type": "string"},
                        "last_name": {"type": "string"},
                        "phone": {"type": "string"},
                        "note": {"type": "string"},
                    },
                },
            },
            "required": ["shop_name", "access_token", "customer_id", "updates"],
        }