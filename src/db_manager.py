
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
            return True, ""
        except Exception as e:
            print(f"Error connecting: {e}")
            return False, str(e)

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

    def sync_schema(self, excel_df):
        """
        Syncs Excel schema changes to DB.
        Refactored to pre-fetch schema to avoid locking issues.
        """
        if not self.engine: return False, ["Not connected."]
        
        logs = []
        
        # 1. Pre-fetch ALL current schemas from DB (Lock-free Read)
        # We fetch everything first so we don't need to open new connections 
        # while holding a transaction lock later.
        try:
            current_schemas = {}
            tables = self.get_tables()
            for t in tables:
                current_schemas[t] = self.get_table_schema(t)
        except Exception as e:
            return False, [f"Error fetching current schema: {e}"]

        # 2. Start Transaction for updates
        with self.engine.connect() as conn:
            # Set lock timeout to avoid infinite hangs (e.g., 5 seconds)
            try:
                conn.execute(text("SET LOCK_TIMEOUT 5000")) 
            except:
                pass # Some DBs might not support this

            trans = conn.begin()
            try:
                # Group by table
                excel_tables = excel_df['Table'].unique()
                
                for table_name, group in excel_df.groupby('Table'):
                    
                    # Fetch pre-loaded schema
                    current_df = current_schemas.get(table_name)
                    
                    # If table logic needs to handle NEW TABLES (not implemented yet, but for safety)
                    if current_df is None or current_df.empty: 
                        # New table creation is complex, currently skipping or could implement CREATE TABLE
                        # For now, skipping as per previous logic (only ALTER/ADD/DROP cols)
                        continue 
                    
                    # Convert to dict for lookup
                    curr_map = {row['Column Name']: row for _, row in current_df.iterrows()}
                    
                    for _, row in group.iterrows():
                        col = row['Column Name']
                        
                        # -- Prepare New attributes (from Excel) --
                        new_type = str(row['Data Type']).strip().upper()
                        
                        raw_new_len = str(row['Length']).strip()
                        if raw_new_len.lower() in ['nan', 'none', '']: 
                            new_len = ''
                        else:
                            try:
                                new_len = str(int(float(raw_new_len)))
                            except:
                                new_len = raw_new_len
                                
                        # Construct type definition
                        type_def = new_type
                        if new_type in ['VARCHAR', 'NVARCHAR', 'CHAR', 'NCHAR', 'VARBINARY'] and new_len:
                            type_def = f"{new_type}({new_len})"
                        elif new_type in ['DECIMAL', 'NUMERIC'] and new_len:
                            type_def = f"{new_type}({new_len})"

                        # Nullability
                        null_val = str(row['Allow Null']).strip().upper()
                        null_def = "NULL" if null_val == 'Y' else "NOT NULL"

                        # 1. ADD Column (If not in DB)
                        if col not in curr_map:
                            sql = f"ALTER TABLE [{table_name}] ADD [{col}] {type_def} {null_def}"
                            print(f"Executing: {sql}")
                            conn.execute(text(sql))
                            logs.append(f"Added Column [{table_name}].[{col}] ({type_def})")
                            continue
                        
                        # 2. MATCH/MODIFY Existing
                        curr = curr_map[col]
                        
                        # -- Prepare Old attributes (from DB) --
                        old_type = str(curr['Data Type']).strip().upper()
                        
                        raw_old_len = str(curr['Length']).strip()
                        if raw_old_len.lower() in ['nan', 'none', '']:
                            old_len = ''
                        else:
                            try:
                                old_len = str(int(float(raw_old_len)))
                            except:
                                old_len = raw_old_len

                        # Check differences
                        types_with_len = ['VARCHAR', 'NVARCHAR', 'CHAR', 'NCHAR', 'VARBINARY']
                        is_diff = False
                        if new_type != old_type:
                            is_diff = True
                        elif new_type in types_with_len and new_len != old_len:
                            is_diff = True
                            
                        if is_diff:
                            sql = f"ALTER TABLE [{table_name}] ALTER COLUMN [{col}] {type_def} {null_def}"
                            print(f"Executing: {sql}")
                            conn.execute(text(sql))
                            logs.append(f"Updated [{table_name}].[{col}]: {old_type}({old_len}) -> {type_def}")

                    # 3. DROP Column (If in DB but not in Excel)
                    excel_cols = set(group['Column Name'])
                    db_cols = set(curr_map.keys())
                    dropped_cols = db_cols - excel_cols
                    
                    for d_col in dropped_cols:
                        sql = f"ALTER TABLE [{table_name}] DROP COLUMN [{d_col}]"
                        print(f"Executing: {sql}")
                        conn.execute(text(sql))
                        logs.append(f"Dropped Column [{table_name}].[{d_col}]")
                        
                trans.commit()
                return True, logs if logs else ["No changes detected."]
            except Exception as e:
                trans.rollback()
                print(f"Sync Error: {e}")
                return False, [str(e)]
