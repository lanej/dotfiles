-- Run: python3 scripts/test-nvim-file-picker.py --check editor
local checkout = vim.fn.getcwd()
local plugins = assert(vim.env.NVIM_TEST_PLUGIN_ROOT)
vim.opt.rtp:prepend(checkout .. "/nvim")
for _, name in ipairs({ "fzf-lua", "nvim-web-devicons" }) do
	vim.opt.rtp:append(plugins .. "/" .. name)
end
vim.g.mapleader = " "
vim.o.columns = 140
vim.o.lines = 40
vim.o.swapfile = false
vim.o.hidden = true
require("fzfconfig")
assert(not package.loaded.snacks, "file selection must not require Snacks")
local root = vim.fn.tempname() .. " with spaces"
vim.fn.mkdir(root, "p")
root = assert(vim.uv.fs_realpath(root))
local function write(path, lines)
	vim.fn.mkdir(vim.fs.dirname(root .. "/" .. path), "p")
	vim.fn.writefile(lines or { "# " .. path }, root .. "/" .. path)
end
write("Makefile")
write("long-directory-name/Makefile")
write("a/b/Makefile")
write("makefile.lower")
write(".hidden/Makefile")
write("ignored/Makefile")
write(".git/Makefile")
write(".ignore", { "ignored/" })
vim.cmd.cd(root)
local function window()
	return require("fzf-lua.utils").fzf_winobj()
end
local function terminal()
	local win = window()
	if not win or not vim.api.nvim_buf_is_valid(win.fzf_bufnr) then
		return ""
	end
	return table.concat(vim.api.nvim_buf_get_lines(win.fzf_bufnr, 0, -1, false), "\n")
end
local function wait(predicate, message)
	assert(vim.wait(vim.env.CI and 30000 or 1000, predicate, 20), message .. "\n" .. terminal())
end
local function send(keys)
	vim.api.nvim_chan_send(vim.b[window().fzf_bufnr].terminal_job_id, keys)
end
local function mapped(keys)
	vim.fn.maparg(" " .. keys, "n", false, true).callback()
	wait(function()
		return terminal():find("Makefile", 1, true) ~= nil
	end, "mapped file picker did not populate")
end
local function close()
	send("\3")
	wait(function()
		return window() == nil
	end, "picker did not close")
end
local function shell_files(query)
	local result = vim.system({
		"zsh",
		"-f",
		"-c",
		'source "$HOME/.files/zsh/zlogin"; eval "$FZF_CTRL_T_COMMAND" | FZF_DEFAULT_OPTS="--scheme=path $FZF_DEFAULT_OPTS $FZF_CTRL_T_OPTS" fzf --filter="$1"',
		"zsh",
		query,
	}, { cwd = root, text = true }):wait()
	assert(result.code == 0, result.stderr)
	return vim.split(vim.trim(result.stdout), "\n", { plain = true })
end
local rows = shell_files("makefile")
assert(rows[1] == "Makefile", vim.inspect(rows))
assert(vim.fn.index(rows, "long-directory-name/Makefile") < vim.fn.index(rows, "a/b/Makefile"), vim.inspect(rows))
assert(vim.tbl_contains(rows, "makefile.lower"), "shell lowercase query must ignore case")
assert(not vim.tbl_contains(shell_files("Makefile"), "makefile.lower"), "shell uppercase query must respect case")
mapped("ff")
send("makefile")
wait(function()
	return terminal():find("makefile.lower", 1, true) ~= nil
end, "lowercase query must ignore case")
local text = terminal()
assert(text:find("long-directory-name/Makefile", 1, true) < text:find("a/b/Makefile", 1, true), text)
send("\21Makefile")
wait(function()
	return not terminal():find("makefile.lower", 1, true)
end, "uppercase query must respect case")
local previous = window()
send("\7")
wait(function()
	return window() ~= previous and terminal():find("ignored/Makefile", 1, true) ~= nil
end, "Ctrl-G did not include ignored files")
assert(terminal():find(".hidden/Makefile", 1, true), terminal())
assert(not terminal():find(".git/Makefile", 1, true), terminal())
previous = window()
send("\27h")
wait(function()
	return window() ~= previous
		and terminal():find("ignored/Makefile", 1, true)
		and not terminal():find(".hidden/Makefile", 1, true)
end, "Alt-H did not preserve ignored-file state while hiding dotfiles")
close()
for _ = 1, 4 do
	vim.cmd.edit(root .. "/a/b/Makefile")
	vim.cmd.enew()
end
require("file-picker").flush(true)
rows = shell_files("Makefile")
assert(rows[1] == "a/b/Makefile", "Ctrl-T did not share editor visits: " .. vim.inspect(rows))
mapped("ff")
send("Makefile")
wait(function()
	local screen = terminal()
	local frequent = screen:find("a/b/Makefile", 1, true)
	local shallow = screen:find("long-directory-name/Makefile", 1, true)
	return frequent and shallow and frequent < shallow
end, "file visits did not improve rank")
send("\21a/b/Makefile")
wait(function()
	return terminal():find("1/4", 1, true)
end, "exact path did not narrow to one file")
send("\r")
wait(function()
	return vim.bo.buftype == "" and vim.api.nvim_buf_get_name(0) == root .. "/a/b/Makefile"
end, "confirm did not open the file")
vim.o.columns = 80
vim.o.lines = 24
mapped("fr")
wait(function()
	return terminal():find("1/1", 1, true)
end, "current-directory picker did not populate")
assert(not terminal():find("long-directory-name", 1, true), terminal())
close()
for _, command in ipairs({
	{ "git", "-C", root, "init", "--quiet" },
	{ "git", "-C", root, "add", "Makefile", "a/b/Makefile", "long-directory-name/Makefile" },
}) do
	local result = vim.system(command):wait()
	assert(result.code == 0, result.stderr)
end
vim.cmd.cd(root .. "/a")
mapped("gf")
wait(function()
	return terminal():find("long-directory-name/Makefile", 1, true)
end, "Git picker lost repository-root scope")
close()
-- The global picker must find a visited file after leaving its project.
vim.cmd.cd(checkout)
mapped("fc")
assert(terminal():find("Makefile", 1, true), "global history lost the visited file")
close()
require("file-picker").flush(true)
vim.fn.delete(root, "rf")
print("file picker: FzfLua, smart case, depth, visits, global history, Ctrl-G, confirm and narrow layout passed")
vim.cmd("qa!")
