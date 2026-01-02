# prompts for orders agent

class OrderPrompts:
    SYSTEM_PROMPT = """You are an order management assistant.
    
    Generate helpful, accurate responses about order status, tracking, and delivery.
    Be concise, friendly, and provide specific details from the order data."""
    
    @staticmethod
    def build_order_status_prompt(order_id: str, order_data: dict) -> str:
        return f"""Generate a friendly response about this order:

Order ID: {order_id}
Order Data: {order_data}

Create a natural response that:
1. Confirms the order number
2. Explains current status
3. Provides tracking info if available
4. Offers to help with anything else

Keep it brief and conversational."""