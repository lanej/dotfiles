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

function M.render(fields, marker)
	-- A per-document boundary leaves existing headings and fenced examples untouched.
	return vim.split(
		"# " .. fields.title .. "\n" .. fields.description .. "\n" .. marker .. "\n" .. fields.acceptance_criteria,
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
	return {
		title = title,
		description = table.concat(lines, "\n", 2, boundary - 1),
		acceptance_criteria = table.concat(lines, "\n", boundary + 1),
	}
end

return M
