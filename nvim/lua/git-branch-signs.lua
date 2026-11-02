-- Branch changes are a dim layer beneath Gitsigns' index-to-buffer signs.
local M = {}
local ns = vim.api.nvim_create_namespace("git-branch-signs")
local generations = {}
local baselines = {}
local enabled = true

function M.refresh(buf)
	generations[buf] = (generations[buf] or 0) + 1
	local generation = generations[buf]
	local function current()
		return enabled and vim.api.nvim_buf_is_loaded(buf) and generations[buf] == generation
	end
	if not vim.api.nvim_buf_is_loaded(buf) then
		return
	end
	local status = vim.b[buf].gitsigns_status_dict
	if not enabled or not status or not status.root then
		vim.api.nvim_buf_clear_namespace(buf, ns, 0, -1)
		return
	end
	local root = status.root
	local file = vim.api.nvim_buf_get_name(buf)
	local relative = file:sub(#root + 2)
	local function git(args, callback)
		vim.system(
			vim.list_extend({ "git", "-C", root }, args),
			{},
			vim.schedule_wrap(function(result)
				if current() then
					callback(result)
				end
			end)
		)
	end
	vim.defer_fn(function()
		if not current() then
			return
		end
		git({ "merge-base", "HEAD", "origin/HEAD" }, function(base)
			if base.code ~= 0 then
				vim.api.nvim_buf_clear_namespace(buf, ns, 0, -1)
				return -- No default-branch ref: retain normal unstaged/staged signs.
			end
			local key = root .. ":" .. vim.trim(base.stdout) .. ":" .. relative
			if baselines[buf] and baselines[buf].key == key then
				M.render(buf, baselines[buf].text)
				return
			end
			git({ "show", vim.trim(base.stdout) .. ":" .. relative }, function(result)
				-- A newly added branch file has no contents at the merge base.
				if result.code ~= 0 then
					git({ "ls-tree", vim.trim(base.stdout), "--", relative }, function(tree)
						if tree.code == 0 and tree.stdout == "" then
							baselines[buf] = { key = key, text = "" }
							M.render(buf, "")
						else
							vim.api.nvim_buf_clear_namespace(buf, ns, 0, -1)
						end
					end)
				else
					baselines[buf] = { key = key, text = result.stdout }
					M.render(buf, result.stdout)
				end
			end)
		end)
	end, 100)
end

function M.render(buf, baseline)
	local encoding = vim.bo[buf].fileencoding
	if encoding ~= "" and encoding ~= "utf-8" then
		baseline = vim.iconv(baseline, encoding, "utf-8")
	end
	if vim.bo[buf].fileformat == "dos" then
		baseline = baseline:gsub("\r\n", "\n")
	elseif vim.bo[buf].fileformat == "mac" then
		baseline = baseline:gsub("\r", "\n")
	end
	local lines = vim.api.nvim_buf_get_lines(buf, 0, -1, false)
	local text = table.concat(lines, "\n") .. (vim.bo[buf].endofline and "\n" or "")
	if vim.bo[buf].bomb then
		text = "\239\187\191" .. text
	end
	local hunks = vim.diff(baseline, text, { result_type = "indices", algorithm = "histogram" })
	vim.api.nvim_buf_clear_namespace(buf, ns, 0, -1)
	for _, hunk in ipairs(hunks) do
		local _, removed, start, added = unpack(hunk)
		local kind = removed == 0 and "Add" or (added == 0 and "Delete" or "Change")
		local first = added == 0 and math.max(start, 1) or start
		local last = added == 0 and first or start + added - 1
		for line = first, math.min(last, #lines) do
			vim.api.nvim_buf_set_extmark(buf, ns, line - 1, 0, {
				sign_text = kind == "Delete" and (start == 0 and "^" or "_") or "│",
				sign_hl_group = "GitSignsStaged" .. kind,
				priority = 5,
			})
		end
	end
end

function M.enable(value)
	enabled = value
	for _, buf in ipairs(vim.api.nvim_list_bufs()) do
		M.refresh(buf)
	end
end

function M.navigate(direction)
	if vim.wo.diff then
		vim.cmd.normal({ args = { vim.v.count1 .. (direction == "next" and "]c" or "[c") }, bang = true })
		return
	end
	local buf = vim.api.nvim_get_current_buf()
	local changed = {}
	-- Gitsigns renders signs only in the viewport. Its complete staged hunk
	-- inventory is internal in the pinned version; get_hunks() exposes unstaged.
	local cache = require("gitsigns.cache").cache[buf]
	local pending = require("gitsigns").get_hunks(buf) or {}
	vim.list_extend(pending, cache and cache.hunks_staged or {})
	for _, hunk in ipairs(pending) do
		local first = math.max(hunk.added.start, 1)
		local last = math.max(hunk.added.start + math.max(hunk.added.count, 1) - 1, first)
		for line = first, last do
			changed[line] = true
		end
	end
	for _, mark in ipairs(vim.api.nvim_buf_get_extmarks(buf, ns, 0, -1, {})) do
		changed[mark[2] + 1] = true
	end
	local lines = vim.tbl_keys(changed)
	table.sort(lines)
	local hunks = {}
	for _, line in ipairs(lines) do
		local last = hunks[#hunks]
		if last and line == last.finish + 1 then
			last.finish = line
		else
			hunks[#hunks + 1] = { start = line, finish = line }
		end
	end
	if #hunks == 0 then
		return
	end
	local line = vim.api.nvim_win_get_cursor(0)[1]
	for _ = 1, vim.v.count1 do
		local target
		if direction == "next" then
			for _, hunk in ipairs(hunks) do
				if hunk.start > line then
					target = hunk.start
					break
				end
			end
			target = target or (vim.o.wrapscan and hunks[1].start)
		else
			for i = #hunks, 1, -1 do
				if hunks[i].finish < line then
					target = hunks[i].start
					break
				end
			end
			target = target or (vim.o.wrapscan and hunks[#hunks].start)
		end
		if not target then
			break
		end
		line = target
	end
	vim.cmd("normal! m'")
	vim.api.nvim_win_set_cursor(0, { line, 0 })
	if vim.o.foldopen:match("search") then
		vim.cmd("normal! zv")
	end
end

function M.setup()
	local group = vim.api.nvim_create_augroup("GitBranchSigns", { clear = true })
	vim.api.nvim_create_autocmd({ "BufEnter", "BufWritePost", "TextChanged", "TextChangedI", "FocusGained" }, {
		group = group,
		callback = function(event)
			M.refresh(event.buf)
		end,
	})
	vim.api.nvim_create_autocmd("User", {
		group = group,
		pattern = "GitSignsUpdate",
		callback = function(event)
			if event.data and event.data.buffer then
				M.refresh(event.data.buffer)
			else
				for _, buf in ipairs(vim.api.nvim_list_bufs()) do
					M.refresh(buf)
				end
			end
		end,
	})
	vim.api.nvim_create_autocmd("BufWipeout", {
		group = group,
		callback = function(event)
			generations[event.buf] = nil
			baselines[event.buf] = nil
		end,
	})
end

return M
