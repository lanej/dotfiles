local M = {}
local root = vim.fn.fnamemodify(vim.fn.resolve(debug.getinfo(1, "S").source:sub(2)), ":h:h:h")
local helper = root .. "/scripts/file-history.py"
local queued, pending, scheduled = {}, {}, false

local function report(result)
	if result.code ~= 0 then
		vim.schedule(function()
			vim.notify("File history: " .. (result.stderr or "recording failed"), vim.log.levels.ERROR)
		end)
	end
end

function M.flush(wait)
	scheduled = false
	if #queued > 0 then
		local batch = queued
		queued = {}
		local entry = {}
		entry.job = vim.system({ "python3", helper, "record", "--stdin" }, {
			stdin = vim.json.encode(batch),
			text = true,
		}, function(result)
			entry.done = true
			report(result)
		end)
		pending[#pending + 1] = entry
	end
	-- Waiting pumps Neovim's event loop; a deferred batch may reenter this function.
	local processing = pending
	pending = {}
	local remaining = {}
	for _, entry in ipairs(processing) do
		if wait and not entry.done then
			entry.job:wait(5000)
		end
		if not entry.done then
			remaining[#remaining + 1] = entry
		end
	end
	vim.list_extend(pending, remaining)
end

function M.setup()
	local group = vim.api.nvim_create_augroup("DotfilesFileHistory", { clear = true })
	local function visit()
		local file = vim.api.nvim_buf_get_name(0)
		if vim.bo.buftype ~= "" or not vim.bo.buflisted or vim.fn.filereadable(file) ~= 1 then
			return
		end
		queued[#queued + 1] = file
		if not scheduled then
			scheduled = true
			vim.defer_fn(M.flush, 200)
		end
	end
	vim.api.nvim_create_autocmd("BufEnter", { group = group, callback = visit })
	vim.api.nvim_create_autocmd("VimLeavePre", {
		group = group,
		callback = function()
			M.flush(true)
		end,
	})
	visit()
end

function M.files(opts)
	M.flush(true)
	opts = vim.deepcopy(opts or {})
	if opts.follow == nil then
		opts.follow = true
	end
	if opts.git then
		local result = vim.system(
			{ "git", "-C", opts.cwd or vim.fn.getcwd(), "rev-parse", "--show-toplevel" },
			{ text = true }
		)
			:wait()
		if result.code ~= 0 then
			vim.notify(result.stderr, vim.log.levels.ERROR)
			return
		end
		opts.cwd = result.stdout:gsub("\n$", "")
	end
	local command = { "python3", helper, "files" }
	for _, flag in ipairs({ "global", "hidden", "no_ignore", "git" }) do
		if opts[flag] then
			command[#command + 1] = "--" .. flag:gsub("_", "-")
		end
	end
	if not opts.follow then
		command[#command + 1] = "--no-follow"
	end
	local source = vim.deepcopy(opts)
	opts.actions = opts.actions or {}
	for key, option in pairs({ ["alt-i"] = "no_ignore", ["alt-h"] = "hidden", ["alt-f"] = "follow" }) do
		opts.actions[key] = function(_, current)
			local next_opts = vim.deepcopy(source)
			next_opts[option] = not current[option]
			next_opts.query = current.last_query or ""
			vim.schedule(function()
				M.files(next_opts)
			end)
		end
	end
	opts.cmd = table.concat(vim.tbl_map(vim.fn.shellescape, command), " ")
	-- The helper owns fd flags; FzfLua must not insert them before Python's script.
	opts.raw_cmd = opts.cmd
	opts.fzf_opts = vim.tbl_extend(
		"force",
		opts.fzf_opts or {},
		{ ["--tiebreak"] = "index", ["--smart-case"] = true, ["--keep-right"] = true }
	)
	opts.prompt = opts["global"] and "Frecent Files❯ " or "Files❯ "
	return require("fzf-lua").files(opts)
end

return M
