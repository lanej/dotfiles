; Existing ac/ic and [[/]] mappings operate on CTEs.
(cte (query_expr) @class.inner) @class.outer
(cte (query_expr) @block.inner) @block.outer
(select_subexpression (query_expr) @block.inner) @block.outer

; Function selection/movement and argument swapping use the existing mappings.
(function_call) @function.outer @call.outer
((function_call) @function.inner
  (#bigquery-call-inner! @function.inner))
((function_call) @call.inner
  (#bigquery-call-inner! @call.inner))
(argument) @parameter.inner
((argument) @parameter.outer
  (#bigquery-with-comma! @parameter.outer))

; SELECT list entries get dedicated ae/ie and ]e/[e buffer mappings.
(select_expression) @select.inner
(select_all) @select.inner
((select_expression) @select.outer
  (#bigquery-with-comma! @select.outer))
((select_all) @select.outer
  (#bigquery-with-comma! @select.outer))

((_) @statement.outer
  (#bigquery-statement? @statement.outer))
