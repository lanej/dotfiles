local M = {}

local function display(text)
	return text:gsub("[%c]", " ")
end

local function color(text, code)
	return "\27[" .. code .. "m" .. text .. "\27[0m"
end

local function column(text, width)
	text = display(text)
	if vim.fn.strdisplaywidth(text) > width then
		local prefix = vim.fn.strcharpart(text, 0, math.floor(width / 3))
		local suffix = vim.fn.strcharpart(text, vim.fn.strchars(text) - (width - vim.fn.strchars(prefix) - 1))
		text = prefix .. "…" .. suffix
		while vim.fn.strdisplaywidth(text) > width do
			suffix = vim.fn.strcharpart(suffix, 1)
			text = prefix .. "…" .. suffix
		end
	end
	return text .. string.rep(" ", width - vim.fn.strdisplaywidth(text))
end

local function age(timestamp, now)
	if not timestamp then
		return "?"
	end
	local seconds = math.max(0, now - timestamp)
	if seconds < 60 then
		return "now"
	elseif seconds < 3600 then
		return math.floor(seconds / 60) .. "m"
	elseif seconds < 86400 then
		return math.floor(seconds / 3600) .. "h"
	elseif seconds < 86400 * 365 then
		return math.floor(seconds / 86400) .. "d"
	end
	return math.floor(seconds / (86400 * 365)) .. "y"
end

local function parse_worktrees(output)
	local trees, tree = {}, nil
	for _, field in ipairs(vim.split(output, "\0", { plain = true })) do
		local key, value = field:match("^(%S+)%s(.*)$")
		if key == "worktree" then
			tree = { path = value }
			table.insert(trees, tree)
		elseif tree then
			if key == "HEAD" then
				tree.head = value
			elseif key == "branch" then
				tree.branch = value:gsub("^refs/heads/", "")
			elseif key == "locked" or field == "locked" then
				tree.locked = true
			elseif key == "prunable" or field == "prunable" then
				tree.prunable = true
			elseif field == "bare" then
				tree.bare = true
			end
		end
	end
	return trees
end

local function location(path, primary)
	if path == primary.path then
		return primary.reference and "reference" or "primary"
	elseif path:sub(1, #primary.path + 12) == primary.path .. "/.worktrees/" then
		return "local/" .. path:sub(#primary.path + 13)
	end
	local codex = path:match("/codex%-worktrees/([^/]+)/[^/]+$")
	if codex then
		return "codex/" .. codex
	end
	local home = vim.env.HOME
	if home and path:sub(1, #home + 1) == home .. "/" then
		return "~/" .. path:sub(#home + 2)
	end
	return path
end

local function changes(output)
	local counts = { staged = 0, modified = 0, untracked = 0, conflicts = 0 }
	local records = vim.split(output, "\0", { plain = true, trimempty = true })
	local i = 1
	while i <= #records do
		local status = records[i]:sub(1, 2)
		if status == "??" then
			counts.untracked = counts.untracked + 1
		elseif status:find("U") or status == "AA" or status == "DD" then
			counts.conflicts = counts.conflicts + 1
		else
			if status:sub(1, 1) ~= " " then
				counts.staged = counts.staged + 1
			end
			if status:sub(2, 2) ~= " " then
				counts.modified = counts.modified + 1
			end
		end
		-- With -z a rename/copy consumes a second record containing its old path.
		if status:find("[RC]") then
			i = i + 1
		end
		i = i + 1
	end
	return counts
end

local function summary(tree)
	if tree.prunable or not vim.uv.fs_stat(tree.path) then
		return "missing"
	elseif tree.status_error then
		return "status ?"
	elseif not tree.changes then
		return "loading"
	end
	local parts = {}
	if tree.ahead and (tree.ahead > 0 or tree.behind > 0) then
		table.insert(parts, color("↑" .. tree.ahead .. " ↓" .. tree.behind, 36))
	elseif not tree.ahead then
		table.insert(parts, color("↑? ↓?", 33))
	end
	local counts = tree.changes
	if counts.staged > 0 then
		table.insert(parts, color("S" .. counts.staged, 32))
	end
	if counts.modified > 0 then
		table.insert(parts, color("M" .. counts.modified, 33))
	end
	if counts.untracked > 0 then
		table.insert(parts, color("?" .. counts.untracked, 36))
	end
	if counts.conflicts > 0 then
		table.insert(parts, color("!" .. counts.conflicts, 31))
	end
	return #parts > 0 and table.concat(parts, " ") or color("clean", 32)
end

local function preview_command(tree, primary, height, width)
	local git = "git --no-optional-locks -C " .. vim.fn.shellescape(tree.path) .. " -c color.ui=always "
	-- Reserve space for commits and all three diff summaries.
	local file_limit = math.max(1, math.min(5, math.floor((height - 20) / 4)))
	local stats = height < 26 and "--shortstat" or ("--stat --stat-count=" .. file_limit .. " --stat-width=" .. width)
	local status_sample = vim.fn.shellescape([[
NR == 1 { print; next }
{ files++; if (files <= limit) print }
END { if (files > limit) printf "\033[2m... %d more files\033[0m\n", files - limit }
]])
	local function heading(text)
		return "printf '\\033[1;36m%s\\033[0m\\n' " .. vim.fn.shellescape(text)
	end
	return table.concat({
		"printf '%s\\n' " .. vim.fn.shellescape(display(tree.path)),
		heading("Working tree"),
		git
			.. "-c color.status=always status --short --branch --untracked-files=all"
			.. " | awk -v limit="
			.. file_limit
			.. " "
			.. status_sample,
		heading("Recent commits (Git age: latest HEAD reflog or commit)"),
		git .. "log -6 --color=always --date=relative --format='%C(yellow)%h%C(reset) %s %C(dim)(%cr)%C(reset)'",
		heading("Unstaged diff"),
		git .. "diff --no-ext-diff " .. stats .. " --color=always",
		heading("Staged diff"),
		git .. "diff --no-ext-diff --cached " .. stats .. " --color=always",
		heading(
			"Branch diff vs "
				.. (primary.reference and "reference" or "primary")
				.. " ("
				.. display(primary.branch or "detached")
				.. ")"
		),
		git .. "diff --no-ext-diff " .. stats .. " --color=always " .. vim.fn.shellescape(primary.head .. "...HEAD"),
	}, "; ")
end

function M.pick()
	local active = { jobs = {}, closed = false }
	local function cancel(run)
		run.closed = true
		if run.finish then
			run.finish()
			run.finish = nil
		end
		if run.autocmd then
			pcall(vim.api.nvim_del_autocmd, run.autocmd)
			run.autocmd = nil
		end
		for _, job in ipairs(run.jobs) do
			if not job:is_closing() then
				job:kill(15)
			end
		end
	end
	local function git(path, args, callback)
		local run = active
		local command = vim.list_extend({ "git", "--no-optional-locks", "-C", path }, args)
		local ok, job = pcall(
			vim.system,
			command,
			{ timeout = 5000 },
			vim.schedule_wrap(function(result)
				if not run.closed then
					callback(result)
				end
			end)
		)
		if ok then
			table.insert(run.jobs, job)
		else
			callback({ code = 1, stdout = "", stderr = tostring(job) })
		end
	end
	git(vim.fn.getcwd(), { "rev-parse", "--show-toplevel" }, function(root)
		if root.code ~= 0 then
			vim.notify("Not in a git repository", vim.log.levels.ERROR)
			return
		end
		local current = root.stdout:gsub("\n$", "")
		git(current, { "worktree", "list", "--porcelain", "-z" }, function(result)
			if result.code ~= 0 then
				vim.notify("Cannot list worktrees: " .. result.stderr, vim.log.levels.ERROR)
				return
			end
			local trees = parse_worktrees(result.stdout)
			local bare = trees[1] and trees[1].bare
			trees = vim.tbl_filter(function(tree)
				return not tree.bare
			end, trees)
			local primary = trees[1]
			if not primary or not primary.head then
				vim.notify("No working checkouts found", vim.log.levels.WARN)
				return
			end
			primary.reference = bare
			local by_id = {}
			for id, tree in ipairs(trees) do
				tree.id = id
				by_id[tostring(id)] = tree
			end
			local function resolve(entry)
				return entry and by_id[entry:match("^(%d+)\t")]
			end
			local branch_width, path_width = 26, 22
			local function row(tree, now)
				local branch = tree.branch or ("detached@" .. (tree.head or ""):sub(1, 7))
				if tree.locked then
					branch = branch .. " [locked]"
				end
				return tree.id
					.. "\t"
					.. (tree.current and "● " or "  ")
					.. column(branch, branch_width)
					.. "  "
					.. column(location(tree.path, primary), path_width)
					.. "  "
					.. column(age(tree.activity, now), 7)
					.. "  "
					.. summary(tree)
			end
			local fzf = require("fzf-lua")
			fzf.fzf_exec(function(cb)
				-- fzf-lua reuses this producer on resume. Each opening owns its jobs.
				cancel(active)
				active = { jobs = {}, closed = false }
				local run = active
				run.finish = cb
				-- Hiding a picker preserves its terminal and producer. Cancel only
				-- when that terminal exits or is wiped, including during inspection.
				run.autocmd = vim.api.nvim_create_autocmd({ "TermClose", "BufWipeout" }, {
					buffer = fzf.utils.fzf_winobj().fzf_bufnr,
					once = true,
					callback = function()
						cancel(run)
					end,
				})
				local cwd, current_tree = vim.uv.fs_realpath(vim.fn.getcwd()), nil
				for _, tree in ipairs(trees) do
					local path = vim.uv.fs_realpath(tree.path)
					if cwd and path and (cwd == path or cwd:sub(1, #path + 1) == path .. "/") then
						if not current_tree or #tree.path > #current_tree.path then
							current_tree = tree
						end
					end
					tree.activity, tree.ahead, tree.behind = nil, nil, nil
				end
				for _, tree in ipairs(trees) do
					tree.current = tree == current_tree
				end
				local pending, next_tree = #trees, 1
				local function complete()
					pending = pending - 1
					if pending == 0 then
						table.sort(trees, function(a, b)
							if a.current ~= b.current then
								return a.current
							elseif (a.activity or 0) ~= (b.activity or 0) then
								return (a.activity or 0) > (b.activity or 0)
							end
							return a.path < b.path
						end)
						local now = os.time()
						for _, tree in ipairs(trees) do
							cb(row(tree, now))
						end
						run.finish = nil
						cb()
					end
				end
				local inspect
				inspect = function()
					local tree = trees[next_tree]
					next_tree = next_tree + 1
					if not tree or run.closed then
						return
					end
					if tree.prunable or not vim.uv.fs_stat(tree.path) then
						complete()
						inspect()
						return
					end
					local remaining = 4
					local function done()
						remaining = remaining - 1
						if remaining == 0 then
							complete()
							inspect()
						end
					end
					git(tree.path, { "status", "--porcelain=v1", "-z", "--untracked-files=all" }, function(status)
						tree.status_error = status.code ~= 0
						tree.changes = status.code == 0 and changes(status.stdout) or nil
						done()
					end)
					git(tree.path, { "log", "-1", "--format=%ct" }, function(commit)
						local timestamp = tonumber(commit.stdout)
						if timestamp then
							tree.activity = math.max(tree.activity or 0, timestamp)
						end
						done()
					end)
					git(tree.path, { "reflog", "-1", "--format=%gD", "--date=unix", "HEAD" }, function(reflog)
						local timestamp = tonumber(reflog.stdout:match("@{(%d+)}"))
						if timestamp then
							tree.activity = math.max(tree.activity or 0, timestamp)
						end
						done()
					end)
					git(tree.path, { "rev-list", "--left-right", "--count", primary.head .. "...HEAD" }, function(diff)
						if diff.code == 0 then
							local behind, ahead = diff.stdout:match("(%d+)%s+(%d+)")
							tree.ahead, tree.behind = tonumber(ahead), tonumber(behind)
						end
						done()
					end)
				end
				-- Bound concurrent inspection to four worktrees; no UI-thread Git waits.
				for _ = 1, math.min(4, #trees) do
					inspect()
				end
			end, {
				prompt = "Worktrees❯ ",
				-- The default hide profile retains stale rows after changing cwd.
				-- Closing on selection lets resume inspect Git and cwd again.
				no_hide = true,
				fzf_colors = true,
				fzf_opts = {
					["--ansi"] = true,
					-- A color base enables ANSI input; role overrides alone may not.
					["--color"] = vim.o.background,
					["--delimiter"] = "\t",
					["--with-nth"] = "2..",
					["--no-sort"] = true,
					["--header"] = "● current · S staged / M unstaged / ? untracked / ! conflicts · ↑↓ vs "
						.. (primary.reference and "reference" or "primary")
						.. "\n"
						.. "  "
						.. column("BRANCH", branch_width)
						.. "  "
						.. column("LOCATION", path_width)
						.. "  "
						.. column("GIT AGE", 7)
						.. "  CHANGES",
				},
				winopts = {
					title = " " .. display(vim.fs.basename(primary.path)) .. " · Worktrees ",
					width = 0.94,
					height = math.min(math.floor(vim.o.lines * 0.85), 36),
					preview = {
						horizontal = "right:45%",
						vertical = "down:60%",
						wrap = true,
						winopts = { number = false, cursorline = false },
					},
				},
				previewer = {
					_ctor = function()
						local previewer = require("fzf-lua.previewer.builtin").buffer_or_file:extend()
						function previewer:parse_entry(entry)
							local tree = resolve(entry)
							if not tree then
								return { content = { "Worktree unavailable" } }
							end
							return {
								path = tree.path,
								filetype = "git",
								do_not_cache = true,
								cmd = {
									"sh",
									"-c",
									preview_command(
										tree,
										primary,
										vim.api.nvim_win_get_height(self.win.preview_winid),
										vim.api.nvim_win_get_width(self.win.preview_winid)
									),
								},
							}
						end
						return previewer
					end,
				},
				actions = {
					["default"] = function(selected)
						local tree = resolve(selected and selected[1])
						if not tree then
							return
						end
						if not vim.uv.fs_stat(tree.path) then
							vim.notify("Worktree is missing: " .. tree.path, vim.log.levels.ERROR)
							return
						end
						local switching = not tree.current
						if switching then
							-- WHY: Prosession wipes buffers even when they contain unsaved edits.
							for _, buffer in ipairs(vim.api.nvim_list_bufs()) do
								if vim.bo[buffer].modified then
									vim.notify("Save unsaved buffers before switching worktrees", vim.log.levels.WARN)
									return
								end
							end
						end
						vim.cmd("cd " .. vim.fn.fnameescape(tree.path))
						if switching then
							vim.cmd("ProsessionReset")
						end
						vim.notify("cwd → " .. tree.path)
					end,
				},
			})
		end)
	end)
end

return M
