-- Run through the installed configuration:
-- nvim --headless -i NONE '+lua dofile("nvim/tests/bigquery.lua")' '+qa!'
local temp = vim.fn.tempname()
local source = {
	"WITH addresses AS (",
	"  SELECT '123 Main St' AS street",
	"), normalized AS (",
	"  SELECT REGEXP_REPLACE(street, r'[^A-Z0-9]+', ' ') AS street",
	"  FROM addresses",
	")",
	"SELECT street, REGEXP_CONTAINS(street, r'^[0-9]+ .*?[A-Z]') AS valid",
	"FROM normalized",
	"QUALIFY",
	"  ROW_NUMBER() OVER (",
	"    PARTITION BY street",
	"    ORDER BY street",
	"  ) = 1;",
}
local function open(path, lines)
	vim.fn.writefile(lines, path)
	vim.cmd.edit(vim.fn.fnameescape(path))
end
local function text(range)
	return table.concat(vim.api.nvim_buf_get_text(0, range[1], range[2], range[4], range[5], {}), "\n")
end
local function save()
	vim.cmd.write()
	assert(
		vim.deep_equal(vim.fn.readfile(vim.api.nvim_buf_get_name(0)), vim.api.nvim_buf_get_lines(0, 0, -1, false)),
		"Write did not persist the formatted buffer"
	)
end
local function workflow()
	vim.o.columns = 120
	vim.o.lines = 40
	vim.fn.mkdir(temp, "p")
	vim.fn.writefile({ '{"keywordCase":"lower","tabWidth":4}' }, temp .. "/.sql-formatter.json")
	open(temp .. "/addresses.sql", source)
	assert(vim.bo.filetype == "sql", "Style-only config must retain generic SQL")
	vim.cmd.BigQuerySetup()
	local settings = vim.json.decode(table.concat(vim.fn.readfile(temp .. "/.sql-formatter.json"), "\n"))
	assert(settings.language == "bigquery", "Setup did not save the project dialect")
	assert(settings.keywordCase == "lower" and settings.tabWidth == 4, "Setup overwrote formatter preferences")
	assert(vim.bo.filetype == "sql.bigquery", "Setup did not refresh the open SQL buffer")

	-- Formatting detector: write through the actual save hook and formatter.
	save()
	local formatted = table.concat(vim.api.nvim_buf_get_lines(0, 0, -1, false), "\n")
	assert(formatted:match("^with%s+addresses as"), "Formatter ignored project keywordCase")
	assert(formatted:find("\n    select", 1, true), "Formatter ignored project indentation")
	vim.api.nvim_buf_set_lines(0, 0, -1, false, source)
	vim.fn.writefile({ '{"language":"bigquery"}' }, temp .. "/.sql-formatter.json")
	save()
	assert(
		vim.deep_equal(source, vim.api.nvim_buf_get_lines(0, 0, -1, false)),
		"Default formatting must preserve the compact reference layout"
	)
	local misindented = vim.deepcopy(source)
	misindented[2] = " " .. source[2]:sub(3)
	misindented[4] = "     " .. source[4]:sub(3)
	misindented[9] = "QUALIFY ROW_NUMBER() OVER ("
	table.remove(misindented, 10)
	vim.api.nvim_buf_set_lines(0, 0, -1, false, misindented)
	save()
	assert(
		vim.deep_equal(source, vim.api.nvim_buf_get_lines(0, 0, -1, false)),
		"Default formatting must repair indentation and put QUALIFY's window on its own line"
	)
	vim.fn.writefile({
		"[sqlfluff:rules:capitalisation.keywords]",
		"capitalisation_policy = lower",
	}, temp .. "/.sqlfluff")
	save()
	assert(
		vim.api.nvim_buf_get_lines(0, 0, 1, false)[1]:match("^with addresses as"),
		"Native project SQLFluff rules must override home defaults"
	)
	vim.fn.writefile({ "addresses.sql" }, temp .. "/.sqlfluffignore")
	local ignored = vim.system(
		{ "sql-format-bigquery", "--stdin-filename", temp .. "/addresses.sql" },
		{ text = true, stdin = table.concat(source, "\n") }
	):wait(5000)
	assert(ignored.code ~= 0 and ignored.stdout == "", "Ignored SQL must fail without replacement output")
	vim.fn.delete(temp .. "/.sqlfluff")
	vim.fn.delete(temp .. "/.sqlfluffignore")
	vim.api.nvim_buf_set_lines(0, 0, -1, false, source)

	-- Textobject detector: use installed selection/movement/swap behavior.
	local shared = require("nvim-treesitter-textobjects.shared")
	local cte = assert(shared.textobject_at_point("@class.outer", "textobjects", 0, { 1, 5 }))
	assert(text(cte):match("^addresses AS %("), "CTE textobject unavailable")
	local inner = assert(shared.textobject_at_point("@class.inner", "textobjects", 0, { 1, 5 }))
	assert(text(inner):match("^SELECT"), "Inner CTE must exclude name and parentheses")
	vim.api.nvim_win_set_cursor(0, { 1, 5 })
	vim.cmd.normal("]]")
	assert(vim.api.nvim_win_get_cursor(0)[1] == 3, "CTE movement failed")
	vim.api.nvim_win_set_cursor(0, { 7, 8 })
	local expression = assert(shared.textobject_at_point("@select.outer", "textobjects"))
	assert(text(expression) == "street,", "SELECT expression must include its separator")
	vim.api.nvim_win_set_cursor(0, { 4, 24 })
	local call = assert(shared.textobject_at_point("@function.inner", "textobjects"))
	assert(text(call) == "street, r'[^A-Z0-9]+', ' '", "Function inner range is incorrect")
	require("nvim-treesitter-textobjects.swap").swap_next("@parameter.inner", "textobjects")
	vim.api.nvim_feedkeys("", "x", false)
	local swapped = vim.api.nvim_buf_get_lines(0, 3, 4, false)[1]
	assert(swapped:find("REGEXP_REPLACE(r'[^A-Z0-9]+', street, ' ')", 1, true), "Argument swap failed")
	vim.api.nvim_buf_set_lines(0, 0, -1, false, source)
	vim.api.nvim_win_set_cursor(0, { 7, 8 })
	vim.cmd.normal(vim.g.mapleader .. "]e")
	vim.api.nvim_feedkeys("", "x", false)
	assert(
		vim.api.nvim_buf_get_lines(0, 6, 7, false)[1]
			== "SELECT REGEXP_CONTAINS(street, r'^[0-9]+ .*?[A-Z]') AS valid, street",
		"SELECT expression swap damaged separators"
	)
	vim.api.nvim_buf_set_lines(0, 0, -1, false, source)
	vim.api.nvim_buf_set_lines(0, 6, 7, false, {
		"SELECT street /* documented */, REGEXP_CONTAINS(street, r'^[0-9]+ .*?[A-Z]') AS valid",
	})
	vim.api.nvim_win_set_cursor(0, { 7, 8 })
	vim.cmd.normal("dae")
	assert(
		not vim.treesitter.get_parser(0):parse(true)[1]:root():has_error(),
		"Deleting a documented SELECT expression left an invalid separator"
	)
	vim.api.nvim_buf_set_lines(0, 0, -1, false, source)

	-- Folding detector: close the first CTE through the normal editor command.
	vim.api.nvim_win_set_cursor(0, { 2, 5 })
	vim.cmd.normal("zx")
	vim.cmd.normal("zc")
	assert(vim.fn.foldclosed(2) == 1 and vim.fn.foldclosedend(2) == 2, "CTE fold is missing or too broad")
	vim.cmd.normal("zR")
	local query_buffer = vim.api.nvim_get_current_buf()
	vim.cmd.enew()
	vim.cmd.buffer(query_buffer)
	local first_window = vim.api.nvim_get_current_win()
	vim.cmd.vsplit()
	local second_window = vim.api.nvim_get_current_win()
	assert(vim.wo[second_window].foldexpr == "v:lua.vim.treesitter.foldexpr()", "Split did not inherit SQL folding")

	-- Regex detector: inspect actual injected highlight captures at character positions.
	local parser = vim.treesitter.get_parser(0)
	parser:parse(true)
	local table_highlight = false
	for _, capture in ipairs(vim.treesitter.get_captures_at_pos(0, 7, 5)) do
		table_highlight = table_highlight or capture.capture == "module"
	end
	assert(table_highlight, "Table reference is missing its semantic highlight")
	for _, capture in ipairs(vim.treesitter.get_captures_at_pos(0, 6, 7)) do
		assert(capture.capture ~= "module", "Column reference was highlighted as a table")
	end
	local regex = assert(parser:children().regex, "Pattern was not injected as regex")
	assert(#regex:trees() == 2, "Input/replacement strings must not become regex trees")
	local groups = {}
	local quantifier = source[4]:find("+", 1, true) - 1
	for _, capture in ipairs(vim.treesitter.get_captures_at_pos(0, 3, quantifier)) do
		groups[capture.capture] = true
	end
	assert(groups["operator"], "Regex quantifier must have an operator highlight")
	groups = {}
	local replacement = source[4]:find("' '", 1, true)
	for _, capture in ipairs(vim.treesitter.get_captures_at_pos(0, 3, replacement)) do
		groups[capture.capture] = true
	end
	assert(not groups["operator"], "Replacement text must retain SQL string highlighting")

	-- Info/refresh detector: change the config in a live buffer and redetect it.
	local report = vim.api.nvim_exec2("BigQueryInfo", { output = true }).output
	assert(report:find("project config (bigquery)", 1, true), "Info omitted detection reason")
	assert(report:find("db6ed431", 1, true), "Info omitted installed parser revision")
	assert(report:find("Parse: no SQL syntax errors", 1, true), "Info omitted parse status")
	vim.fn.writefile({ '{"language":"postgresql","keywordCase":"lower"}' }, temp .. "/.sql-formatter.json")
	vim.cmd.BigQueryInfo({ bang = true })
	assert(vim.bo.filetype == "sql", "Bang command did not redetect the live buffer")
	assert(
		vim.wo[first_window].foldexpr ~= "v:lua.vim.treesitter.foldexpr()",
		"BigQuery folds leaked in original split"
	)
	assert(vim.wo[second_window].foldexpr ~= "v:lua.vim.treesitter.foldexpr()", "BigQuery folds leaked in new split")
	assert(require("bigquery").formatter_config(0).language == "postgresql", "Project dialect was not retained")
	vim.cmd.close()
	open(temp .. "-generic.sql", { "SELECT    1 AS value;" })
	assert(vim.bo.filetype == "sql", "Generic SQL changed dialect")
	assert(require("bigquery").formatter_config(0).language == "sql", "Global config leaked its dialect")
	save()
	assert(
		vim.fn.readfile(temp .. "-generic.sql")[1] ~= "SELECT    1 AS value;",
		"Generic SQL was not formatted on write"
	)
	print("BigQuery editor: formatting, textobjects, folding, regex highlights and info/refresh passed")
end
local ok, err = xpcall(workflow, debug.traceback)
vim.fn.delete(temp, "rf")
vim.fn.delete(temp .. "-generic.sql")
if not ok then
	vim.api.nvim_err_writeln(err)
	vim.cmd.cquit(1)
end
