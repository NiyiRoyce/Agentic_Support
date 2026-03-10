# orders agent (stub)

from agents.base import BaseAgent, AgentContext, AgentResult, AgentType
from llm import LLMRouter, LLMMessage, LLMConfig


class OrdersAgent(BaseAgent):
    def __init__(self, llm_router: LLMRouter, default_config=None):
        super().__init__(
            llm_router=llm_router,
            agent_type=AgentType.ORDERS,
            default_config=default_config or LLMConfig(
                model="gpt-4o-mini",
                temperature=0.7,
                max_tokens=400,
            ),
        )
        self.prompts = OrderPrompts()
    
    async def execute(self, user_message: str, context: AgentContext, 
                     order_data: dict = None, **kwargs) -> AgentResult:
        if not order_data:
            return self._create_error_result("No order data provided")
        
        prompt = self.build_prompt(user_message, context, order_data=order_data)
        messages = [
            LLMMessage(role="system", content=self.prompts.SYSTEM_PROMPT),
            LLMMessage(role="user", content=prompt),
        ]
        
        response = await self._call_llm(messages)
        
        if not response.success:
            return self._create_error_result(f"LLM error: {response.error}")
        
        return self._create_success_result(
            data={
                "response_message": response.content.strip(),
                "order_info": order_data,
                "needs_escalation": False,
            },
            confidence=0.9,
            reasoning="Order status response generated"
        )
    
    def build_prompt(self, user_message: str, context: AgentContext,
                    order_data: dict, **kwargs) -> str:
        order_id = order_data.get("order_id", "Unknown")
        return self.prompts.build_order_status_prompt(order_id, order_data)

