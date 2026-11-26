; extends

([
  (table . [(bare_key) (quoted_key) (dotted_key)] @markup.heading)
  (table_array_element . [(bare_key) (quoted_key) (dotted_key)] @markup.heading)
]
  (#set! priority 105))

((boolean) @boolean.true
  (#eq? @boolean.true "true"))

((boolean) @boolean.false
  (#eq? @boolean.false "false"))
