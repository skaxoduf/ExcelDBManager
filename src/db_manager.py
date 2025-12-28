
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
        """Returns a list of all table names in the database."""
        if not self.engine: return []
        inspector = inspect(self.engine)
        return inspector.get_table_names()

    def get_table_schema(self, table_name):
        """Returns a DataFrame containing column details for a specific table."""
        if not self.engine: return pd.DataFrame()
        
        inspector = inspect(self.engine)
        columns = inspector.get_columns(table_name)
        
        # Convert to DataFrame for easy handling
        df = pd.DataFrame(columns)
        # Expected cols: name, type, nullable, default, autoincrement, etc.
        
        # Simplify Type to string
        df['type'] = df['type'].apply(lambda x: str(x))
        
        # Add 'table_name' column for aggregation later if needed
        df['table_name'] = table_name
        
        return df

    def get_all_schemas(self):
        """Iterates over all tables and gathers their column info."""
        tables = self.get_tables()
        all_dfs = []
        for t in tables:
            df = self.get_table_schema(t)
            all_dfs.append(df)
            
        if not all_dfs:
            return pd.DataFrame()
        return pd.concat(all_dfs, ignore_index=True)

    def get_procedures_and_functions(self):
        """Fetches Stored Procedures and Scalar/Table-valued Functions."""
        if not self.engine: return pd.DataFrame()
        
        query = text("""
            SELECT 
                ROUTINE_NAME as name,
                ROUTINE_TYPE as type,
                ROUTINE_DEFINITION as definition
            FROM INFORMATION_SCHEMA.ROUTINES 
            WHERE ROUTINE_BODY = 'SQL'
            ORDER BY ROUTINE_TYPE, ROUTINE_NAME
        """)
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(query)
                return pd.DataFrame(result.fetchall(), columns=['name', 'type', 'definition'])
        except Exception as e:
            print(f"Error fetching routines: {e}")
            return pd.DataFrame()
