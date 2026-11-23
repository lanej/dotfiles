local M = {}

-- Build a containment forest without treating blocker edges as children. Malformed
-- graphs stay inspectable: cut revisited edges, retain their source relationship.
function M.forest(graph)
	local by_id, children, parents, warnings, seen = {}, {}, {}, {}, {}
	for _, task in ipairs(graph.items) do
		by_id[task.id] = task
	end
	for _, edge in ipairs(graph.edges) do
		if edge.type == "parent-child" then
			if parents[edge.issue_id] then
				warnings[edge.issue_id] = "Multiple parents"
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
				warnings[id] = "Parent outside project: " .. parent
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
	local forest = {}
	local function visit(root, cyclic)
		local stack = { { id = root, into = forest, guides = "", depth = 0 } }
		while #stack > 0 do
			local entry = table.remove(stack)
			if not seen[entry.id] then
				seen[entry.id] = true
				local node = {
					id = entry.id,
					task = by_id[entry.id],
					children = {},
					guides = entry.guides,
					branch = entry.branch,
					depth = entry.depth,
					warning = warnings[entry.id] or (cyclic and entry.id == root and "Cyclic containment" or nil),
				}
				entry.into[#entry.into + 1] = node
				local ids = children[entry.id] or {}
				for index = #ids, 1, -1 do
					local more = index < #ids
					stack[#stack + 1] = {
						id = ids[index],
						into = node.children,
						depth = entry.depth + 1,
						guides = (
							entry.guides
							.. (entry.branch and (entry.branch == "├─ " and "│  " or "   ") or "")
						):sub(-21),
						branch = more and "├─ " or "└─ ",
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
	return forest, parents
end

return M
