# escalation agent (stub)

from agents.base import BaseAgent, AgentContext, AgentResult, AgentType
from agents.escalation.schemas import EscalationAgentOutput
from llm import LLMRouter, LLMMessage, LLMConfig


class EscalationAgent(BaseAgent):
    def __init__(self, llm_router: LLMRouter, default_config=None):
        super().__init__(
            llm_router=llm_router,
            agent_type=AgentType.ESCALATION,
            default_config=default_config or LLMConfig(
                model="gpt-4o-mini",
                temperature=0.3,
                max_tokens=400,
                json_mode=True,
            ),
        )
        self.prompts = EscalationPrompts()
    
    async def execute(self, user_message: str, context: AgentContext,
                     **kwargs) -> AgentResult:
        prompt = self.build_prompt(user_message, context)
        messages = [
            LLMMessage(role="system", content=self.prompts.SYSTEM_PROMPT),
            LLMMessage(role="user", content=prompt),
        ]
        
        response = await self._call_llm(messages)
        is_valid, parsed, error = self._parse_llm_json(response, EscalationAgentOutput)
        
        if not is_valid:
            return self._create_error_result(f"Parse error: {error}")
        
        return self._create_success_result(
            data=parsed,
            confidence=parsed.get("should_escalate", False) and 0.95 or 0.85,
            reasoning="Escalation decision made"
        )
    
    def build_prompt(self, user_message: str, context: AgentContext, **kwargs) -> str:
        history = self._format_conversation_history(context, max_messages=5)
        return self.prompts.build_escalation_prompt(history)
