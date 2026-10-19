
from sqlalchemy import text
from mini_crm.database import engine

with engine.connect() as connection:
    result = connection.execute(text("SELECT version()"))
    print("Connected successfully!")
    print(result.scalar())
