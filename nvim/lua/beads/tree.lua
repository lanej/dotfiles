local M = {}
local statuses = { open = "○", in_progress = "●", blocked = "⊘", deferred = "◇", closed = "✓" }

local function plain(text)
	return tostring(text):gsub("[%c]", " ")
end

function M.rows(graph, expanded, attention)
	local by_id, children, parents, warning, rows, seen = {}, {}, {}, {}, {}, {}
	for _, task in ipairs(graph.items) do
		by_id[task.id] = task
	end
	for _, edge in ipairs(graph.edges) do
		if edge.type == "parent-child" then
			if parents[edge.issue_id] then
				warning[edge.issue_id] = "multiple parents"
			else
				parents[edge.issue_id] = edge.depends_on_id
			end
		end
	end
	for id, parent in pairs(parents) do
		if by_id[id] then
			if by_id[parent] then
				children[parent] = children[parent] or {}
				children[parent][#children[parent] + 1] = id
			else
				warning[id] = "parent outside project: " .. parent
			end
		end
	end
	local function sort(ids)
		table.sort(ids, function(a, b)
			return by_id[a].title == by_id[b].title and a < b or by_id[a].title < by_id[b].title
		end)
	end
	for _, ids in pairs(children) do
		sort(ids)
	end
	local function visit(root, force)
		local stack = { { id = root, depth = 0, visible = true } }
		while #stack > 0 do
			local entry = table.remove(stack)
			if not seen[entry.id] then
				seen[entry.id] = true
				local task = by_id[entry.id]
				local descendants = children[entry.id] or {}
				if entry.visible then
					local mark = #descendants == 0 and "·" or expanded[entry.id] and "▾" or "▸"
					local signal = attention and attention(task) or nil
					local suffix = (signal and " ! " .. plain(signal) or "")
						.. (warning[entry.id] and " ⚠ " .. warning[entry.id] or "")
						.. (force and entry.depth == 0 and " ⚠ cyclic containment" or "")
					rows[#rows + 1] = {
						id = entry.id,
						text = string.rep("  ", math.min(entry.depth, 12))
							.. mark
							.. " "
							.. (statuses[task.status] or ("[" .. plain(task.status or "unknown") .. "]"))
							.. " "
							.. plain(task.title)
							.. " · "
							.. plain(task.id)
							.. suffix,
					}
				end
				for index = #descendants, 1, -1 do
					stack[#stack + 1] = {
						id = descendants[index],
						depth = entry.depth + 1,
						visible = entry.visible and expanded[entry.id] == true,
					}
				end
			end
		end
	end
	local ids = vim.tbl_keys(by_id)
	sort(ids)
	for _, id in ipairs(ids) do
		if not parents[id] or not by_id[parents[id]] then
			visit(id)
		end
	end
	for _, id in ipairs(ids) do
		if not seen[id] then
			visit(id, true)
		end
	end
	return rows, parents
end

return M
