
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
        pk_constraint = inspector.get_pk_constraint(table_name)
        pk_columns = pk_constraint.get('constrained_columns', [])

        processed_cols = []
        for col in columns:
            col_type = col['type']
            length = getattr(col_type, 'length', None)
            
            # Clean Data Type: Extract class name (e.g. VARCHAR, INTEGER) to avoid "VARCHAR(64) ..."
            # SQLAlchemy reflection returns types like VARCHAR, INTEGER, etc.
            try:
                # __visit_name__ usually holds the SQL type name (e.g. 'varchar', 'integer')
                type_name = col_type.__visit_name__.upper()
            except:
                # Fallback
                type_name = type(col_type).__name__.upper()
            
            c_info = {
                'Table': table_name,
                'Column Name': col['name'],
                'Data Type': type_name, 
                'Length': length if length else '', 
                'PK': 'Y' if col['name'] in pk_columns else '',
                'Allow Null': 'Y' if col['nullable'] else 'N',
                'Default Value': col.get('default', '')
            }
            # Clean up default value (sometimes it comes as object)
            if c_info['Default Value'] is None: c_info['Default Value'] = ''
            
            processed_cols.append(c_info)
        
        return pd.DataFrame(processed_cols)

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
