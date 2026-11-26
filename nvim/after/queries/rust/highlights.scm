; extends

((boolean_literal) @boolean.true
  (#eq? @boolean.true "true"))

((boolean_literal) @boolean.false
  (#eq? @boolean.false "false"))

((identifier) @constructor
  (#any-of? @constructor "Some" "Ok" "Err")
  (#set! priority 105))

(lifetime "'" @attribute
  (#set! priority 105))

[
  "=>"
  "_"
] @operator
