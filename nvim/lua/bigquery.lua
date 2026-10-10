local M = {}
local projects = {}
local fold_windows = {}
local fold_origins = {}
local fold_expr = "v:lua.vim.treesitter.foldexpr()"

local function read_config(path)
	if vim.fn.filereadable(path) ~= 1 then
		return nil
	end
	local ok, settings = pcall(function()
		return vim.json.decode(table.concat(vim.fn.readfile(path), "\n"))
	end)
	if
		not ok
		or type(settings) ~= "table"
		or vim.islist(settings)
		or (settings.language ~= nil and type(settings.language) ~= "string")
	then
		return nil, "Invalid formatter config: " .. path
	end
	return settings
end

local function project(path)
	local root = vim.fs.root(path, ".git")
	local dir = vim.fs.dirname(vim.fs.normalize(path))
	local home = vim.fs.normalize(vim.fn.expand("~"))
	local config
	-- Prefer the nearest project config, including projects without Git.
	-- The home config supplies style, never project identity.
	while dir and dir ~= home do
		local candidate = dir .. "/.sql-formatter.json"
		if vim.fn.filereadable(candidate) == 1 then
			config = candidate
			break
		end
		if dir == root then
			break
		end
		local parent = vim.fs.dirname(dir)
		if parent == dir then
			break
		end
		dir = parent
	end
	local settings, warning
	if config then
		settings, warning = read_config(config)
	end
	local remote
	if root then
		if projects[root] == nil then
			local result = vim.system({ "git", "-C", root, "config", "--get", "remote.origin.url" }, { text = true })
				:wait(1000)
			projects[root] = result.code == 0 and vim.trim(result.stdout or ""):gsub("%.git$", "") or ""
		end
		remote = projects[root]
	end
	return { root = root, config = config, settings = settings, warning = warning, remote = remote }
end

function M.detect(path, buf)
	local context = project(path)
	local lower = path:lower()
	if lower:match("%.bqsql$") or lower:match("%.bigquery%.sql$") or lower:match("%.bq%.sql$") then
		return "sql.bigquery", "filename", context
	end
	if buf and vim.api.nvim_buf_is_valid(buf) then
		for _, line in ipairs(vim.api.nvim_buf_get_lines(buf, 0, 5, false)) do
			if line:lower():match("^%s*#standardsql%s*$") then
				return "sql.bigquery", "#standardSQL directive", context
			end
		end
	end
	if context.settings and type(context.settings.language) == "string" then
		local language = context.settings.language:lower()
		return language == "bigquery" and "sql.bigquery" or "sql", "project config (" .. language .. ")", context
	end
	if context.remote and context.remote:match("[:/]easypost%-sandbox/looker%-development$") then
		return "sql.bigquery", "repository origin", context
	end
	return "sql", "generic SQL fallback", context
end

function M.formatter_config(buf)
	buf = buf or vim.api.nvim_get_current_buf()
	local context = project(vim.api.nvim_buf_get_name(buf))
	local global_path = vim.fn.expand("~/.sql-formatter.json")
	local global, warning = read_config(global_path)
	local settings = vim.tbl_extend("force", global or {}, context.settings or {})
	-- Global dialect settings must not turn unrelated SQL into BigQuery.
	settings.language = context.settings and context.settings.language or "sql"
	if vim.bo[buf].filetype == "sql.bigquery" then
		settings.language = "bigquery"
	end
	return settings, context.config or global_path, context.warning or warning
end

function M.project_formatter_config(buf)
	local context = project(vim.api.nvim_buf_get_name(buf or vim.api.nvim_get_current_buf()))
	return context.settings or vim.empty_dict(), context.warning
end

function M.refresh(buf)
	projects = {}
	buf = buf or vim.api.nvim_get_current_buf()
	local path = vim.api.nvim_buf_get_name(buf)
	local ft = vim.bo[buf].filetype
	if
		ft ~= "sql"
		and ft ~= "sql.bigquery"
		and not path:lower():match("%.sql$")
		and not path:lower():match("%.bqsql$")
	then
		return
	end
	ft = M.detect(path, buf)
	for _, client in ipairs(vim.lsp.get_clients({ bufnr = buf })) do
		local filetypes = client.config.filetypes
		if filetypes and not vim.tbl_contains(filetypes, ft) then
			vim.lsp.buf_detach_client(buf, client.id)
		end
	end
	if vim.bo[buf].filetype ~= ft then
		vim.bo[buf].filetype = ft
	end
end

function M.setup_project(buf)
	buf = buf or vim.api.nvim_get_current_buf()
	local path = vim.api.nvim_buf_get_name(buf)
	if path == "" then
		error("Open a named SQL file before running BigQuerySetup", 0)
	end
	local ft = vim.bo[buf].filetype
	if
		ft ~= "sql"
		and ft ~= "sql.bigquery"
		and not path:lower():match("%.sql$")
		and not path:lower():match("%.bqsql$")
	then
		error("BigQuerySetup requires a SQL buffer", 0)
	end
	local context = project(path)
	if context.warning then
		error(context.warning, 0)
	end
	local config = context.config or (context.root or vim.fs.dirname(path)) .. "/.sql-formatter.json"
	if vim.fs.normalize(vim.fs.dirname(config)) == vim.fs.normalize(vim.fn.expand("~")) then
		error("Use a project directory for BigQuerySetup; for this buffer, use :setfiletype sql.bigquery", 0)
	end
	local config_buf = vim.fn.bufnr(config)
	if config_buf ~= -1 and vim.bo[config_buf].modified then
		error("Save the pending edits to " .. config .. " before running BigQuerySetup", 0)
	end
	local settings = vim.tbl_extend("force", context.settings or {}, { language = "bigquery" })
	if vim.fn.writefile({ vim.json.encode(settings) }, config) ~= 0 then
		error("Unable to write " .. config, 0)
	end
	if config_buf ~= -1 then
		vim.cmd.checktime(config_buf)
	end
	-- Redetect all loaded SQL buffers sharing this config so their parser,
	-- formatter and LSP change together.
	for _, candidate in ipairs(vim.api.nvim_list_bufs()) do
		if vim.api.nvim_buf_is_loaded(candidate) then
			local candidate_path = vim.api.nvim_buf_get_name(candidate)
			if candidate_path ~= "" and project(candidate_path).config == config then
				M.refresh(candidate)
			end
		end
	end
	return config
end

function M.info(buf)
	buf = buf or vim.api.nvim_get_current_buf()
	local detected, reason, context = M.detect(vim.api.nvim_buf_get_name(buf), buf)
	local settings, config, warning = M.formatter_config(buf)
	local is_bigquery = vim.bo[buf].filetype == "sql.bigquery"
	local command = is_bigquery and "sql-format-bigquery" or "sql-formatter"
	if is_bigquery then
		warning = context.warning
	end
	local lang = vim.treesitter.language.get_lang(vim.bo[buf].filetype)
	local revision_path = vim.fn.stdpath("data") .. "/site/parser-info/" .. (lang or "sql") .. ".revision"
	local revision = vim.fn.filereadable(revision_path) == 1 and vim.fn.readfile(revision_path)[1] or "unknown"
	local lines = {
		"Filetype: " .. vim.bo[buf].filetype .. " (detected: " .. detected .. ")",
		"Detection: " .. reason,
		"Project: " .. (context.root or "no Git root"),
		"Parser: " .. (lang or "none") .. " @ " .. revision,
		"Formatter: " .. command .. " (" .. settings.language .. ")",
		"Formatter config: " .. (is_bigquery and (context.config or vim.fn.expand("~/.sqlfluff")) or config),
	}
	if is_bigquery then
		table.insert(
			lines,
			"SQLFluff defaults: " .. vim.fn.expand("~/.sqlfluff") .. "; project .sqlfluff takes precedence"
		)
	end
	if warning then
		table.insert(lines, warning)
	end
	local ok, parser = pcall(vim.treesitter.get_parser, buf, lang)
	if not ok or not parser then
		table.insert(lines, "Parse: parser unavailable")
	else
		local parsed, trees = pcall(parser.parse, parser)
		if not parsed or not trees or not trees[1] then
			table.insert(lines, "Parse: unable to parse buffer")
		else
			local errors = {}
			local function visit(node)
				if node:type() == "ERROR" or node:missing() then
					local row, col = node:range()
					table.insert(errors, ("%s at %d:%d"):format(node:type(), row + 1, col + 1))
				end
				if #errors >= 8 then
					return
				end
				for child in node:iter_children() do
					if child:has_error() or child:missing() then
						visit(child)
						if #errors >= 8 then
							break
						end
					end
				end
			end
			visit(trees[1]:root())
			table.insert(
				lines,
				#errors == 0 and "Parse: no SQL syntax errors" or "Parse: " .. table.concat(errors, "; ")
			)
		end
	end
	table.insert(lines, command .. " executable: " .. (vim.fn.executable(command) == 1 and "available" or "missing"))
	return lines
end

local function folds()
	-- Filetype is buffer-local; fold options are window-local. Redetection must
	-- restore every split, including newly split windows that inherited our expr.
	for _, win in ipairs(vim.api.nvim_list_wins()) do
		local buf = vim.api.nvim_win_get_buf(win)
		local options = vim.wo[win]
		if vim.bo[buf].filetype == "sql.bigquery" then
			if not fold_windows[win] then
				local previous = { method = options.foldmethod, expr = options.foldexpr, level = options.foldlevel }
				if previous.expr == fold_expr and fold_origins[buf] then
					previous = vim.deepcopy(fold_origins[buf])
				end
				fold_origins[buf] = fold_origins[buf] or vim.deepcopy(previous)
				fold_windows[win] = previous
				options.foldmethod = "expr"
				options.foldexpr = fold_expr
				options.foldlevel = 99
			end
			fold_origins[buf] = fold_origins[buf] or vim.deepcopy(fold_windows[win])
		elseif fold_windows[win] then
			local previous = fold_windows[win]
			if options.foldexpr == fold_expr then
				options.foldmethod = previous.method
				options.foldexpr = previous.expr
				options.foldlevel = previous.level
			end
			fold_windows[win] = nil
		end
	end
	-- Hidden buffers retain their per-window fold options. Keep their originals
	-- until BufWipeout so reopening them cannot mistake our expr for the user's.
end

function M.setup()
	vim.treesitter.language.register("sql_bigquery", "sql.bigquery")
	vim.filetype.add({
		extension = {
			bqsql = "sql.bigquery",
			sql = function(path, buf)
				local ft = M.detect(path, buf)
				return ft
			end,
		},
	})
	vim.treesitter.query.add_predicate("bigquery-regex-pattern?", function(match, _, source, predicate)
		local name = vim.treesitter.get_node_text(match[predicate[2]][1], source):upper():gsub("^SAFE%.", "")
		local functions = {
			REGEXP_CONTAINS = true,
			REGEXP_EXTRACT = true,
			REGEXP_EXTRACT_ALL = true,
			REGEXP_SUBSTR = true,
			REGEXP_REPLACE = true,
			REGEXP_INSTR = true,
		}
		if not functions[name] then
			return false
		end
		local text = vim.treesitter.get_node_text(match[predicate[3]][1], source)
		-- Escaped SQL strings must be decoded before regex parsing. Raw strings
		-- and plain strings without SQL escapes can be injected without distortion.
		local prefix = text:match("^[rRbB]*") or ""
		return prefix:lower():find("r", 1, true) ~= nil or not text:find("\\", 1, true)
	end, { force = true })
	vim.treesitter.query.add_predicate("bigquery-statement?", function(match, _, _, predicate)
		return match[predicate[2]][1]:type():match("_statement$") ~= nil
	end, { force = true })
	-- SQL strings hide their scanner tokens. Trim raw prefixes and single or
	-- triple quotes dynamically so regex injection ranges contain only the pattern.
	vim.treesitter.query.add_directive("bigquery-regex-content!", function(match, _, source, predicate, metadata)
		local id = predicate[2]
		local node = match[id][1]
		local text = vim.treesitter.get_node_text(node, source)
		local prefix = text:match("^[rRbB]*") or ""
		local quote = text:sub(#prefix + 1, #prefix + 1)
		local width = text:sub(#prefix + 1, #prefix + 3) == quote:rep(3) and 3 or 1
		local sr, sc, er, ec = node:range()
		metadata[id] = metadata[id] or {}
		metadata[id].range = { sr, sc + #prefix + width, er, ec - width }
	end, { force = true })
	vim.treesitter.query.add_directive("bigquery-call-inner!", function(match, _, _, predicate, metadata)
		local id = predicate[2]
		local sr, sc
		for child in match[id][1]:iter_children() do
			if child:type() == "(" then
				_, _, sr, sc = child:range()
			elseif child:type() == ")" and sr then
				local er, ec = child:range()
				metadata[id] = metadata[id] or {}
				metadata[id].range = { sr, sc, er, ec }
				break
			end
		end
	end, { force = true })
	vim.treesitter.query.add_directive("bigquery-with-comma!", function(match, _, _, predicate, metadata)
		local id = predicate[2]
		local node = match[id][1]
		local sr, sc, er, ec = node:range()
		local next_node, previous = node:next_sibling(), node:prev_sibling()
		while next_node and next_node:extra() do
			next_node = next_node:next_sibling()
		end
		while previous and previous:extra() do
			previous = previous:prev_sibling()
		end
		if next_node and next_node:type() == "," then
			_, _, er, ec = next_node:range()
		elseif previous and previous:type() == "," then
			sr, sc = previous:range()
		end
		metadata[id] = metadata[id] or {}
		metadata[id].range = { sr, sc, er, ec }
	end, { force = true })
	local group = vim.api.nvim_create_augroup("bigquery", { clear = true })
	vim.api.nvim_create_autocmd({ "FileType", "BufWinEnter", "WinNew" }, { group = group, callback = folds })
	vim.api.nvim_create_autocmd("WinClosed", {
		group = group,
		callback = function(args)
			fold_windows[tonumber(args.match)] = nil
		end,
	})
	vim.api.nvim_create_autocmd("BufWipeout", {
		group = group,
		callback = function(args)
			fold_origins[args.buf] = nil
		end,
	})
	vim.api.nvim_create_autocmd("FileType", {
		group = group,
		callback = function(args)
			if vim.bo[args.buf].filetype ~= "sql.bigquery" then
				for _, mode in ipairs({ "n", "x", "o" }) do
					for _, mapping in ipairs(vim.api.nvim_buf_get_keymap(args.buf, mode)) do
						if mapping.desc and mapping.desc:match("^BigQuery:") then
							vim.keymap.del(mode, mapping.lhs, { buffer = args.buf })
						end
					end
				end
				return
			end
			local select = require("nvim-treesitter-textobjects.select")
			local move = require("nvim-treesitter-textobjects.move")
			local swap = require("nvim-treesitter-textobjects.swap")
			local function bind(modes, key, action, capture, desc)
				vim.keymap.set(modes, key, function()
					action(capture, "textobjects")
				end, { buffer = args.buf, desc = "BigQuery: " .. desc })
			end
			bind({ "x", "o" }, "ae", select.select_textobject, "@select.outer", "SELECT expression")
			bind({ "x", "o" }, "ie", select.select_textobject, "@select.inner", "Inside SELECT expression")
			bind("n", "]e", move.goto_next_start, "@select.outer", "Next SELECT expression")
			bind("n", "[e", move.goto_previous_start, "@select.outer", "Previous SELECT expression")
			-- SQL's ftplugin has buffer-local motions which override global TS maps.
			bind("n", "]]", move.goto_next_start, "@class.outer", "Next CTE")
			bind("n", "[[", move.goto_previous_start, "@class.outer", "Previous CTE")
			bind("n", "]m", move.goto_next_start, "@function.outer", "Next function")
			bind("n", "[m", move.goto_previous_start, "@function.outer", "Previous function")
			bind("n", "]s", move.goto_next_start, "@statement.outer", "Next statement")
			bind("n", "[s", move.goto_previous_start, "@statement.outer", "Previous statement")
			bind("n", "]a", move.goto_next_start, "@parameter.inner", "Next argument")
			bind("n", "[a", move.goto_previous_start, "@parameter.inner", "Previous argument")
			bind("n", "<leader>]c", swap.swap_next, "@class.outer", "Swap CTE forward")
			bind("n", "<leader>[c", swap.swap_previous, "@class.outer", "Swap CTE backward")
			bind("n", "<leader>]e", swap.swap_next, "@select.inner", "Swap SELECT expression forward")
			bind("n", "<leader>[e", swap.swap_previous, "@select.inner", "Swap SELECT expression backward")
			bind("n", "<leader>]s", swap.swap_next, "@statement.outer", "Swap statement forward")
			bind("n", "<leader>[s", swap.swap_previous, "@statement.outer", "Swap statement backward")
		end,
	})
	vim.api.nvim_create_user_command("BigQueryInfo", function(opts)
		if opts.bang then
			M.refresh()
		end
		vim.api.nvim_echo({ { table.concat(M.info(), "\n") } }, true, {})
	end, { bang = true, desc = "Show SQL dialect, parser and formatter; ! refreshes detection", force = true })
	vim.api.nvim_create_user_command("BigQuerySetup", function()
		local ok, result = pcall(M.setup_project)
		vim.notify(
			ok and ("BigQuery configured: " .. result) or result,
			ok and vim.log.levels.INFO or vim.log.levels.ERROR
		)
	end, { desc = "Save BigQuery project config and refresh open SQL buffers", force = true })
end

return M
