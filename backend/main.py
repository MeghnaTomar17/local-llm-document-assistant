from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router
from backend.llm_sql.routes import router as recruiter_search_router
from backend.routes.resume_routes import router as resume_router


app = FastAPI(title="Resume Intelligence Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(resume_router)
app.include_router(recruiter_search_router)


@app.get("/")
def health_check():
    return {"status": "ok", "service": "Resume Intelligence Assistant"}
