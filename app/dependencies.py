from typing import Optional, Dict, List
from fastapi import Depends, HTTPException, Header, status
from functools import lru_cache

from llm import (
    LLMRouter,
    OpenAIProvider,
    AnthropicProvider,
    RouteConfig,
    RoutingStrategy,
    LLMProvider,
    BaseLLMProvider,
)
from memory import MemoryManager, InMemoryStore, RedisStore
from memory.store import BaseMemoryStore
from orchestration import OrchestrationRouter, PolicyManager
from knowledge.vector_store import ChromaVectorStore
from knowledge.embeddings import OpenAIEmbedder
from knowledge.retrieval import KnowledgeRetriever
from config import settings


_llm_router: Optional[LLMRouter] = None
_memory_manager: Optional[MemoryManager] = None
_orchestration_router: Optional[OrchestrationRouter] = None
_knowledge_retriever: Optional[KnowledgeRetriever] = None


@lru_cache()
def get_llm_router() -> LLMRouter:
    global _llm_router

    if _llm_router is None:
        providers: Dict[LLMProvider, BaseLLMProvider] = {}

        if settings.openai_api_key:
            providers[LLMProvider.OPENAI] = OpenAIProvider(
                api_key=settings.openai_api_key,
                default_model=settings.default_model,
            )

        if settings.anthropic_api_key:
            providers[LLMProvider.ANTHROPIC] = AnthropicProvider(
                api_key=settings.anthropic_api_key,
                default_model=settings.fallback_model,
            )

        if not providers:
            raise RuntimeError("No LLM providers configured")

        strategy_map = {
            "cost": RoutingStrategy.COST,
            "latency": RoutingStrategy.LATENCY,
            "quality": RoutingStrategy.QUALITY,
            "primary": RoutingStrategy.PRIMARY,
        }

        fallback_providers: List[LLMProvider] = []
        if (
            settings.fallback_provider
            and settings.fallback_provider != settings.default_llm_provider
        ):
            provider_map = {
                "openai": LLMProvider.OPENAI,
                "anthropic": LLMProvider.ANTHROPIC,
            }
            fallback_provider_enum = provider_map.get(settings.fallback_provider)
            if fallback_provider_enum:
                fallback_providers.append(fallback_provider_enum)

        _llm_router = LLMRouter(
            providers=providers,
            route_config=RouteConfig(
                strategy=strategy_map.get(
                    settings.llm_routing_strategy, RoutingStrategy.QUALITY
                ),
                primary_provider=provider_map.get(
                    settings.default_llm_provider, LLMProvider.OPENAI
                ),
                fallback_providers=fallback_providers if fallback_providers else None,
            ),
        )

    return _llm_router


@lru_cache()
def get_memory_manager() -> MemoryManager:
    global _memory_manager

    if _memory_manager is None:
        store: BaseMemoryStore

        if settings.is_production and settings.redis_url:
            store = RedisStore(
                redis_url=settings.redis_url,
                ttl_seconds=7 * 86400,
            )
        else:
            store = InMemoryStore()

        _memory_manager = MemoryManager(
            store=store,
            llm_router=get_llm_router(),
            enable_summarization=settings.enable_rag,
            enable_validation=True,
            auto_summarize_threshold=20,
        )

    return _memory_manager


@lru_cache()
def get_knowledge_retriever() -> KnowledgeRetriever:
    global _knowledge_retriever

    if _knowledge_retriever is None:
        vector_store = ChromaVectorStore(
            persist_directory=settings.rag_vector_store_path
        )

        if not settings.openai_api_key:
            raise RuntimeError("OpenAI API key required for embeddings")

        embedder = OpenAIEmbedder(api_key=settings.openai_api_key)

        _knowledge_retriever = KnowledgeRetriever(
            vector_store=vector_store,
            embedder=embedder,
            max_results=settings.rag_max_results,
            score_threshold=settings.rag_score_threshold,
        )

    return _knowledge_retriever


@lru_cache()
def get_orchestration_router() -> OrchestrationRouter:
    global _orchestration_router

    if _orchestration_router is None:
        _orchestration_router = OrchestrationRouter(
            llm_router=get_llm_router(),
            memory_manager=get_memory_manager(),
            policy_manager=PolicyManager(),
            knowledge_retriever=get_knowledge_retriever(),
        )

    return _orchestration_router


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> str:
    if settings.is_development:
        return "dev_key"

    if not settings.api_key:
        return "no_key_configured"

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is missing",
        )

    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    return x_api_key


async def get_request_context() -> Dict[str, str]:
    """Get request context for tracking."""
    return {
        "app_name": settings.app_name,
        "app_env": settings.app_env,
    }