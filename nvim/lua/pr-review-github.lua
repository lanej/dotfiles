-- GitHub facts stay distinct from queue policy. All requests use authenticated gh.
local M = {}

local function present(value)
	return value ~= nil and value ~= vim.NIL
end

function M.request(args, input, callback)
	local command = { "gh", "api", "--hostname", "github.com" }
	vim.list_extend(command, args)
	vim.system(
		command,
		{
			text = true,
			stdin = input and vim.json.encode(input) or nil,
			timeout = 60000,
		},
		vim.schedule_wrap(function(result)
			local ok, data = pcall(vim.json.decode, result.stdout or "")
			if result.code ~= 0 then
				callback(
					nil,
					vim.trim(result.stderr or "") ~= "" and vim.trim(result.stderr) or "gh failed or timed out"
				)
			elseif not ok then
				callback(nil, "gh returned invalid JSON")
			elseif present(data.errors) and #data.errors > 0 then
				local messages = {}
				for _, err in ipairs(data.errors) do
					messages[#messages + 1] = err.message
				end
				callback(nil, table.concat(messages, "; "))
			else
				callback(data)
			end
		end)
	)
end

function M.graphql(query, variables, callback)
	M.request({ "graphql", "--input", "-" }, { query = query, variables = variables }, function(data, err)
		callback(data and data.data or nil, err)
	end)
end

-- Broad team searches can time out while resolving a large page of rich PR nodes.
local search_query = [[
query PRReviewSearch($query:String!, $cursor:String) {
  search(query:$query, type:ISSUE, first:10, after:$cursor) {
    issueCount pageInfo { hasNextPage endCursor }
    nodes { ... on PullRequest {
      id number title body url createdAt headRefOid isDraft state
      author { login } repository { nameWithOwner }
    } }
  }
}]]

local checks_query = [[
query PRReviewChecks($id:ID!, $cursor:String) {
  node(id:$id) { ... on PullRequest {
    headRefOid commits(last:1) { nodes { commit {
      statusCheckRollup { contexts(first:100, after:$cursor) {
        pageInfo { hasNextPage endCursor } nodes {
          ... on CheckRun {
            name status conclusion detailsUrl
            checkSuite { workflowRun { workflow { name } } }
          }
          ... on StatusContext { context state description targetUrl }
        }
      } }
    } } }
  } }
}]]

local reviews_query = [[
query PRReviewHistory($id:ID!, $login:String!, $cursor:String) {
  node(id:$id) { ... on PullRequest {
    headRefOid reviews(first:100, author:$login, after:$cursor) {
      pageInfo { hasNextPage endCursor }
      nodes { state submittedAt commit { oid } }
    }
  } }
}]]

local batch_query = [[
query PRReviewBatch($ids:[ID!]!, $login:String!) {
  nodes(ids:$ids) { ... on PullRequest {
    id headRefOid
    commits(last:1) { nodes { commit {
      statusCheckRollup { contexts(first:100) {
        pageInfo { hasNextPage endCursor } nodes {
          ... on CheckRun {
            name status conclusion detailsUrl
            checkSuite { workflowRun { workflow { name } } }
          }
          ... on StatusContext { context state description targetUrl }
        }
      } }
    } } }
    reviews(first:100, author:$login) {
      pageInfo { hasNextPage endCursor }
      nodes { state submittedAt commit { oid } }
    }
  } }
}]]

-- Unknown observations cannot promote a PR above known passing checks.
function M.check_status(checks, complete)
	if not complete then
		return "unknown"
	end
	local count, failed, pending, unknown = 0, false, false, false
	for _, check in ipairs(checks) do
		local run = check.checkSuite and check.checkSuite ~= vim.NIL and check.checkSuite.workflowRun
		local workflow = run and run ~= vim.NIL and run.workflow
		local exempt = check.name == "check-all-owners"
			and workflow
			and workflow ~= vim.NIL
			and workflow.name == "Require All Owners Approval"
		if not exempt then
			count = count + 1
			local state = check.state or (check.status == "COMPLETED" and check.conclusion or check.status)
			if state == "SUCCESS" or state == "SKIPPED" or state == "NEUTRAL" then
				-- Accepted terminal results.
			elseif
				state == "PENDING"
				or state == "QUEUED"
				or state == "IN_PROGRESS"
				or state == "WAITING"
				or state == "REQUESTED"
				or state == "EXPECTED"
			then
				pending = true
			elseif
				state == "FAILURE"
				or state == "ERROR"
				or state == "CANCELLED"
				or state == "TIMED_OUT"
				or state == "ACTION_REQUIRED"
				or state == "STARTUP_FAILURE"
				or state == "STALE"
			then
				failed = true
			else
				unknown = true
			end
		end
	end
	if failed then
		return "failed"
	elseif pending then
		return "pending"
	elseif unknown then
		return "unknown"
	elseif count == 0 then
		return "missing"
	end
	return "passing"
end

function M.sort(prs)
	local priority = { passing = 1, pending = 2, failed = 3, missing = 4, unknown = 5 }
	table.sort(prs, function(a, b)
		if a.check_status ~= b.check_status then
			return priority[a.check_status] < priority[b.check_status]
		elseif a.personal ~= b.personal then
			return a.personal
		elseif a.createdAt ~= b.createdAt then
			return a.createdAt < b.createdAt
		end
		return a.url < b.url
	end)
end

local function connection_pages(query, variables, extract, consume, callback)
	local cursors = variables.cursor and { [variables.cursor] = true } or {}
	local function page()
		M.graphql(query, variables, function(data, err)
			if err then
				callback(err)
				return
			end
			local connection = extract(data)
			if not connection then
				callback("GitHub returned an unavailable connection")
				return
			end
			consume(connection)
			if connection.pageInfo.hasNextPage then
				local cursor = connection.pageInfo.endCursor
				if not present(cursor) or cursors[cursor] then
					callback("GitHub pagination stopped without a new cursor")
					return
				end
				cursors[cursor], variables.cursor = true, cursor
				page()
			else
				callback()
			end
		end)
	end
	page()
end

function M.repository(cwd, callback)
	vim.system(
		{ "git", "remote", "get-url", "origin" },
		{ cwd = cwd, text = true, timeout = 10000 },
		vim.schedule_wrap(function(result)
			if result.code ~= 0 then
				callback(
					nil,
					"Current directory needs a GitHub checkout with an origin remote; use :PRReviewsAll for all repositories"
				)
				return
			end
			local url = vim.trim(result.stdout)
			local repo = url:match("^git@github%.com:(.+)$")
				or url:match("^https://github%.com/(.+)$")
				or url:match("^ssh://git@github%.com/(.+)$")
			repo = repo and repo:gsub("/$", ""):gsub("%.git$", ""):lower()
			if repo and repo:match("^[%w_.-]+/[%w_.-]+$") then
				callback(repo)
				return
			end
			-- Bind fallback to this origin, rather than gh's environment or
			-- configured default remote, and accept only GitHub.com results.
			vim.system(
				{ "gh", "repo", "view", url, "--json", "nameWithOwner,url" },
				{ cwd = cwd, text = true, timeout = 10000, env = { GH_REPO = "", GH_HOST = "github.com" } },
				vim.schedule_wrap(function(remote)
					local ok, data = pcall(vim.json.decode, remote.stdout or "")
					local name = ok and type(data) == "table" and data.nameWithOwner
					if
						remote.code == 0
						and type(name) == "string"
						and name:match("^[%w_.-]+/[%w_.-]+$")
						and data.url == "https://github.com/" .. name
					then
						callback(name:lower())
					else
						callback(
							nil,
							"Cannot identify the current GitHub repository; use :PRReviewsAll for all repositories"
						)
					end
				end)
			)
		end)
	)
end

function M.discover(include_reviewed, callback, known_login, repository)
	local errors, prs, by_id, login = {}, {}, {}, nil
	local next_index, workers = 1, 2
	local function report(message)
		errors[#errors + 1] = message
	end
	local function checks(node, pr)
		if not present(node) or node.headRefOid ~= pr.headRefOid then
			return nil
		end
		local commit = node.commits.nodes[1]
		local rollup = commit and commit.commit.statusCheckRollup
		return present(rollup) and rollup.contexts or { nodes = {}, pageInfo = { hasNextPage = false } }
	end
	local function reviews(node, pr)
		return present(node) and node.headRefOid == pr.headRefOid and node.reviews or nil
	end
	local function consume_reviews(pr, connection)
		for _, review in ipairs(connection.nodes) do
			if
				present(review.submittedAt)
				and present(review.commit)
				and review.commit.oid == pr.headRefOid
				and review.state ~= "PENDING"
			then
				pr.reviewed = true
			end
		end
	end
	-- The batched first page supplies the common case. Extra pages retain the
	-- same head checks and pagination guards as individual reads.
	local function pages(query, variables, extract, consume, first, done)
		if first then
			consume(first)
			if not first.pageInfo.hasNextPage then
				done()
				return
			end
			if not present(first.pageInfo.endCursor) then
				done("GitHub pagination stopped without a cursor")
				return
			end
			variables.cursor = first.pageInfo.endCursor
		end
		connection_pages(query, variables, extract, consume, done)
	end
	local function enrich_pr(pr, first, done)
		pr.checks = {}
		pages(
			checks_query,
			{ id = pr.id },
			function(data)
				return checks(data.node, pr)
			end,
			function(connection)
				vim.list_extend(pr.checks, connection.nodes)
			end,
			first and checks(first, pr),
			function(check_err)
				pr.check_status = M.check_status(pr.checks, check_err == nil)
				if check_err then
					report(pr.repository.nameWithOwner .. "#" .. pr.number .. " checks: " .. check_err)
				end
				pages(
					reviews_query,
					{ id = pr.id, login = login },
					function(data)
						return reviews(data.node, pr)
					end,
					function(connection)
						consume_reviews(pr, connection)
					end,
					first and reviews(first, pr),
					function(review_err)
						if review_err then
							report(pr.repository.nameWithOwner .. "#" .. pr.number .. " review history: " .. review_err)
						end
						done()
					end
				)
			end
		)
	end
	local function enrich()
		local group, ids = {}, {}
		for _ = 1, 20 do
			local pr = prs[next_index]
			if not pr then
				break
			end
			next_index = next_index + 1
			group[#group + 1], ids[#ids + 1] = pr, pr.id
		end
		if #group == 0 then
			workers = workers - 1
			if workers > 0 then
				return
			end
			local visible = {}
			for _, entry in ipairs(prs) do
				if include_reviewed or not entry.reviewed then
					visible[#visible + 1] = entry
				end
			end
			M.sort(visible)
			callback(visible, errors, login)
			return
		end
		M.graphql(batch_query, { ids = ids, login = login }, function(data, err)
			local nodes = {}
			if not err and data and present(data.nodes) then
				for _, node in ipairs(data.nodes) do
					if present(node) then
						nodes[node.id] = node
					end
				end
			end
			-- On a batch error, read individually to isolate unavailable PRs.
			-- Two workers per batch keep fallback reads bounded to four jobs.
			local index, pending = 1, math.min(2, #group)
			local function take()
				local pr = group[index]
				index = index + 1
				if not pr then
					pending = pending - 1
					if pending == 0 then
						enrich()
					end
					return
				end
				enrich_pr(pr, nodes[pr.id], take)
			end
			for _ = 1, pending do
				take()
			end
		end)
	end
	local function search_sources(sources, index)
		local source = sources[index]
		if not source then
			for _ = 1, workers do
				enrich()
			end
			return
		end
		local count, total = 0, 0
		local restriction = repository and "repo:" .. repository .. " " or ""
		connection_pages(
			search_query,
			{ query = "is:pr is:open draft:false -author:" .. login .. " " .. restriction .. source.query },
			function(data)
				return data.search
			end,
			function(connection)
				total = connection.issueCount
				for _, node in ipairs(connection.nodes) do
					count = count + 1
					if
						present(node.id)
						and node.state == "OPEN"
						and not node.isDraft
						and (not repository or node.repository.nameWithOwner:lower() == repository)
						and (not present(node.author) or node.author.login ~= login)
					then
						local pr = by_id[node.id]
						if not pr then
							pr, by_id[node.id] = node, node
							pr.sources, pr.personal = {}, false
							prs[#prs + 1] = pr
						end
						pr.personal = pr.personal or source.personal
						pr.sources[#pr.sources + 1] = source.label
					end
				end
			end,
			function(err)
				if err then
					report(source.label .. ": " .. err)
				end
				if total > count then
					report(source.label .. ": truncated (" .. count .. "/" .. total .. "; GitHub search caps at 1000)")
				end
				search_sources(sources, index + 1)
			end
		)
	end
	local function with_user(user, err)
		if err then
			callback({}, { "Authentication: " .. err })
			return
		end
		login = user.login
		-- GitHub resolves team membership. Two searches preserve personal
		-- priority without listing teams or issuing a search for each one.
		search_sources({
			{ query = "user-review-requested:" .. login, label = "personal", personal = true },
			{ query = "team-review-requested-user:" .. login, label = "team", personal = false },
		}, 1)
	end
	if known_login then
		with_user({ login = known_login })
	else
		M.request({ "user" }, nil, with_user)
	end
end

return M
