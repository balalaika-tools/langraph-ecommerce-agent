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
        sql_template = load_query("get_table_descriptions.sql")
        
        for table in self.table_names:
            # full dataset path for INFORMATION_SCHEMA — use as-is
            full_dataset = self.dataset_name  
            sql = sql_template.format(
                full_dataset=full_dataset,
                table_name=table
            )
            rows = self.client.query(sql).result()
            lines = [f"Table `{table}`:"]
            for row in rows:
                nullable = "NULLABLE" if row.is_nullable == "YES" else "REQUIRED"
                lines.append(f"  - {row.column_name} ({row.data_type}, {nullable})")
            desc[table] = "\n".join(lines)
        return json.dumps(desc)