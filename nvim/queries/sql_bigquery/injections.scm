; Match only the pattern (second argument), never input or replacement text.
((function_call
  function: (identifier) @_function
  "(" . (argument) . "," . (argument (string) @injection.content))
  (#bigquery-regex-pattern? @_function @injection.content)
  (#set! injection.language "regex")
  (#set! injection.include-children)
  (#bigquery-regex-content! @injection.content))
