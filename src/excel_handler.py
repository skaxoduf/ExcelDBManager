
import pandas as pd
import os
from openpyxl.utils import get_column_letter

class ExcelHandler:
    def __init__(self, filename="ExcelDBManager.xlsx"):
        self.filename = filename

    def export_schema(self, schema_df, routines_df):
        """
        Saves the schema and routines DataFrames to Excel with formatting.
        """
        try:
            # Reorder columns as requested
            # User wants: Column Size, PK, Default, Type separately
            # My extracted DF has: Table, Column Name, Data Type, Length, PK, Allow Null, Default Value
            
            desired_order = ['Table', 'Column Name', 'Data Type', 'Length', 'PK', 'Allow Null', 'Default Value']
            # Filter cols that exist
            final_cols = [c for c in desired_order if c in schema_df.columns]
            
            if not final_cols: 
                final_cols = schema_df.columns

            with pd.ExcelWriter(self.filename, engine='openpyxl') as writer:
                # 1. Schema Sheet
                sheet_name = 'Schema'
                if not schema_df.empty:
                    schema_df[final_cols].to_excel(writer, sheet_name=sheet_name, index=False)
                    worksheet = writer.sheets[sheet_name]
                    self._apply_formatting(worksheet)
                
                # 2. Routines Sheet
                if not routines_df.empty:
                    routines_df.to_excel(writer, sheet_name='Procedures_Functions', index=False)
                    self._apply_formatting(writer.sheets['Procedures_Functions'])
            
            return True, f"Successfully exported to {self.filename}"
        except Exception as e:
            return False, f"Export failed: {e}"

    def _apply_formatting(self, worksheet):
        """Applies freeze panes and auto-width."""
        # Freeze top row
        worksheet.freeze_panes = 'A2'
        
        # Auto-width
        for column in worksheet.columns:
            max_length = 0
            column_letter = get_column_letter(column[0].column)
            
            # Helper to calculate length
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            
            adjusted_width = (max_length + 2) * 1.2
            # Cap width to avoid extremely wide cols (e.g. definitions)
            if adjusted_width > 50: adjusted_width = 50
            
            worksheet.column_dimensions[column_letter].width = adjusted_width

    def read_schema(self):
        """
        Reads the 'Schema' sheet back from Excel.
        """
        if not os.path.exists(self.filename):
            return None
        
        try:
            # Read all as string to prevent auto-conversion issues
            df = pd.read_excel(self.filename, sheet_name='Schema', dtype=str)
            # Nan handling
            df.fillna('', inplace=True)
            return df
        except Exception as e:
            print(f"Error reading excel: {e}")
            return None
