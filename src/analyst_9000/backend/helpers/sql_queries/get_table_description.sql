SELECT
  description
FROM
  {full_dataset}.INFORMATION_SCHEMA.TABLES
WHERE
  table_name = '{table_name}';

