-- Detached worktrees never switch or clean the user's existing checkout.
local M = {}
local registry_path = vim.fn.stdpath("state") .. "/pr-review-worktrees.json"

local function notify(message, level)
	vim.notify(message, level or vim.log.levels.INFO, { title = "PR review worktrees" })
end

local function git(path, args, callback)
	local cmd = { "git", "-C", path }
	vim.list_extend(cmd, args)
	vim.system(
		cmd,
		{ text = true, timeout = 60000 },
		vim.schedule_wrap(function(result)
			callback(
				result.code == 0 and result.stdout or nil,
				result.code ~= 0
						and (vim.trim(result.stderr or "") ~= "" and vim.trim(result.stderr) or "Git failed or timed out")
					or nil
			)
		end)
	)
end

local function identity(url)
	local repo = url:match("^git@github%.com:(.+)$")
		or url:match("^https://github%.com/(.+)$")
		or url:match("^ssh://git@github%.com/(.+)$")
	return repo and repo:gsub("/$", ""):gsub("%.git$", ""):lower()
end

local function matching_remote(path, repo, callback)
	git(path, { "remote", "-v" }, function(output, err)
		if err then
			callback(nil)
			return
		end
		for remote, url in output:gmatch("([^\n\t ]+)%s+([^\n\t ]+)%s+%(fetch%)") do
			if identity(url) == repo:lower() then
				callback(remote)
				return
			end
		end
		callback(nil)
	end)
end

local function read_registry()
	if vim.fn.filereadable(registry_path) == 0 then
		return {}
	end
	local ok, entries = pcall(vim.json.decode, table.concat(vim.fn.readfile(registry_path), "\n"))
	if not ok or type(entries) ~= "table" then
		notify("Worktree registry is unreadable: " .. registry_path, vim.log.levels.ERROR)
		return nil
	end
	return entries
end

local function record(path, entry)
	local entries = read_registry()
	if not entries then
		return false
	end
	entries[path] = entry
	vim.fn.mkdir(vim.fn.fnamemodify(registry_path, ":h"), "p")
	local temporary = registry_path .. "." .. vim.fn.getpid()
	vim.fn.writefile({ vim.json.encode(entries) }, temporary)
	assert(vim.uv.fs_rename(temporary, registry_path))
	return true
end

local function trees(output)
	local result, current = {}, nil
	for field in output:gmatch("[^%z]+") do
		if field:sub(1, 9) == "worktree " then
			current = { path = field:sub(10) }
			result[#result + 1] = current
		elseif current and field:sub(1, 5) == "HEAD " then
			current.sha = field:sub(6)
		elseif current and field == "detached" then
			current.detached = true
		end
	end
	return result
end

local function open_tab(path, pr)
	vim.cmd.tabnew()
	vim.cmd("tcd " .. vim.fn.fnameescape(path))
	vim.t.pr_review_id = pr.id
	require("fzf-lua").files({ cwd = path })
	notify("Local files: " .. path .. ". Leave feedback in the remote Octo review.")
end

local function create(path, pr, remote)
	git(path, { "worktree", "list", "--porcelain", "-z" }, function(output, err)
		if err then
			notify(err, vim.log.levels.ERROR)
			return
		end
		local listed = trees(output)
		local primary = listed[1] and listed[1].path
		if not primary then
			notify("Cannot identify the primary checkout", vim.log.levels.ERROR)
			return
		end
		local destination = primary .. "/.worktrees/pr-review-" .. pr.number .. "-" .. pr.headRefOid:sub(1, 12)
		git(primary, { "check-ignore", "--quiet", "--", destination }, function(ignored)
			if not ignored then
				notify("Worktree location must be ignored before checkout: " .. destination, vim.log.levels.ERROR)
				return
			end
			for _, tree in ipairs(listed) do
				if tree.path == destination then
					if tree.sha ~= pr.headRefOid or not tree.detached then
						notify(
							"Existing worktree has a different revision or branch: " .. destination,
							vim.log.levels.ERROR
						)
						return
					end
					-- A pre-existing tree can be used but is not adopted for cleanup.
					open_tab(destination, pr)
					return
				end
			end
			if vim.uv.fs_stat(destination) then
				notify("Destination exists but is not a registered worktree: " .. destination, vim.log.levels.ERROR)
				return
			end
			if not read_registry() then
				return
			end
			git(path, { "fetch", "--no-tags", remote, "refs/pull/" .. pr.number .. "/head" }, function(_, fetch_err)
				if fetch_err then
					notify(fetch_err, vim.log.levels.ERROR)
					return
				end
				git(path, { "rev-parse", "FETCH_HEAD" }, function(head, head_err)
					if head_err or vim.trim(head) ~= pr.headRefOid then
						notify(head_err or "PR head changed; refresh the queue before checkout", vim.log.levels.ERROR)
						return
					end
					local branch = "review/pr-" .. pr.number .. "-" .. pr.headRefOid:sub(1, 12)
					local function add()
						git(primary, { "rev-parse", "refs/heads/" .. branch }, function(retained, retention_err)
							if retention_err or vim.trim(retained) ~= pr.headRefOid then
								notify(
									retention_err or "Retention branch has a different revision",
									vim.log.levels.ERROR
								)
								return
							end
							git(
								primary,
								{ "worktree", "add", "--detach", destination, pr.headRefOid },
								function(_, add_err)
									if add_err then
										notify(add_err, vim.log.levels.ERROR)
										return
									end
									record(destination, {
										primary = primary,
										repo = pr.repository.nameWithOwner,
										sha = pr.headRefOid,
										branch = branch,
									})
									open_tab(destination, pr)
								end
							)
						end)
					end
					git(primary, { "show-ref", "--verify", "--quiet", "refs/heads/" .. branch }, function(existing)
						if existing then
							add()
						else
							git(primary, { "branch", "--no-track", branch, pr.headRefOid }, function(_, branch_err)
								if branch_err then
									notify(branch_err, vim.log.levels.ERROR)
								else
									add()
								end
							end)
						end
					end)
				end)
			end)
		end)
	end)
end

local function clones(root)
	local result = {}
	local function scan(path, depth)
		if vim.uv.fs_stat(path .. "/.git") then
			result[#result + 1] = path
			return
		end
		if depth == 0 then
			return
		end
		local iterator = vim.uv.fs_scandir(path)
		if iterator then
			while true do
				local name, kind = vim.uv.fs_scandir_next(iterator)
				if not name then
					break
				end
				if kind == "directory" and name:sub(1, 1) ~= "." and name ~= "node_modules" then
					scan(path .. "/" .. name, depth - 1)
				end
			end
		end
	end
	scan(root, 3)
	return result
end

function M.checkout(pr, clone_path)
	if clone_path then
		local path = vim.uv.fs_realpath(vim.fn.expand(clone_path))
		if not path then
			notify("Clone path does not exist", vim.log.levels.ERROR)
			return
		end
		matching_remote(path, pr.repository.nameWithOwner, function(remote)
			if remote then
				create(path, pr, remote)
			else
				notify(
					"Clone has no matching github.com remote for " .. pr.repository.nameWithOwner,
					vim.log.levels.ERROR
				)
			end
		end)
		return
	end
	local candidates, matches = clones(vim.fn.expand("~/src")), {}
	local function choose()
		local function check(path)
			path = vim.uv.fs_realpath(vim.fn.expand(path))
			if not path then
				notify("Clone path does not exist", vim.log.levels.ERROR)
				return
			end
			matching_remote(path, pr.repository.nameWithOwner, function(remote)
				if remote then
					create(path, pr, remote)
				else
					notify(
						"Clone has no matching github.com remote for " .. pr.repository.nameWithOwner,
						vim.log.levels.ERROR
					)
				end
			end)
		end
		if #matches == 0 then
			vim.ui.input(
				{ prompt = "Clone path for " .. pr.repository.nameWithOwner .. ": ", completion = "dir" },
				function(path)
					if path and path ~= "" then
						check(path)
					end
				end
			)
		elseif #matches == 1 then
			check(matches[1])
		else
			vim.ui.select(matches, { prompt = "Choose clone" }, function(path)
				if path then
					check(path)
				end
			end)
		end
	end
	local function inspect(index)
		if not candidates[index] then
			choose()
			return
		end
		matching_remote(candidates[index], pr.repository.nameWithOwner, function(remote)
			if remote then
				matches[#matches + 1] = candidates[index]
			end
			inspect(index + 1)
		end)
	end
	inspect(1)
end

local function inside(path, directory)
	path = vim.uv.fs_realpath(path) or path
	directory = vim.uv.fs_realpath(directory) or directory
	return path == directory or path:sub(1, #directory + 1) == directory .. "/"
end

local function active(path)
	for _, tab in ipairs(vim.api.nvim_list_tabpages()) do
		if inside(vim.fn.getcwd(-1, vim.api.nvim_tabpage_get_number(tab)), path) then
			return "active tab " .. vim.api.nvim_tabpage_get_number(tab) .. " working directory"
		end
	end
	for _, buffer in ipairs(vim.api.nvim_list_bufs()) do
		if
			vim.api.nvim_buf_is_loaded(buffer)
			and inside(vim.api.nvim_buf_get_name(buffer), path)
			and (
				vim.bo[buffer].buftype == ""
				or (vim.bo[buffer].modified and vim.bo[buffer].bufhidden ~= "wipe")
				or #vim.fn.win_findbuf(buffer) > 0
			)
		then
			return "loaded buffer " .. vim.api.nvim_buf_get_name(buffer)
		end
	end
	return false
end

function M.cleanup()
	local entries = read_registry()
	if not entries then
		return
	end
	local paths = vim.tbl_keys(entries)
	table.sort(paths)
	if #paths == 0 then
		notify("No owned PR review worktrees")
		return
	end
	vim.ui.select(paths, { prompt = "Clean up PR review worktree" }, function(path)
		if not path then
			return
		end
		local entry = entries[path]
		local function retained(reason)
			notify("Retained " .. path .. ": " .. reason, vim.log.levels.WARN)
		end
		local use = active(path)
		if use then
			retained(use)
			return
		end
		git(entry.primary, { "worktree", "list", "--porcelain", "-z" }, function(output, err)
			if err then
				retained(err)
				return
			end
			local found
			for _, tree in ipairs(trees(output)) do
				if tree.path == path and tree.detached and tree.sha == entry.sha then
					found = true
				end
			end
			if not found then
				retained("registration, revision or detached state changed")
				return
			end
			if not entry.branch then
				retained("no named retention branch recorded")
				return
			end
			git(entry.primary, { "rev-parse", "refs/heads/" .. entry.branch }, function(sha, retention_err)
				if retention_err or vim.trim(sha) ~= entry.sha then
					retained(retention_err or "retention branch changed")
					return
				end
				matching_remote(path, entry.repo, function(remote)
					if not remote then
						retained("repository identity changed")
						return
					end
					git(path, { "status", "--short", "--untracked-files=all" }, function(status, status_err)
						if status_err or status ~= "" then
							retained(status_err or "uncommitted work")
							return
						end
						git(
							path,
							{ "ls-files", "--others", "--ignored", "--exclude-standard" },
							function(ignored, ignored_err)
								if ignored_err or ignored ~= "" then
									retained(ignored_err or "ignored artifacts")
									return
								end
								if vim.fn.executable("lsof") ~= 1 then
									retained("lsof unavailable; cannot check active processes")
									return
								end
								vim.system(
									{ "lsof", "-n", "+D", path, "-Fpn" },
									{ text = true, timeout = 10000 },
									vim.schedule_wrap(function(result)
										if
											result.stdout ~= ""
											or result.code > 1
											or vim.trim(result.stderr or "") ~= ""
										then
											retained("active process or incomplete process inspection")
											return
										end
										local current_use = active(path)
										if current_use then
											retained(current_use)
											return
										end
										-- Git protects ordinary dirt on removal, but ignored artifacts
										-- may have appeared while the process inspection was running.
										git(
											path,
											{ "ls-files", "--others", "--ignored", "--exclude-standard" },
											function(latest, latest_err)
												if latest_err or latest ~= "" then
													retained(latest_err or "ignored artifacts")
													return
												end
												local final_use = active(path)
												if final_use then
													retained(final_use)
													return
												end
												git(
													entry.primary,
													{ "worktree", "remove", path },
													function(_, remove_err)
														if remove_err then
															retained(remove_err)
															return
														end
														git(
															entry.primary,
															{ "worktree", "list", "--porcelain", "-z" },
															function(after, verify_err)
																if verify_err or vim.uv.fs_stat(path) then
																	retained(
																		verify_err or "removal could not be confirmed"
																	)
																	return
																end
																for _, tree in ipairs(trees(after)) do
																	if tree.path == path then
																		retained("worktree registration remains")
																		return
																	end
																end
																record(path, nil)
																notify("Removed " .. path)
															end
														)
													end
												)
											end
										)
									end)
								)
							end
						)
					end)
				end)
			end)
		end)
	end)
end

return M
