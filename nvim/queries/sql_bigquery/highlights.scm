; extends

(_ table_name: (identifier) @module)
(_ source_table_name: (identifier) @module)
(_ referenced_table_name: (identifier) @module)
(_ new_table_name: (identifier) @module)
(cte alias_name: (identifier) @module)
(from_item (as_alias alias_name: (identifier) @module))

((function_call function: (identifier) @function.builtin
  "(" . (argument) . "," . (argument (string) @_pattern))
  (#bigquery-regex-pattern? @function.builtin @_pattern))
