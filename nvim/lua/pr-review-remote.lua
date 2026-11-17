-- Checkout creation and inline feedback must agree on the repository's fetch remote.
local M = {}

function M.identity(url)
	local repo = url:match("^git@github%.com:(.+)$")
		or url:match("^https://github%.com/(.+)$")
		or url:match("^https://github%.com:443/(.+)$")
		or url:match("^ssh://git@github%.com/(.+)$")
	return repo and repo:gsub("/$", ""):gsub("%.git$", ""):lower()
end

function M.matching(output, repo)
	for remote, url in output:gmatch("([^\n\t ]+)%s+([^\n\t ]+)%s+%(fetch%)") do
		if M.identity(url) == repo:lower() then
			return remote
		end
	end
end

return M
