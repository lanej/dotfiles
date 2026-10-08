local M = {}

local relations = {
	PROJECT = "󰆼",
	DATASET = "󰉋",
	TABLE = "󰓫",
	["TABLE ALIAS"] = "󰓫",
	CTE = "󰓫",
}

local function is_bigquery(ctx)
	if not ctx.item.client_id then
		return false
	end
	local client = vim.lsp.get_client_by_id(ctx.item.client_id)
	return client and client.name == "bqls"
end

function M.label_text(ctx)
	if is_bigquery(ctx) then
		return ctx.label
	end
	return require("colorful-menu").blink_components_text(ctx)
end

function M.label_highlight(ctx)
	if not is_bigquery(ctx) or (not relations[ctx.item.detail] and ctx.kind ~= "Field") then
		return require("colorful-menu").blink_components_highlight(ctx)
	end
	local highlights = {
		{ 0, #ctx.label, group = relations[ctx.item.detail] and "@module" or "@variable" },
	}
	for _, idx in ipairs(ctx.label_matched_indices) do
		highlights[#highlights + 1] = { idx, idx + 1, group = "BlinkCmpLabelMatch" }
	end
	return highlights
end

function M.type_highlight(ctx)
	return relations[ctx.item.detail] and "@module" or "@type"
end

function M.type_text(ctx)
	if is_bigquery(ctx) then
		return ctx.item.detail or ""
	end
	return ""
end

function M.icon_text(ctx)
	local icon = is_bigquery(ctx) and relations[ctx.item.detail] or nil
	return (icon or ctx.kind_icon) .. ctx.icon_gap
end

function M.icon_highlight(ctx)
	local group = is_bigquery(ctx) and relations[ctx.item.detail] and "@module" or ctx.kind_hl
	if is_bigquery(ctx) and ctx.kind == "Field" then
		group = "@variable"
	end
	return { { group = group, priority = 20000 } }
end

return M
