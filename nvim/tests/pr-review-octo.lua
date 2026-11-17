-- Run by pr-reviews.lua with the feature omitted and explicitly disabled.
local function workflow()
	vim.o.columns, vim.o.lines = 180, 50
	require("lazy").load({ plugins = { "octo.nvim" } })
	assert(vim.fn.exists(":Octo") == 2 and vim.fn.exists(":PRReviews") == 2)
	assert(vim.fn.exists(":PRReviewCurrent") == 0 and vim.fn.exists(":GHLitePRAddComment") == 0)
	assert(not package.loaded["ghlite"] and not package.loaded["pr-review-ghlite"])
	assert(require("octo.config").values.use_local_fs == false, "Default Octo review enabled local source files")
	assert(vim.fn.maparg(",gP", "n") == "", "Disabled feature retained the ghlite shortcut")
	require("octo.config").values.gh_env = { PR_REVIEW_FIXTURE = vim.env.PR_REVIEW_FIXTURE }
	require("pr-reviews").open({
		id = "PR1",
		number = 1,
		headRefOid = string.rep("a", 40),
		repository = { nameWithOwner = "example/repo" },
	}, "example/repo")
	assert(
		vim.wait(15000, function()
			local buffer = require("octo.utils").get_current_buffer()
			return buffer and buffer.ready and buffer.number == 1 and vim.fn.maparg(",or", "n", false, true).callback
		end, 20),
		"Default review backend did not open the Octo description"
	)
	require("pr-reviews").start()
	assert(
		vim.wait(15000, function()
			local review = require("octo.reviews").get_current_review()
			return review and review.layout.files[1] and review.layout.files[1].right_bufid
		end, 20),
		"Default Octo remote review did not start"
	)
	local review = require("octo.reviews").get_current_review()
	assert(review.layout.files[1].right_lines[1] == "new", "Octo remote diff content missing")
	assert(vim.fn.exists(":PRReviewCheckout") == 2 and vim.fn.exists(":PRReviewCleanup") == 2)
	print("Default Octo startup and remote review passed")
end

local ok, err = xpcall(workflow, debug.traceback)
if not ok then
	io.stderr:write(err .. "\n")
end
vim.cmd(ok and "qa!" or "cquit 1")
