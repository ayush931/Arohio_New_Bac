from fastapi import FastAPI
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import engine
from app.api import api_router
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOADS_DIR = os.path.abspath(os.path.join(os.getcwd(), "uploads"))
print("UPLOADS_DIR =", UPLOADS_DIR)
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
app.mount("/profile_images", StaticFiles(directory="public/profile_images"), name="profile_images")
@app.get("/")
async def root():
    return {"message": "Backend running"}

@app.get("/test-db")
async def test_db():
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT 1"))
        return {"db_response": result.scalar()}