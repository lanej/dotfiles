local M = {}

local function git(root, args)
	return vim.system(vim.list_extend({ "git", "-C", root }, args), {}):wait()
end

local function disk_options(file)
	local fd = vim.uv.fs_open(file, "r", 438)
	if not fd then
		return
	end
	local stat = vim.uv.fs_fstat(fd)
	local offset, previous, dos = 0, "", false
	local read_ok = stat ~= nil
	while stat and offset < stat.size do
		local chunk = vim.uv.fs_read(fd, math.min(stat.size - offset, 4096), offset)
		if not chunk or #chunk == 0 then
			read_ok = false
			break
		end
		local newline = chunk:find("\n", 1, true)
		if newline then
			dos = (newline == 1 and previous or chunk:sub(newline - 1, newline - 1)) == "\r"
			break
		end
		previous = chunk:sub(-1)
		offset = offset + #chunk
	end
	local tail = stat and vim.uv.fs_read(fd, math.min(stat.size, 2), math.max(stat.size - 2, 0))
	vim.uv.fs_close(fd)
	if not read_ok or not tail then
		return
	end
	return {
		endofline = stat.size == 0 or tail:sub(-1) == "\n",
		fileformat = dos and "dos" or "unix",
		-- The native disk preview retains raw bytes, including any BOM.
		bomb = false,
		fileencoding = "",
	}
end

local function previewer(base)
	local native = require("fzf-lua.previewer.builtin").buffer_or_file
	local preview = native:extend()
	function preview:attach_git(entry)
		local buf = self.preview_bufnr
		if not buf or not entry.path or entry.cmd or entry.terminal then
			return
		end
		local options
		if entry.bufnr and vim.api.nvim_buf_is_loaded(entry.bufnr) then
			options = {}
			for _, name in ipairs({ "endofline", "bomb", "fileformat", "fileencoding" }) do
				options[name] = vim.bo[entry.bufnr][name]
			end
		else
			options = disk_options(entry.path)
		end
		if not options then
			return
		end
		for name, value in pairs(options) do
			vim.bo[buf][name] = value
		end
		require("git-branch-signs").set_preview_base(buf, base)
		require("gitsigns").attach(buf, { file = entry.path })
	end
	function preview:do_syntax(entry)
		native.do_syntax(self, entry)
		-- Filetype detection can rename the scratch buffer and detach Gitsigns.
		self:attach_git(entry)
	end
	function preview:preview_buf_post(entry, minimal)
		native.preview_buf_post(self, entry, minimal)
		if not self.syntax then
			self:attach_git(entry)
		end
	end
	return preview
end

function M.pick()
	local root_result = vim.system({ "git", "rev-parse", "--show-toplevel" }, {}):wait()
	if root_result.code ~= 0 then
		vim.notify("Not in a git repository", vim.log.levels.ERROR)
		return
	end
	local root = root_result.stdout:gsub("\n$", "")
	local default_branch
	local origin_head = git(root, { "symbolic-ref", "refs/remotes/origin/HEAD" })
	if origin_head.code == 0 then
		default_branch = vim.trim(origin_head.stdout)
	else
		for _, ref in ipairs({ "origin/main", "origin/master" }) do
			if git(root, { "rev-parse", "--verify", ref }).code == 0 then
				default_branch = ref
				break
			end
		end
	end
	local base
	if default_branch then
		local result = git(root, { "merge-base", "HEAD", default_branch })
		if result.code == 0 then
			base = vim.trim(result.stdout)
		end
	end
	local has_head = git(root, { "rev-parse", "--verify", "HEAD" }).code == 0
	local statuses = {}
	local function diff(args)
		local result =
			git(root, vim.list_extend({ "diff", "--no-ext-diff", "--no-renames", "--name-status", "-z" }, args))
		if result.code ~= 0 then
			vim.notify(result.stderr, vim.log.levels.ERROR)
			return false
		end
		local fields = vim.split(result.stdout, "\0", { plain = true, trimempty = true })
		for i = 1, #fields, 2 do
			statuses[fields[i + 1]] = fields[i]
		end
		return true
	end
	if base and not diff({ base, "HEAD", "--" }) then
		return
	end
	if not diff({ "--cached", "--" }) or not diff({ "--" }) then
		return
	end
	-- The cumulative diff keeps a branch-added file marked A after further edits.
	if has_head and not diff({ base or "HEAD", "--" }) then
		return
	end
	local untracked = git(root, { "ls-files", "--others", "--exclude-standard", "-z" })
	if untracked.code ~= 0 then
		vim.notify(untracked.stderr, vim.log.levels.ERROR)
		return
	end
	for _, file in ipairs(vim.split(untracked.stdout, "\0", { plain = true, trimempty = true })) do
		statuses[file] = "??"
	end
	local files = vim.tbl_keys(statuses)
	table.sort(files)
	if #files == 0 then
		vim.notify("No changed files found", vim.log.levels.INFO)
		return
	end
	local fzf = require("fzf-lua")
	local entries = {}
	for _, file in ipairs(files) do
		local entry = fzf.make_entry.file(file, { file_icons = true, color_icons = true })
		entries[#entries + 1] = string.format("%-2s", statuses[file]) .. fzf.utils.nbsp .. entry
	end
	fzf.fzf_exec(entries, {
		cwd = root,
		prompt = "ChangedFiles❯ ",
		previewer = {
			_ctor = function()
				return previewer(base)
			end,
		},
		winopts = {
			preview = {
				vertical = "down:60%",
				horizontal = "right:60%",
				winopts = { signcolumn = "yes:1" },
			},
		},
		actions = {
			["default"] = function(selected, opts)
				if not selected or #selected == 0 then
					return
				end
				local file = fzf.path.entry_to_file(selected[1], opts).path
				require("fzf-lua.actions").file_edit(selected, opts)
				local current = vim.api.nvim_buf_get_name(0)
				if (vim.uv.fs_realpath(current) or current) ~= (vim.uv.fs_realpath(file) or file) then
					return
				end
				if not has_head then
					return
				end
				local result = git(root, { "diff", "--no-ext-diff", "--unified=0", base or "HEAD", "--", file })
				if result.code == 0 then
					local line = result.stdout:match("\n@@[^\n]-%+(%d+)")
					if line then
						local target = math.min(math.max(tonumber(line), 1), vim.api.nvim_buf_line_count(0))
						vim.api.nvim_win_set_cursor(0, { target, 0 })
						vim.cmd("normal! zz")
					end
				end
			end,
		},
	})
end

return M
