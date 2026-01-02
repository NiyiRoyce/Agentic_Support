# prompts for knowledge agent
"""Prompts for Knowledge Agent."""

from typing import List


class KnowledgePrompts:
    """Prompt templates for knowledge retrieval agent."""
    
    SYSTEM_PROMPT = """You are a helpful customer support assistant with access to a knowledge base.

Your job is to answer customer questions accurately based on the provided knowledge base context.

Guidelines:
1. ONLY use information from the provided knowledge base context
2. If the context doesn't contain the answer, clearly say "I don't have that information in my knowledge base"
3. Be concise but complete - include all relevant details
4. Use a friendly, professional tone
5. If you're unsure or the information is incomplete, acknowledge it
6. Cite specific details when relevant (policies, dates, numbers)
7. If the question requires human expertise or is beyond the knowledge base, indicate this

Never make up information. It's better to admit you don't know than to provide incorrect information."""
    
    @staticmethod
    def build_rag_prompt(
        question: str,
        context_chunks: List[str],
        conversation_history: str,
    ) -> str:
        """Build prompt for RAG-based question answering."""
        # Format context
        context = "\n\n---\n\n".join([
            f"[Source {i+1}]\n{chunk}"
            for i, chunk in enumerate(context_chunks)
        ])
        
        return f"""Answer the customer's question based on the knowledge base context below.

CUSTOMER QUESTION: "{question}"

KNOWLEDGE BASE CONTEXT:
{context}

CONVERSATION HISTORY:
{conversation_history}

Provide a clear, helpful answer based ONLY on the information in the knowledge base context above. If the answer isn't in the context, say so clearly.

Your response should be:
- Accurate (based only on provided context)
- Helpful and conversational
- Appropriately detailed
- Professional and friendly"""
    
    @staticmethod
    def build_confidence_evaluation_prompt(
        question: str,
        answer: str,
        sources: List[str],
    ) -> str:
        """Build prompt to evaluate answer confidence."""
        sources_text = "\n".join([f"- {s}" for s in sources])
        
        return f"""Evaluate the quality and confidence of this answer.

QUESTION: "{question}"
ANSWER: "{answer}"
SOURCES USED:
{sources_text}

Respond with JSON:
{{
  "confidence": 0.0-1.0,
  "reasoning": "explanation of confidence score",
  "requires_human": true/false,
  "concerns": ["list any concerns about the answer"]
}}

Confidence guidelines:
- 0.9-1.0: Complete, accurate answer fully supported by sources
- 0.7-0.9: Good answer with minor gaps or ambiguity
- 0.5-0.7: Partial answer, missing some information
- 0.3-0.5: Uncertain or incomplete answer
- 0.0-0.3: Unable to answer properly

Set requires_human=true if:
- Question needs human judgment
- Answer quality is low (<0.5 confidence)
- Complex policy or legal question
- Sensitive customer situation"""
    
    @staticmethod
    def build_greeting_response() -> str:
        """Build a friendly greeting response."""
        return """Hello! I'm here to help you today. I can assist you with:

- Product information and specifications
- Order status and tracking
- Account and shipping questions
- General policies and FAQs

What can I help you with?"""
    
    @staticmethod
    def build_fallback_response(question: str) -> str:
        """Build fallback response when no answer found."""
        return f"""I don't have specific information about "{question}" in my knowledge base right now.

However, I'd be happy to help you in other ways:
- I can connect you with our support team who can answer this directly
- If you have a different question, I'm here to help
- You can also visit our help center for more resources

What would you prefer?"""