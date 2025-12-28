
import pandas as pd
import os

class ExcelHandler:
    def __init__(self, filename="ExcelDBManager.xlsx"):
        self.filename = filename

    def export_schema(self, schema_df, routines_df):
        """
        Saves the schema and routines DataFrames to Excel.
        """
        try:
            with pd.ExcelWriter(self.filename, engine='openpyxl') as writer:
                # 1. Schema Sheet
                if not schema_df.empty:
                    # Select/Order columns for better readability
                    # Available: name, type, nullable, etc., table_name
                    cols = ['table_name', 'name', 'type', 'max_length', 'is_nullable', 'primary_key']
                    # Filter only existing cols
                    final_cols = [c for c in cols if c in schema_df.columns]
                    # If some are missing, just dump all
                    if not final_cols: 
                        final_cols = schema_df.columns
                    
                    schema_df[final_cols].to_excel(writer, sheet_name='Schema', index=False)
                
                # 2. Routines Sheet
                if not routines_df.empty:
                    routines_df.to_excel(writer, sheet_name='Procedures_Functions', index=False)
            
            return True, f"Successfully exported to {self.filename}"
        except Exception as e:
            return False, f"Export failed: {e}"

    def read_schema(self):
        """
        Reads the 'Schema' sheet back from Excel.
        """
        if not os.path.exists(self.filename):
            return None
        
        try:
            df = pd.read_excel(self.filename, sheet_name='Schema')
            return df
        except Exception as e:
            print(f"Error reading excel: {e}")
            return None
