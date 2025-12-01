SELECT
  column_name,
  data_type,
  is_nullable
FROM
  {full_dataset}.INFORMATION_SCHEMA.COLUMNS
WHERE
  table_name = '{table_name}'
ORDER BY
  ordinal_position;
