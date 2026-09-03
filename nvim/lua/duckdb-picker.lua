-- Dynamic picker for local *.duckdb files, wired into dadbod-grip.nvim.
--
-- NOTE ON PICKER CHOICE: nvim-telescope/telescope.nvim is currently
-- `enabled = false` in init.lua (require("telescope") fails at runtime --
-- verified headlessly), so it cannot back a working keymap right now.
-- ibhagwan/fzf-lua is the fuzzy-finder actually wired up throughout this
-- config (see fzfconfig.lua), so this picker is built on fzf_exec() to match
-- what's really live, following the same prompt/preview/action conventions
-- fzfconfig.lua already uses for its other custom pickers (e.g. <leader>gw,
-- <leader>cf, <leader>sf).
local M = {}

-- Connects `path` as a dadbod-grip DuckDB connection. Shared by the
-- <leader>dd picker's selection action and the BufReadCmd autocmd below, so
-- both entry points go through the same one-line connect path.
--
-- dadbod-grip.nvim owns its own connection persistence (per-project
-- `.grip/connections.json`, promotable to `~/.grip/connections.json`) and
-- its own `:GripConnect duckdb:<path>` command (confirmed syntax from the
-- plugin's README) -- there's no dadbod-ui-style connections.json to
-- read/write/dedup ourselves anymore.
function M.open_file(path)
	vim.cmd("GripConnect duckdb:" .. path)
end

local function find_duckdb_files(root)
	local ok, files = pcall(vim.fn.systemlist, {
		"find",
		root,
		"(",
		"-name",
		".git",
		"-o",
		"-name",
		"node_modules",
		"-o",
		"-name",
		".venv",
		")",
		"-prune",
		"-o",
		"-type",
		"f",
		"-name",
		"*.duckdb",
		"-print",
	})
	if not ok or vim.v.shell_error ~= 0 then
		return {}
	end
	table.sort(files)
	return files
end

function M.pick()
	local cwd = vim.fn.getcwd()
	local files = find_duckdb_files(cwd)

	if #files == 0 then
		vim.notify("No .duckdb files found under " .. cwd, vim.log.levels.WARN)
		return
	end

	require("fzf-lua").fzf_exec(files, {
		prompt = "DuckDB Files❯ ",
		preview = "duckdb -readonly {} -c 'SHOW TABLES;' 2>&1",
		actions = {
			["default"] = function(selected)
				if not selected or #selected == 0 then
					return
				end
				M.open_file(selected[1])
			end,
		},
	})
end

vim.keymap.set("n", "<leader>dd", M.pick, { noremap = true, silent = true, desc = "Pick a .duckdb file and connect via dadbod-grip" })

-- Opening a *.duckdb file directly (`nvim some.duckdb`, `:e some.duckdb`)
-- should land in dadbod-grip's connection UI instead of slurping the binary
-- SQLite-format file into a text buffer. BufReadCmd (not BufReadPost/
-- BufNewFile) is the event that actually intercepts before Neovim's default
-- read behavior runs -- it replaces that behavior entirely rather than
-- firing after the binary garbage has already been loaded into the buffer.
--
-- The placeholder buffer Neovim creates for the pattern match is wiped and
-- replaced by open_file()'s own grip buffers. The wipe + open_file() call
-- are deferred one tick via vim.schedule() so the buffer isn't deleted out
-- from under Neovim while it's still inside this same autocmd's buffer-read
-- codepath.
vim.api.nvim_create_autocmd("BufReadCmd", {
	pattern = "*.duckdb",
	callback = function(args)
		local path = vim.fn.fnamemodify(args.file, ":p")
		local buf = args.buf
		vim.schedule(function()
			if vim.api.nvim_buf_is_valid(buf) then
				vim.cmd("bwipeout! " .. buf)
			end
			M.open_file(path)
		end)
	end,
})

return M
