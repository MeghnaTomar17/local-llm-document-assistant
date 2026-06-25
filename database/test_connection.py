from sqlalchemy import text

from connection import engine

try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT version();"))

        print("\nConnected Successfully!\n")

        print(result.fetchone()[0])

except Exception as e:
    print("\nConnection Failed!\n")
    print(e)