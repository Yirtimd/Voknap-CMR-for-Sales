from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.modules.activity import models as activity_models
from app.modules.ai_agent import models as ai_agent_models
from app.modules.connectors import models as connectors_models
from app.modules.knowledge import models as knowledge_models
from app.modules.production import models as production_models
from app.modules.sales import models as sales_models
from app.modules.templates import models as templates_models
from app.modules.activity.router import router as activity_router
from app.modules.ai_agent.router import router as ai_agent_router
from app.modules.auth.router import router as auth_router
from app.modules.connectors.router import router as connectors_router
from app.modules.health.router import router as health_router
from app.modules.knowledge.router import router as knowledge_router
from app.modules.me.router import router as me_router
from app.modules.production.router import router as production_router
from app.modules.sales.router import router as sales_router
from app.modules.templates.router import router as templates_router


app = FastAPI(title="CMR Sales App", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "app": "CMR Sales App",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
    }


app.include_router(health_router, tags=["health"])
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(me_router, tags=["me"])
app.include_router(activity_router, prefix="/activities", tags=["activities"])
app.include_router(sales_router, prefix="/sales", tags=["sales"])
app.include_router(knowledge_router, prefix="/knowledge", tags=["knowledge"])
app.include_router(ai_agent_router, prefix="/ai-agent", tags=["ai-agent"])
app.include_router(connectors_router, prefix="/connectors", tags=["connectors"])
app.include_router(templates_router, prefix="/templates", tags=["templates"])
app.include_router(production_router, prefix="/production", tags=["production"])
