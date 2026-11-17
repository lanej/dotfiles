local B = {}

function B.open(session, notify)
	local pr = session.pr
	if require("octo.reviews").get_current_review() or vim.bo.modified then
		vim.cmd.tabnew()
	end
	-- Octo owns description, discussion, diff navigation, comments and suggestions.
	-- Opening the description does not create a pending review.
	require("octo.utils").get_pull_request(pr.number, pr.repository.nameWithOwner)
	local buffer = require("octo.utils").get_current_buffer()
	if buffer and buffer.ready and buffer:isPullRequest() then
		buffer:update_metadata()
		-- Octo can mark rendered UI text modified. Its editable-region metadata
		-- identifies actual title, description and discussion edits.
		local dirty = buffer.titleMetadata.dirty or buffer.bodyMetadata.dirty
		for _, comment in ipairs(buffer.commentsMetadata) do
			dirty = dirty or comment.dirty
		end
		if dirty then
			session.loading = "blocked"
			notify(
				"Save the description's edits before reloading it; existing feedback is retained.",
				vim.log.levels.WARN
			)
		else
			buffer.ready = false
			require("octo").load_buffer({ bufnr = buffer.bufnr })
		end
	end
end

function B.install(M, find_session, notify)
	local function context()
		local buffer = require("octo.utils").get_current_buffer()
		if buffer and buffer:isPullRequest() then
			return find_session(buffer.node.id)
		end
		local review = require("octo.reviews").get_current_review()
		if review and find_session(review.pull_request.id) then
			return find_session(review.pull_request.id), review
		end
		local id = vim.t.pr_review_id
		return id and find_session(id) or nil
	end

	local function pending_review(session, review)
		if review and review.id ~= -1 and review.pull_request.id == session.pr.id then
			return review
		end
		for _, candidate in pairs(require("octo.reviews").reviews) do
			if
				candidate.id ~= -1
				and candidate.pull_request.id == session.pr.id
				and candidate.layout
				and vim.api.nvim_tabpage_is_valid(candidate.layout.tabpage)
			then
				return candidate
			end
		end
	end

	-- These shortcuts only navigate to the pending review. Octo owns the
	-- review UI, summary buffer, submission and failure handling.
	local function review_command(command)
		local session, active_review = context()
		local review = session and pending_review(session, active_review)
		if review then
			vim.api.nvim_set_current_tabpage(review.layout.tabpage)
		end
		vim.cmd(command)
	end

	function M.start()
		local session, active_review = context()
		if not session then
			return
		end
		local review = pending_review(session, active_review)
		if review then
			vim.api.nvim_set_current_tabpage(review.layout.tabpage)
		else
			local current = require("octo.utils").get_current_buffer()
			if not current or not current:isPullRequest() or current.node.id ~= session.pr.id then
				local description
				for bufnr, buffer in pairs(_G.octo_buffers) do
					if
						vim.api.nvim_buf_is_loaded(bufnr)
						and buffer:isPullRequest()
						and buffer.node.id == session.pr.id
						and buffer.ready
					then
						description = bufnr
						break
					end
				end
				if not description then
					M.open(session.pr, session.scope)
					notify("Start or resume from the loaded Octo description (,rs)")
					return
				end
				local window
				for _, win in ipairs(vim.api.nvim_list_wins()) do
					if vim.api.nvim_win_get_buf(win) == description then
						window = win
						break
					end
				end
				if window then
					vim.api.nvim_set_current_win(window)
				else
					vim.cmd.tabnew()
					vim.api.nvim_set_current_buf(description)
				end
			end
			local selected = require("octo.utils").get_current_buffer()
			if selected and selected.ready and session.loading == true then
				session.pr.headRefOid, session.loading = selected.node.headRefOid, false
			end
			if
				session.loading == "blocked"
				or not selected
				or not selected.ready
				or selected.node.headRefOid ~= session.pr.headRefOid
			then
				notify(
					"Wait for the selected PR revision to load, or save edits and refresh its description before starting",
					vim.log.levels.WARN
				)
				return
			end
			vim.cmd("Octo review")
		end
	end

	function M.checkout(opts)
		local session, review = context()
		if session then
			local pr = vim.deepcopy(session.pr)
			local buffer = require("octo.utils").get_current_buffer()
			pr.headRefOid = review and review.pull_request.right.commit
				or (buffer and buffer:isPullRequest() and buffer.node.headRefOid)
				or pr.headRefOid
			require("pr-review-checkout").checkout(pr, opts and opts.args ~= "" and opts.args or nil)
		end
	end

	M.octo_mappings = {
		pull_request = {
			review = { lhs = "<leader>or", desc = "Start/resume review" },
			add_comment = { lhs = "<leader>oc", desc = "Add comment" },
			list_changed_files = { lhs = "<leader>of", desc = "Changed files" },
			open_in_browser = { lhs = "<leader>ob", desc = "Open PR in browser" },
			resolve_thread = { lhs = "<leader>ot", desc = "Resolve thread" },
			unresolve_thread = { lhs = "<leader>oT", desc = "Reopen thread" },
		},
		review_thread = {
			add_reply = { lhs = "<leader>oc", desc = "Reply to thread" },
			add_suggestion = { lhs = "<leader>oS", desc = "Add suggestion" },
			resolve_thread = { lhs = "<leader>ot", desc = "Resolve thread" },
			unresolve_thread = { lhs = "<leader>oT", desc = "Reopen thread" },
		},
		review_diff = {
			submit_review = { lhs = "<leader>os", desc = "Submit review" },
			add_review_comment = { lhs = "<leader>oc", desc = "Add inline comment", mode = { "n", "x" } },
			add_review_suggestion = { lhs = "<leader>oS", desc = "Add suggestion", mode = { "n", "x" } },
			toggle_files = { lhs = "<leader>of", desc = "Toggle changed files" },
			toggle_viewed = { lhs = "<leader>ov", desc = "Toggle file viewed" },
		},
		file_panel = {
			submit_review = { lhs = "<leader>os", desc = "Submit review" },
			toggle_files = { lhs = "<leader>of", desc = "Toggle changed files" },
			toggle_viewed = { lhs = "<leader>ov", desc = "Toggle file viewed" },
		},
	}

	local function attach(bufnr)
		if bufnr ~= vim.api.nvim_get_current_buf() then
			return
		end
		local session = context()
		local comment = vim.fn.maparg("<leader>oc", "n", false, true)
		local submit = vim.fn.maparg("<leader>os", "n", false, true)
		local native = require("octo.mappings")
		local summary = vim.fn.maparg("<C-a>", "n", false, true).callback == native.approve_review
		local octo_context = comment.buffer == 1 or submit.buffer == 1 or summary
		if octo_context then
			-- Treesitter keeps <leader>o outside Octo's description/review buffers.
			local function show_actions()
				require("which-key").show({ keys = vim.g.mapleader .. "o" })
			end
			vim.keymap.set("n", "<leader>o", show_actions, { buffer = bufnr, desc = "Octo review actions" })
			if vim.fn.maparg("<leader>oc", "x", false, true).buffer == 1 then
				vim.keymap.set("x", "<leader>o", show_actions, { buffer = bufnr, desc = "Octo review actions" })
			end
		end
		local aliases = {
			["<leader>rs"] = "<leader>or",
			["<leader>rp"] = "<leader>op",
			["<leader>rv"] = "<leader>os",
			["<leader>rq"] = "<leader>oq",
			["<leader>rl"] = "<leader>ol",
		}
		for key, binding in
			pairs(session and {
				["<leader>rs"] = { M.start, "Start/resume PR review" },
				["<leader>rp"] = {
					function()
						review_command("Octo review comments")
					end,
					"Pending PR comments",
				},
				["<leader>rv"] = {
					function()
						review_command("Octo review submit")
					end,
					"Submit PR review",
				},
				["<leader>rq"] = {
					function()
						M.pick({ scope = session.scope or "all" })
					end,
					"Return to PR review queue",
				},
				["<leader>rl"] = { M.checkout, "Local PR worktree" },
			} or {})
		do
			vim.keymap.set("n", key, binding[1], { buffer = bufnr, desc = binding[2] })
			if octo_context then
				vim.keymap.set("n", aliases[key], binding[1], { buffer = bufnr, desc = binding[2] })
			end
		end
		if summary then
			vim.keymap.set("n", "<leader>oa", native.approve_review, { buffer = bufnr, desc = "Approve review" })
			vim.keymap.set("n", "<leader>oc", native.comment_review, { buffer = bufnr, desc = "Submit comment review" })
			vim.keymap.set("n", "<leader>or", native.request_changes, { buffer = bufnr, desc = "Request changes" })
		end
	end

	function M.setup()
		vim.api.nvim_create_user_command("PRReviews", M.pick, { bang = true })
		vim.api.nvim_create_user_command("PRReviewsAll", M.all, { bang = true })
		vim.api.nvim_create_user_command("PRReviewCheckout", M.checkout, { nargs = "?", complete = "dir" })
		vim.api.nvim_create_user_command("PRReviewCleanup", function()
			require("pr-review-checkout").cleanup()
		end, {})
		vim.keymap.set("n", "<leader>gR", M.pick, { desc = "PR review requests" })
		vim.api.nvim_create_autocmd({ "BufEnter", "FileType" }, {
			group = vim.api.nvim_create_augroup("PRReviewQueue", { clear = true }),
			callback = function(ev)
				vim.schedule(function()
					attach(ev.buf)
				end)
			end,
		})
	end
end

return B
