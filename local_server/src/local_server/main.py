from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from local_server.database import create_db_and_tables, engine
from local_server.admin import setup_admin
from local_server.routers import users, accounts, transactions, sync, reports
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Initialize scheduler
scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup database tables on startup
    create_db_and_tables()
    setup_admin(app, engine)
    
    # Setup and start scheduler
    # In future iterations, add actual cron jobs here
    scheduler.start()
    
    yield
    # Cleanup here
    scheduler.shutdown()

app = FastAPI(title="CloudApi Local Server", lifespan=lifespan)

# CORS config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
app.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
app.include_router(sync.router, prefix="/sync", tags=["sync"])
app.include_router(reports.router, prefix="/reports", tags=["reports"])

@app.get("/")
async def root():
    return {"message": "CloudApi Local Server is running"}
