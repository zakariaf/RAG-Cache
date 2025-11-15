"""
Query processing endpoint.

Sandi Metz Principles:
- Single Responsibility: HTTP request handling
- Small functions: Minimal logic in endpoints
- Dependency Injection: Service injected
"""

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_query_service
from app.exceptions import LLMProviderError
from app.models.query import QueryRequest
from app.models.response import QueryResponse
from app.services.query_service import QueryService
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/query", response_model=QueryResponse)
async def process_query(
    request: QueryRequest,
    service: QueryService = Depends(get_query_service),  # noqa: B008
) -> QueryResponse:
    """
    Process query with caching.

    Args:
        request: Query request
        service: Query service (injected)

    Returns:
        Query response

    Raises:
        HTTPException: If processing fails
    """
    try:
        return await service.process(request)
    except LLMProviderError as e:
        logger.error("LLM provider error", error=str(e))
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")
