local M = {}

function M.fields(task)
	return {
		title = task.title,
		description = task.description or "",
		acceptance_criteria = task.acceptance_criteria or "",
	}
end

function M.same(left, right)
	return vim.deep_equal(M.fields(left), M.fields(right))
end

function M.token()
	return vim.fn.sha256(tostring(vim.uv.hrtime()) .. vim.fn.getpid() .. tostring({})):sub(1, 24)
end

local acceptance_heading = "## Acceptance criteria"

local function has_heading(marker)
	return marker:find("<!-- beads:acceptance:v2:", 1, true) == 1
end

function M.render(fields, marker)
	-- A per-document boundary leaves existing headings and fenced examples untouched.
	return vim.split(
		"# "
			.. fields.title
			.. "\n"
			.. fields.description
			.. "\n"
			.. marker
			.. "\n"
			.. (has_heading(marker) and acceptance_heading .. "\n" or "")
			.. fields.acceptance_criteria,
		"\n",
		{ plain = true }
	)
end

function M.parse(lines, marker)
	local title = (lines[1] or ""):match("^# (.+)$")
	assert(
		title and title:find("%S") and #title <= 255 and not title:find("[%c]"),
		"Use one nonempty '# Title' (at most 255 bytes)"
	)
	local boundary
	for index = 2, #lines do
		if lines[index] == marker then
			assert(not boundary, "The acceptance boundary occurs more than once")
			boundary = index
		end
	end
	assert(boundary, "Restore the document's acceptance boundary before saving")
	local acceptance_start = boundary + 1
	if has_heading(marker) then
		assert(
			lines[acceptance_start] == acceptance_heading,
			"Restore the Acceptance criteria heading below the managed boundary"
		)
		acceptance_start = acceptance_start + 1
	end
	return {
		title = title,
		description = table.concat(lines, "\n", 2, boundary - 1),
		acceptance_criteria = table.concat(lines, "\n", acceptance_start),
	}
end

return M
