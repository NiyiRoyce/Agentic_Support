# tickets agent (stub)

from agents.base import BaseAgent, AgentContext, AgentResult, AgentType
from agents.tickets.schemas import TicketAgentOutput
from llm import LLMRouter, LLMMessage, LLMConfig


class TicketsAgent(BaseAgent):
    def __init__(self, llm_router: LLMRouter, default_config=None):
        super().__init__(
            llm_router=llm_router,
            agent_type=AgentType.TICKETS,
            default_config=default_config or LLMConfig(
                model="gpt-4o-mini",
                temperature=0.5,
                max_tokens=600,
                json_mode=True,
            ),
        )
        self.prompts = TicketPrompts()
    
    async def execute(self, user_message: str, context: AgentContext,
                     **kwargs) -> AgentResult:
        prompt = self.build_prompt(user_message, context)
        messages = [
            LLMMessage(role="system", content=self.prompts.SYSTEM_PROMPT),
            LLMMessage(role="user", content=prompt),
        ]
        
        response = await self._call_llm(messages)
        is_valid, parsed, error = self._parse_llm_json(response, TicketAgentOutput)
        
        if not is_valid:
            return self._create_error_result(f"Parse error: {error}")
        
        return self._create_success_result(
            data=parsed,
            confidence=0.85,
            reasoning="Ticket details generated"
        )
    
    def build_prompt(self, user_message: str, context: AgentContext, **kwargs) -> str:
        return self.prompts.build_ticket_creation_prompt(
            issue=user_message,
            user_info=context.user_metadata
        )
