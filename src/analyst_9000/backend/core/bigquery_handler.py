from google.cloud import bigquery
from typing import List, Dict
from analyst_9000.backend.helpers.utils import load_query
import json

class BigQueryHandler:
    def __init__(self, dataset_name: str, table_names: List[str]):
        self.client = bigquery.Client()
        self.dataset_name = dataset_name
        self.table_names = table_names
        self.tables_description = self.get_tables_description()

    def get_tables_description(self) -> Dict[str, str]:
        desc: Dict[str, str] = {}
        table_schema_sql = load_query("get_table_schema.sql")
        
        for table in self.table_names:
            # full dataset path for INFORMATION_SCHEMA — use as-is
            full_dataset = self.dataset_name  
            
            # Get table description using get_table() method (works for both public and private datasets)
            table_description = None
            try:
                # Try INFORMATION_SCHEMA 
                table_desc_sql_template = load_query("get_table_description.sql")
                table_desc_sql = table_desc_sql_template.format(
                    full_dataset=full_dataset,
                    table_name=table
                )
                table_desc_rows = list(self.client.query(table_desc_sql).result())
                if table_desc_rows and hasattr(table_desc_rows[0], 'description') and table_desc_rows[0].description:
                    table_description = table_desc_rows[0].description
            except Exception:
                # Fall back to get_table() method 
                try:
                    table_fqn = f"{full_dataset}.{table}"
                    bq_table = self.client.get_table(table_fqn)
                    if bq_table.description:
                        table_description = bq_table.description
                except Exception:
                    pass  # If both methods fail, continue without description
            
            # Get column information
            sql = table_schema_sql.format(
                full_dataset=full_dataset,
                table_name=table
            )
            rows = self.client.query(sql).result()
            lines = [f"Table `{table}`:"]
            
            # Add table description if available
            if table_description:
                lines.append(f"Description: {table_description}")
                lines.append("")  # Empty line for readability
            
            for row in rows:
                nullable = "NULLABLE" if row.is_nullable == "YES" else "REQUIRED"
                lines.append(f"  - {row.column_name} ({row.data_type}, {nullable})")
            desc[table] = "\n".join(lines)
        return json.dumps(desc)