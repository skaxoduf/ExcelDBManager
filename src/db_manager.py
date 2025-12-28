
import sqlalchemy
from sqlalchemy import create_engine, inspect, text
import pandas as pd

class DBManager:
    def __init__(self, server, database, user, password):
        self.connection_string = f"mssql+pyodbc://{user}:{password}@{server}/{database}?driver=ODBC+Driver+17+for+SQL+Server"
        self.engine = None

    def connect(self):
        try:
            self.engine = create_engine(self.connection_string)
            with self.engine.connect() as conn:
                print("Connection successful!")
            return True
        except Exception as e:
            print(f"Error connecting: {e}")
            return False

    def get_tables(self):
        if not self.engine: return []
        inspector = inspect(self.engine)
        return inspector.get_table_names()
