local B = {}
local github = require("pr-review-github")

function B.open(session)
	local pr = session.pr
	require("pr-review-ghlite").open(session, function()
		vim.t.pr_review_id = pr.id
		if
			require("pr-review-ghlite").checked_out()
			and vim.bo.buftype == ""
			and vim.api.nvim_buf_get_name(0) ~= ""
		then
			require("ghlite.comments").load_comments()
		else
			-- ghlite reuses description buffers by PR number across repositories.
			for _, bufnr in ipairs(vim.api.nvim_list_bufs()) do
				if vim.api.nvim_buf_get_name(bufnr):match("PR View: " .. pr.number .. "$") then
					vim.b[bufnr].pr_review_id = pr.id
				end
			end
			require("ghlite.pr_commands").load_pr_view()
		end
	end)
end

function B.install(M, find_session, notify)
	local function context()
		local id = vim.b.pr_review_id or vim.t.pr_review_id
		return id and find_session(id) or require("pr-review-ghlite").current()
	end

	function M.review_current()
		github.repository(vim.fn.getcwd(), function(repo, err)
			if not repo then
				notify(err, vim.log.levels.WARN)
				return
			end
			vim.system(
				{ "gh", "pr", "view", "--json", "id,number,headRefOid,url" },
				{ text = true, timeout = 15000, env = { GH_REPO = repo, GH_HOST = "github.com" } },
				vim.schedule_wrap(function(result)
					local ok, pr = pcall(vim.json.decode, result.stdout or "")
					if result.code ~= 0 or not ok or type(pr) ~= "table" or not pr.id then
						notify(
							"Could not find this branch's PR: " .. vim.trim(result.stderr or ""),
							vim.log.levels.WARN
						)
						return
					end
					pr.repository = { nameWithOwner = repo }
					M.open(pr, repo)
				end)
			)
		end)
	end

	function M.start()
		local session = context()
		if
			session
			and require("pr-review-ghlite").select(session)
			and require("pr-review-ghlite").require_checkout()
		then
			require("ghlite.pr_commands").start_review("github")
		end
	end

	function M.checkout(opts)
		local session = context()
		if session then
			if session.loading then
				notify("Wait for the selected PR revision to load before checkout", vim.log.levels.WARN)
				return
			end
			require("pr-review-checkout").checkout(session.pr, opts and opts.args ~= "" and opts.args or nil)
		end
	end

	function M.local_files(pr, path)
		local session = find_session(pr.id)
		if not session or not require("pr-review-ghlite").select(session) then
			return
		end
		session.root = path
		vim.cmd("tcd " .. vim.fn.fnameescape(path))
		vim.t.pr_review_id = pr.id
		require("ghlite.comments").load_comments()
		require("fzf-lua").files({ cwd = path })
	end

	local function attach(bufnr)
		if bufnr ~= vim.api.nvim_get_current_buf() then
			return
		end
		local session = context()
		if not session or session.loading then
			return
		end
		if not require("pr-review-ghlite").select(session) then
			return
		end
		local name = vim.api.nvim_buf_get_name(bufnr)
		local source = vim.bo[bufnr].buftype == ""
			and name ~= ""
			and require("pr-review-ghlite").checked_out()
			and session.root
			and name:sub(1, #session.root + 1) == session.root .. "/"
		local review_buffer = vim.bo[bufnr].buftype == "nofile"
			and (name:find("PR View:", 1, true) or name:find("PR comment", 1, true) or name:find("PR reply", 1, true))
		if not source and not review_buffer then
			return
		end
		vim.b[bufnr].pr_review_id = session.pr.id
		local function command(cmd)
			return function()
				if require("pr-review-ghlite").select(session) then
					vim.cmd(cmd)
				end
			end
		end
		local function comment(opts)
			if
				not require("pr-review-ghlite").select(session) or not require("pr-review-ghlite").require_checkout()
			then
				return
			end
			local comments = require("ghlite.comments")
			local task = require("ghlite.pr_commands").start_review("github")
			task:on_complete(function(err)
				vim.schedule(function()
					if not err and require("ghlite.state").pending_reviews[session.pr.number] then
						comments.comment_on_line(opts)
					end
				end)
			end)
		end
		local bindings = {
			["<leader>or"] = { M.start, "Start/resume review" },
			["<leader>oc"] = { source and comment or command("GHLitePRAddPRComment"), "Add comment or reply" },
			["<leader>of"] = {
				function()
					if require("pr-review-ghlite").require_checkout() then
						require("fzf-lua").files()
					end
				end,
				"PR files",
			},
			["<leader>ov"] = { command("GHLitePRToggleFileViewed"), "Toggle file viewed" },
			["<leader>op"] = {
				function()
					if require("pr-review-ghlite").require_checkout() then
						vim.cmd("GHLitePRLoadComments")
						vim.cmd("copen")
					end
				end,
				"Review comments (including pending)",
			},
			["<leader>os"] = { command("GHLitePRSubmitReview github"), "Submit review" },
			["<leader>oa"] = { command("GHLitePRApprove"), "Approve review" },
			["<leader>ox"] = { command("GHLitePRRequestChanges"), "Request changes" },
			["<leader>oq"] = {
				function()
					M.pick({ scope = session.scope or "all" })
				end,
				"Return to review queue",
			},
			["<leader>ol"] = { M.checkout, "Local PR worktree" },
			["<leader>ob"] = {
				function()
					vim.ui.open(
						session.pr.url
							or (
								"https://github.com/"
								.. session.pr.repository.nameWithOwner
								.. "/pull/"
								.. session.pr.number
							)
					)
				end,
				"Open PR in browser",
			},
			["<leader>ot"] = { command("GHLitePRResolveComment"), "Resolve thread" },
			["<leader>oT"] = { command("GHLitePRUnresolveComment"), "Reopen thread" },
			["<leader>oh"] = {
				function()
					vim.diagnostic.open_float({ scope = "line", source = true })
				end,
				"Read review thread",
			},
		}
		for key, binding in pairs(bindings) do
			vim.keymap.set("n", key, binding[1], { buffer = bufnr, desc = binding[2] })
		end
		for alias, key in pairs({ rs = "or", rp = "op", rv = "os", rq = "oq", rl = "ol" }) do
			local binding = bindings["<leader>" .. key]
			vim.keymap.set("n", "<leader>" .. alias, binding[1], { buffer = bufnr, desc = binding[2] })
		end
		local function menu()
			require("which-key").show({ keys = vim.g.mapleader .. "o" })
		end
		vim.keymap.set("n", "<leader>o", menu, { buffer = bufnr, desc = "PR review actions" })
		if source then
			vim.keymap.set("x", "<leader>oc", function()
				local first, last = vim.fn.line("v"), vim.fn.line(".")
				vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes("<Esc>", true, false, true), "nx", false)
				comment({ line1 = math.min(first, last), line2 = math.max(first, last) })
			end, { buffer = bufnr, desc = "Comment on selected lines" })
			vim.keymap.set("x", "<leader>o", menu, { buffer = bufnr, desc = "PR review actions" })
		end
	end

	function M.setup()
		vim.api.nvim_create_user_command("PRReviews", M.pick, { bang = true })
		vim.api.nvim_create_user_command("PRReviewsAll", M.all, { bang = true })
		vim.api.nvim_create_user_command("PRReviewCurrent", M.review_current, {})
		vim.api.nvim_create_user_command("PRReviewCheckout", M.checkout, { nargs = "?", complete = "dir" })
		vim.api.nvim_create_user_command("PRReviewCleanup", function()
			require("pr-review-checkout").cleanup()
		end, {})
		vim.keymap.set("n", "<leader>gR", M.pick, { desc = "PR review requests" })
		vim.keymap.set("n", "<leader>gP", M.review_current, { desc = "Review current PR inline" })
		vim.api.nvim_create_autocmd({ "BufEnter", "FileType" }, {
			group = vim.api.nvim_create_augroup("PRReviewQueue", { clear = true }),
			callback = function(ev)
				vim.schedule(function()
					attach(ev.buf)
				end)
			end,
		})
		vim.api.nvim_create_autocmd("User", {
			pattern = "PRReviewUpdated",
			group = vim.api.nvim_create_augroup("PRReviewUpdates", { clear = true }),
			callback = function()
				attach(vim.api.nvim_get_current_buf())
			end,
		})
	end
end

return B
