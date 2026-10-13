; extends

((function_call function: (identifier) @function.builtin
  "(" . (argument) . "," . (argument (string) @_pattern))
  (#bigquery-regex-pattern? @function.builtin @_pattern))
