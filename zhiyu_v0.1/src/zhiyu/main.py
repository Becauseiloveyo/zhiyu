from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from zhiyu import __version__
from zhiyu.api.body_limit import BodyLimitMiddleware
from zhiyu.api.routes import (
    ai,
    demo,
    events,
    health,
    incidents,
    intelligence,
    product,
    response,
    verification,
)
from zhiyu.core.config import settings
from zhiyu.core.errors import AccessDenied, ConflictError, DomainError
from zhiyu.product.sessions import router as session_router
from zhiyu.product.web import ProductHeaders, mount_console

app = FastAPI(
    title="智御 Zhiyu Control Plane",
    version=__version__,
    description="Evidence-bounded AI proposals with deterministic authorization and independent verification. AI influence is disabled by default.",
)
app.add_middleware(BodyLimitMiddleware, max_bytes=settings.max_body_bytes)
app.add_middleware(ProductHeaders)


@app.exception_handler(DomainError)
async def domain_error(request: Request, error: DomainError) -> JSONResponse:
    code = 403 if isinstance(error, AccessDenied) else 409 if isinstance(error, ConflictError) else 422
    return JSONResponse({"detail": error.code}, status_code=code)


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, error: SQLAlchemyError) -> JSONResponse:
    status = 422 if isinstance(error, IntegrityError) else 503
    return JSONResponse(
        {"detail": "database_constraint_violation" if status == 422 else "database_unavailable"},
        status_code=status,
    )


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        {"detail": [{"type": e["type"], "loc": e["loc"]} for e in error.errors()]}, status_code=422
    )


app.include_router(health.router)
app.include_router(events.router)
app.include_router(verification.router)
app.include_router(incidents.router)
app.include_router(intelligence.router)
app.include_router(response.router)
app.include_router(ai.router)
app.include_router(product.router)
app.include_router(demo.router)
app.include_router(session_router)
mount_console(app)
