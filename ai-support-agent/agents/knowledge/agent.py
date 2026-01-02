# knowledge agent implementation (stub)
"""Knowledge retrieval agent using RAG."""

from typing import Optional, List

from agents.base import BaseAgent, AgentContext, AgentResult, AgentType
from agents.knowledge.schemas import KnowledgeResponse
from agents.knowledge.prompts import KnowledgePrompts
from llm import LLMRouter, LLMMessage, LLMConfig


class KnowledgeAgent(BaseAgent):
    """
    Agent responsible for answering questions using RAG (Retrieval Augmented Generation).
    
    This agent:
    1. Takes a user question
    2. Retrieves relevant context from knowledge base (handled externally)
    3. Generates answer based on retrieved context
    4. Evaluates confidence in the answer
    """
    
    def __init__(
        self,
        llm_router: LLMRouter,
        default_config: Optional[LLMConfig] = None,
    ):
        super().__init__(
            llm_router=llm_router,
            agent_type=AgentType.KNOWLEDGE,
            default_config=default_config or LLMConfig(
                model="gpt-4o-mini",
                temperature=0.7,
                max_tokens=800,
            ),
        )
        self.prompts = KnowledgePrompts()
    
    async def execute(
        self,
        user_message: str,
        context: AgentContext,
        retrieved_chunks: Optional[List[str]] = None,
        **kwargs,
    ) -> AgentResult:
        """
        Answer user question using retrieved knowledge base context.
        
        Args:
            user_message: The user's question
            context: Contextual information including history
            retrieved_chunks: List of retrieved knowledge base chunks
            
        Returns:
            AgentResult with answer and sources
        """
        # Handle greeting
        if self._is_greeting(user_message):
            return self._create_success_result(
                data={
                    "answer": self.prompts.build_greeting_response(),
                    "sources_used": [],
                    "requires_human": False,
                },
                confidence=1.0,
                reasoning="Standard greeting response",
            )
        
        # Check if we have context
        if not retrieved_chunks:
            return self._handle_no_context(user_message)
        
        # Build prompt with retrieved context
        prompt = self.build_prompt(
            user_message,
            context,
            retrieved_chunks=retrieved_chunks,
        )
        
        # Prepare messages
        messages = [
            LLMMessage(role="system", content=self.prompts.SYSTEM_PROMPT),
            LLMMessage(role="user", content=prompt),
        ]
        
        # Generate answer
        response = await self._call_llm(messages, self.default_config)
        
        if not response.success:
            return self._create_error_result(
                error=f"Failed to generate answer: {response.error}",
                metadata={
                    "tokens_used": response.tokens_used,
                    "cost": response.cost_usd,
                }
            )
        
        answer = response.content.strip()
        
        # Evaluate confidence
        confidence_score = await self._evaluate_confidence(
            question=user_message,
            answer=answer,
            sources=retrieved_chunks,
        )
        
        # Build result
        return self._create_success_result(
            data={
                "answer": answer,
                "sources_used": [f"Source {i+1}" for i in range(len(retrieved_chunks))],
                "requires_human": confidence_score < 0.5,
            },
            confidence=confidence_score,
            reasoning=f"Answer generated from {len(retrieved_chunks)} knowledge base sources",
            metadata={
                "tokens_used": response.tokens_used,
                "cost": response.cost_usd,
                "model": response.model,
                "provider": response.provider,
                "num_sources": len(retrieved_chunks),
            }
        )
    
    def build_prompt(
        self,
        user_message: str,
        context: AgentContext,
        retrieved_chunks: List[str],
        **kwargs,
    ) -> str:
        """Build prompt for knowledge-based question answering."""
        # Format conversation history
        history = self._format_conversation_history(context, max_messages=3)
        
        # Build RAG prompt
        return self.prompts.build_rag_prompt(
            question=user_message,
            context_chunks=retrieved_chunks,
            conversation_history=history,
        )
    
    async def _evaluate_confidence(
        self,
        question: str,
        answer: str,
        sources: List[str],
    ) -> float:
        """
        Evaluate confidence in the generated answer.
        
        Args:
            question: Original question
            answer: Generated answer
            sources: Sources used
            
        Returns:
            Confidence score 0.0-1.0
        """
        # Build evaluation prompt
        eval_prompt = self.prompts.build_confidence_evaluation_prompt(
            question=question,
            answer=answer,
            sources=[s[:200] for s in sources],  # Truncate for prompt
        )
        
        messages = [
            LLMMessage(role="system", content="You are an answer quality evaluator."),
            LLMMessage(role="user", content=eval_prompt),
        ]
        
        # Use JSON mode for structured output
        eval_config = LLMConfig(
            model=self.default_config.model,
            temperature=0.3,
            max_tokens=300,
            json_mode=True,
        )
        
        response = await self._call_llm(messages, eval_config)
        
        if response.success:
            is_valid, parsed, error = self._parse_llm_json(response)
            if is_valid and "confidence" in parsed:
                return parsed["confidence"]
        
        # Fallback: estimate based on answer characteristics
        return self._estimate_confidence_heuristic(answer, sources)
    
    def _estimate_confidence_heuristic(
        self,
        answer: str,
        sources: List[str],
    ) -> float:
        """
        Estimate confidence using heuristics.
        
        Args:
            answer: Generated answer
            sources: Sources used
            
        Returns:
            Estimated confidence score
        """
        confidence = 0.5  # Start at medium
        
        # Increase confidence if answer is substantial
        if len(answer) > 100:
            confidence += 0.1
        
        # Increase confidence if multiple sources
        if len(sources) >= 3:
            confidence += 0.1
        
        # Decrease confidence if answer indicates uncertainty
        uncertainty_phrases = [
            "i don't have",
            "i'm not sure",
            "might be",
            "possibly",
            "may be",
        ]
        if any(phrase in answer.lower() for phrase in uncertainty_phrases):
            confidence -= 0.2
        
        # Ensure within bounds
        return max(0.0, min(1.0, confidence))
    
    def _is_greeting(self, message: str) -> bool:
        """Check if message is a greeting."""
        greetings = ["hello", "hi", "hey", "good morning", "good afternoon"]
        message_lower = message.lower().strip()
        return any(
            message_lower.startswith(g) or message_lower == g
            for g in greetings
        )
    
    def _handle_no_context(self, question: str) -> AgentResult:
        """Handle case where no context was retrieved."""
        fallback = self.prompts.build_fallback_response(question)
        
        return self._create_success_result(
            data={
                "answer": fallback,
                "sources_used": [],
                "requires_human": True,
            },
            confidence=0.3,
            reasoning="No relevant context found in knowledge base",
            metadata={"no_context": True}
        )