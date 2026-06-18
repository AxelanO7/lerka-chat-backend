import asyncio
import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatRequest, CompareRequest, ChatMessage
from app.services.chat_service import ChatService
from app.services.moderation_service import moderation_service
from app.api.deps import verify_internal_gateway
from app.infrastructure.llm.factory import get_llm_provider
from app.infrastructure.cache.redis_cache import get_exact_cache, set_exact_cache, get_cache_key, normalize_prompt
from app.infrastructure.cache.semantic_cache import get_semantic_cache, set_semantic_cache
from app.infrastructure.embeddings.embedding_service import embedding_service
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/stream", dependencies=[Depends(verify_internal_gateway)])
async def chat_stream(request: ChatRequest):
    """
    Streams single-model completions.
    """
    # Find the prompt in request messages to run moderation
    prompt = ""
    for msg in reversed(request.messages):
        if msg.role == "user":
            prompt = msg.content
            break

    # 1. Moderation Check
    is_blocked, do_not_cache, reason = moderation_service.moderate_prompt(prompt)
    if is_blocked:
        async def block_generator():
            yield f"Blocked by moderation: {reason}"
        return StreamingResponse(block_generator(), media_type="text/plain")

    # 2. Cache check
    # Check exact cache
    cache_key = get_cache_key(prompt, request.model_id, request.temperature, 1024)
    cached_val = await get_exact_cache(prompt, request.model_id, request.temperature, 1024)
    if cached_val:
        async def cached_generator():
            yield cached_val.get("content", "")
            yield f"__USAGE__ {json.dumps(cached_val.get('usage', {'prompt_tokens': 0, 'completion_tokens': 0}))}"
        return StreamingResponse(cached_generator(), media_type="text/plain")

    if request.use_rag and request.user_id:
        from app.infrastructure.rag.retrieval import retrieve
        try:
            chunks = await retrieve(prompt, request.user_id, request.session_id)
            if chunks:
                context_str = "\n".join(chunks)
                rag_message = ChatMessage(
                    role="system",
                    content=f"Use the following retrieved context to answer the user's prompt if it is relevant:\n{context_str}"
                )
                request.messages.insert(0, rag_message)
        except Exception as e:
            logger.error(f"RAG retrieval error: {e}")

    # 3. Stream from Provider
    async def provider_generator():
        provider = get_llm_provider(request.model_id)
        full_response_text = []
        token_usage = {"prompt_tokens": 0, "completion_tokens": 0}
        
        try:
            async for chunk in provider.generate_stream(
                messages=request.messages,
                model_id=request.model_id,
                temperature=request.temperature
            ):
                if chunk.startswith("__USAGE__"):
                    try:
                        token_usage = json.loads(chunk[10:])
                    except Exception:
                        pass
                    yield chunk
                else:
                    full_response_text.append(chunk)
                    yield chunk
            
            # Write to cache if not flagged do_not_cache
            if not do_not_cache:
                await set_exact_cache(
                    prompt=prompt,
                    model_id=request.model_id,
                    temperature=request.temperature,
                    max_tokens=1024,
                    payload={
                        "content": "".join(full_response_text),
                        "usage": token_usage
                    }
                )
        except Exception as e:
            logger.error(f"Error in stream route handler: {e}")
            yield f"\n[Worker Stream Error: {str(e)}]"
            
    return StreamingResponse(provider_generator(), media_type="text/plain")

@router.post("/compare", dependencies=[Depends(verify_internal_gateway)])
async def chat_compare(request: CompareRequest):
    """
    Streams comparison of two paid models and a judge summary.
    Runs comparisons concurrently and streams chunks back in SSE format.
    Writes exact cache and conditional semantic cache (only if is_curated=True).
    """
    prompt = request.prompt
    if not prompt and request.messages:
        for msg in reversed(request.messages):
            if msg.role == "user":
                prompt = msg.content
                break
                
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt or messages is required")

    # 1. Moderation Check
    is_blocked, do_not_cache, reason = moderation_service.moderate_prompt(prompt)
    if is_blocked:
        async def block_generator():
            yield f"data: {json.dumps({'error': reason})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(block_generator(), media_type="text/event-stream")

    # 2. Check Caches
    norm_prompt = normalize_prompt(prompt)
    
    # Exact cache
    cached_exact = await get_exact_cache(prompt, "compare_set", request.temperature, 1024)
    if cached_exact:
        async def cached_exact_generator():
            for model_id, text in cached_exact.get("model_responses", {}).items():
                yield f"data: {json.dumps({'model': model_id, 'text': text})}\n\n"
            yield f"data: {json.dumps({'model': 'judge', 'text': cached_exact.get('judge_summary', '')})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(cached_exact_generator(), media_type="text/event-stream")

    # Semantic cache
    embedding = await embedding_service.get_embedding(norm_prompt)
    cached_semantic = await get_semantic_cache(embedding)
    if cached_semantic:
        async def cached_semantic_generator():
            for model_id, text in cached_semantic.get("model_responses", {}).items():
                yield f"data: {json.dumps({'model': model_id, 'text': text})}\n\n"
            yield f"data: {json.dumps({'model': 'judge', 'text': cached_semantic.get('judge_summary', '')})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(cached_semantic_generator(), media_type="text/event-stream")

    # 3. Parallel Execution using gather + async queue
    async def compare_stream_generator():
        # Use the models selected upstream. The API gateway is the source of
        # truth for tier/registry validation, so models arriving here are
        # already authorized. Fall back to env defaults only when none provided.
        requested = [m for m in (request.models or []) if isinstance(m, str) and m.strip()]
        models = requested if len(requested) >= 2 else settings.COMPARE_LIVE_MODELS
        queue = asyncio.Queue()
        
        chunks = []
        if request.use_rag and request.user_id:
            from app.infrastructure.rag.retrieval import retrieve
            try:
                chunks = await retrieve(prompt, request.user_id, request.session_id)
            except Exception as e:
                logger.error(f"RAG retrieval error in compare: {e}")

        async def run_single_model(m_id: str):
            provider = get_llm_provider(m_id)
            system_content = (
                "You are a helpful assistant. Answer in the same language as the user. "
                "Be concise and direct. Answer briefly unless the user asks for detail."
            )
            if chunks:
                context_str = "\n".join(chunks)
                system_content += f"\nUse the following retrieved context if relevant:\n{context_str}"

            messages = [
                ChatMessage(role="system", content=system_content),
                ChatMessage(role="user", content=prompt)
            ]
            accumulated = []

            async def _run():
                async for chunk in provider.generate_stream(messages, m_id, request.temperature):
                    if chunk.startswith("__USAGE__"):
                        continue
                    accumulated.append(chunk)
                    await queue.put({"model": m_id, "text": chunk})

            try:
                await asyncio.wait_for(_run(), timeout=30.0)
            except asyncio.TimeoutError:
                logger.warning(f"Model {m_id} timed out after 30s")
                await queue.put({"model": m_id, "text": "\n[Model timed out]"})
            except Exception as e:
                logger.error(f"Error in model {m_id}: {e}")
                await queue.put({"model": m_id, "text": f"\n[Model Error: {str(e)}]"})
            finally:
                await queue.put({"model": m_id, "done": True, "full_text": "".join(accumulated)})

        # Start paid models in parallel
        tasks = [asyncio.create_task(run_single_model(m)) for m in models]
        
        responses = {}
        completed = 0
        while completed < len(models):
            item = await queue.get()
            if item.get("done"):
                completed += 1
                responses[item["model"]] = item["full_text"]
            else:
                yield f"data: {json.dumps({'model': item['model'], 'text': item['text']})}\n\n"

        # 4. Judge summary synthesis
        judge_model = settings.JUDGE_MODEL
        judge_system = (
            "You are Lerka, the master synthesis judge presiding over a live debate between several AI models "
            "who have just answered the same user question. They have argued, agreed, and challenged each other. "
            "Your job is NOT to average them — it is to weigh their arguments, expose where they clashed, "
            "discard the weak or hallucinated claims, and deliver one confident verdict.\n\n"
            "Voice & drama:\n"
            "- Write with quiet confidence and momentum, as if announcing the conclusion of a sharp debate.\n"
            "- When the models disagreed, dramatize it briefly: name the tension in one vivid sentence "
            "(e.g. 'The models split here:' or 'One pushed back —') before resolving it.\n"
            "- When they all agreed, frame it as a unanimous verdict ('All minds converge:').\n"
            "- Be persuasive and decisive, never wishy-washy. The user should feel many minds were consulted "
            "and one clear truth emerged.\n\n"
            "Rules:\n"
            "- Use the SAME language as the user (if the user wrote Indonesian, answer in Indonesian).\n"
            "- Lead with the direct answer / verdict first.\n"
            "- Then, in one short punchy paragraph, reveal the debate: where models agreed or clashed.\n"
            "- Stay concise — drama through word choice, not length.\n"
            "- Use 2-4 bullets only if they sharpen the verdict.\n"
            "- Never reveal chain-of-thought or a long model-by-model transcript.\n"
            "- For simple factual questions, 1-3 decisive sentences are enough.\n"
            "- Close with the feeling: 'Many minds. One answer.'"
        )
        judge_prompt = "Here is what each model argued in the debate:\n\n"
        for model_id, text in responses.items():
            judge_prompt += f"--- {model_id} argued ---\n{text}\n\n"
        judge_prompt += "\nNow deliver your final verdict as the synthesis judge."

        judge_messages = [
            ChatMessage(role="system", content=judge_system),
            ChatMessage(role="user", content=judge_prompt)
        ]
        
        judge_provider = get_llm_provider(judge_model)
        judge_accumulated = []
        try:
            async for chunk in judge_provider.generate_stream(judge_messages, judge_model, request.temperature):
                if chunk.startswith("__USAGE__"):
                    continue
                judge_accumulated.append(chunk)
                yield f"data: {json.dumps({'model': 'judge', 'text': chunk})}\n\n"
        except Exception as e:
            logger.error(f"Error in judge: {e}")
            err_msg = f"\n[Judge Summary Error: {str(e)}]"
            judge_accumulated.append(err_msg)
            yield f"data: {json.dumps({'model': 'judge', 'text': err_msg})}\n\n"

        judge_summary = "".join(judge_accumulated)

        # 5. Write-through Cache (Exact + Conditional Semantic)
        payload = {
            "model_responses": responses,
            "judge_summary": judge_summary
        }
        
        if not do_not_cache:
            # Set exact cache
            await set_exact_cache(prompt, "compare_set", request.temperature, 1024, payload)
            # Set semantic cache only if curated
            if request.is_curated:
                await set_semantic_cache(embedding, norm_prompt, payload, settings.MODEL_SET_VERSION)

        yield "data: [DONE]\n\n"

    return StreamingResponse(compare_stream_generator(), media_type="text/event-stream")