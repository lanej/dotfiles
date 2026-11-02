local M = {}

function M.setup()
	local executable
	for _, candidate in ipairs({
		"ctags",
		"universal-ctags",
		"uctags",
		"/opt/homebrew/bin/ctags",
		"/usr/local/bin/ctags",
	}) do
		local path = vim.fn.exepath(candidate)
		if path ~= "" then
			local version = vim.system({ path, "--version" }, { text = true }):wait()
			if version.code == 0 and (version.stdout or ""):find("Universal Ctags", 1, true) then
				executable = path
				break
			end
		end
	end
	if not executable then
		vim.g.gutentags_enabled = 0
		vim.schedule(function()
			vim.notify("Project tags need Universal Ctags; LSP and text search remain available", vim.log.levels.WARN)
		end)
		return
	end
	vim.g.gutentags_modules = { "ctags" }
	vim.g.gutentags_ctags_executable = executable
	vim.g.gutentags_cache_dir = vim.fn.stdpath("cache") .. "/gutentags"
	vim.g.gutentags_add_default_project_roots = 0
	vim.g.gutentags_project_root = { ".git" }
	vim.g.gutentags_exclude_filetypes = { "gitcommit", "gitrebase", "norg" }
	vim.g.gutentags_generate_on_missing = 1
	vim.g.gutentags_generate_on_new = 1
	vim.g.gutentags_generate_on_write = 1
	vim.g.gutentags_background_update = 1
	vim.g.gutentags_file_list_command = {
		markers = { [".git"] = "git -c core.quotepath=false ls-files --cached --others --exclude-standard" },
	}
	vim.g.gutentags_ctags_exclude = {
		".git",
		"node_modules",
		".venv",
		"venv",
		".mypy_cache",
		".pytest_cache",
		"__pycache__",
		"target",
		"build",
		"dist",
		"bazel-*",
		"tags",
		"tags.temp",
	}
end

return M
