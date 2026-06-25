from database.base import Base
from database.connection import engine

# Import all models
import database.models

print("Creating database tables...")

Base.metadata.create_all(bind=engine)

print("Done!")