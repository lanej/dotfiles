-- WezTerm Configuration
-- Replaces Kitty + tmux with native WezTerm multiplexing
local wezterm = require("wezterm")
local act = wezterm.action

local config = {}
if wezterm.config_builder then
	config = wezterm.config_builder()
end

-- =============================================================================
-- COLORS - Exact Nord Theme Match (from kitty/kittyconf)
-- =============================================================================

config.colors = {
	foreground = "#D8DEE9",
	background = "#2E3440",
	cursor_bg = "#81A1C1",
	cursor_fg = "#2E3440",
	cursor_border = "#81A1C1",
	selection_fg = "#000000",
	selection_bg = "#FFFACD",

	-- ANSI colors (kitty lines 61-91)
	ansi = {
		"#434C5E", -- black
		"#BF616A", -- red
		"#A3BE8C", -- green
		"#EBCB8B", -- yellow
		"#81A1C1", -- blue
		"#B48EAD", -- magenta
		"#88C0D0", -- cyan
		"#E5E9F0", -- white
	},
	brights = {
		"#4C566A", -- bright black
		"#D08770", -- bright red
		"#B5CEA8", -- bright green
		"#E5C07B", -- bright yellow
		"#88C0D0", -- bright blue
		"#C678DD", -- bright magenta
		"#8FBCBB", -- bright cyan
		"#ECEFF4", -- bright white
	},

	split = "#4C566A", -- Nord dark gray for pane borders

	tab_bar = {
		background = "#2E3440",
		active_tab = {
			bg_color = "#88C0D0", -- Nord cyan
			fg_color = "#2E3440", -- Black
		},
		inactive_tab = {
			bg_color = "#4C566A", -- Nord dark gray
			fg_color = "#88C0D0", -- Nord cyan
		},
		inactive_tab_hover = {
			bg_color = "#4C566A",
			fg_color = "#D8DEE9",
		},
		new_tab = {
			bg_color = "#2E3440",
			fg_color = "#88C0D0",
		},
		new_tab_hover = {
			bg_color = "#4C566A",
			fg_color = "#D8DEE9",
		},
	},
}

-- =============================================================================
-- FONT & VISUAL SETTINGS
-- =============================================================================

config.font = wezterm.font("Hack Nerd Font Mono", { weight = "Regular" })
config.font_size = 13.0
config.cell_width = 0.90 -- Tighter character spacing (90%)

-- Cursor settings (kitty lines 35-38)
config.default_cursor_style = "SteadyBlock"
config.cursor_blink_rate = 500
config.cursor_blink_ease_in = "Constant"
config.cursor_blink_ease_out = "Constant"

-- Window settings - NO DECORATIONS (critical requirement)
config.window_decorations = "RESIZE" -- No title bar
config.window_padding = {
	left = 2,
	right = 2,
	top = 2,
	bottom = 2,
}

-- Scrollback (tmux line 47, kitty line 42)
config.scrollback_lines = 99999999

-- Disable audio bell (kitty lines 15-17)
config.audible_bell = "Disabled"
config.visual_bell = {
	fade_in_function = "EaseIn",
	fade_in_duration_ms = 0,
	fade_out_function = "EaseOut",
	fade_out_duration_ms = 0,
}

-- Inactive pane dimming (tmux lines 153-154: #2E3440 → #2a3038)
config.inactive_pane_hsb = {
	saturation = 0.90,
	brightness = 0.80,
}

-- =============================================================================
-- TAB BAR STYLING (Powerline Slanted)
-- =============================================================================

config.use_fancy_tab_bar = false
config.tab_bar_at_bottom = false
config.show_tab_index_in_tab_bar = false
config.tab_max_width = 32

-- Powerline separators
local SOLID_LEFT_ARROW = wezterm.nerdfonts.pl_right_hard_divider
local SOLID_RIGHT_ARROW = wezterm.nerdfonts.pl_left_hard_divider

-- Format tab titles (tmux style: index* title)
wezterm.on("format-tab-title", function(tab, tabs, panes, config, hover, max_width)
	local background = "#4C566A"
	local foreground = "#88C0D0"

	if tab.is_active then
		background = "#88C0D0"
		foreground = "#2E3440"
	end

	local index = tab.tab_index
	local title = tab.active_pane.title

	-- Truncate if needed
	if title and #title > 20 then
		title = title:sub(1, 17) .. "..."
	end

	-- Mark active with *
	local marker = tab.is_active and "*" or ""

	-- Determine next tab's background for interlocking chevrons
	local next_tab = tabs[tab.tab_index + 2] -- tabs is 1-indexed
	local next_background = "#2E3440" -- default to bar background
	if next_tab then
		if next_tab.is_active then
			next_background = "#88C0D0"
		else
			next_background = "#4C566A"
		end
	end

	return {
		{ Background = { Color = background } },
		{ Foreground = { Color = foreground } },
		{ Text = " " .. index .. marker .. " " .. (title or "shell") .. " " },
		{ Background = { Color = next_background } },
		{ Foreground = { Color = background } },
		{ Text = SOLID_RIGHT_ARROW },
	}
end)

-- =============================================================================
-- DYNAMIC PANE TITLES (show command or directory)
-- =============================================================================

wezterm.on("update-status", function(window, pane)
	-- Update pane title
	local process_name = pane:get_foreground_process_name()
	local cwd = pane:get_current_working_dir()

	if process_name then
		local cmd = process_name:match("([^/]+)$")

		-- If not a shell, show command
		if cmd and not (cmd:match("^zsh") or cmd:match("^bash") or cmd:match("^sh$")) then
			pane:set_title(cmd)
			return
		end
	end

	-- Show directory
	if cwd then
		local dir = cwd.file_path:match("([^/]+)$") or cwd.file_path
		pane:set_title(dir)
	end
end)

-- =============================================================================
-- STATUS BAR (Left: Workspace | Right: SSH + Battery + Time + Host)
-- =============================================================================

config.status_update_interval = 10000 -- 10 seconds

-- Left status: Workspace name (like tmux session)
wezterm.on("update-status", function(window, pane)
	local workspace = window:active_workspace()

	window:set_left_status(wezterm.format({
		{ Background = { Color = "#81A1C1" } }, -- Nord blue
		{ Foreground = { Color = "#2E3440" } },
		{ Attribute = { Intensity = "Bold" } },
		{ Text = " " .. workspace .. " " },
		{ Background = { Color = "#2E3440" } },
		{ Foreground = { Color = "#81A1C1" } },
		{ Text = SOLID_RIGHT_ARROW },
	}))
end)

-- Right status: SSH + Battery + DateTime + Hostname
wezterm.on("update-right-status", function(window, pane)
	-- Build segments array with background colors for interlocking
	local segment_data = {}

	-- SSH indicator
	local ssh_env = os.getenv("SSH_CONNECTION") or os.getenv("SSH_CLIENT") or os.getenv("SSH_TTY")
	if ssh_env then
		table.insert(segment_data, {
			bg = "#4C566A",
			fg = "#88C0D0",
			text = " 🔐 SSH ",
		})
	end

	-- Battery status
	for _, b in ipairs(wezterm.battery_info()) do
		local charge = b.state_of_charge * 100
		local icon = "⚡"
		local color = "#EBCB8B" -- Nord yellow

		if b.state == "Charging" then
			icon = "🔋"
			color = "#A3BE8C" -- Nord green
		elseif charge < 10 then
			icon = "🪫"
			color = "#BF616A" -- Nord red
		elseif charge < 20 then
			icon = "⚠️"
			color = "#D08770" -- Nord orange
		end

		table.insert(segment_data, {
			bg = "#4C566A",
			fg = color,
			text = string.format(" %s%.0f%% ", icon, charge),
		})
	end

	-- Date and time
	local datetime = wezterm.strftime("%Y-%m-%d %H:%M")
	table.insert(segment_data, {
		bg = "#4C566A",
		fg = "#D8DEE9",
		text = " " .. datetime .. " ",
	})

	-- Hostname
	local hostname = wezterm.hostname()
	table.insert(segment_data, {
		bg = "#88C0D0",
		fg = "#2E3440",
		text = " " .. hostname .. " ",
	})

	-- Build formatted segments with interlocking chevrons
	local formatted_segments = {}
	for i, seg in ipairs(segment_data) do
		local prev_bg = "#2E3440" -- Default to bar background
		if i > 1 then
			prev_bg = segment_data[i - 1].bg
		end

		table.insert(
			formatted_segments,
			wezterm.format({
				{ Background = { Color = prev_bg } },
				{ Foreground = { Color = seg.bg } },
				{ Text = SOLID_LEFT_ARROW },
				{ Background = { Color = seg.bg } },
				{ Foreground = { Color = seg.fg } },
				{ Text = seg.text },
			})
		)
	end

	window:set_right_status(table.concat(formatted_segments, ""))
end)

-- =============================================================================
-- LEADER KEY & KEYBINDINGS
-- =============================================================================

-- Leader key: C-f (matching tmux)
config.leader = { key = "f", mods = "CTRL", timeout_milliseconds = 1000 }
config.keys = {}

-- Send prefix to terminal (tmux line 13-14)
table.insert(config.keys, {
	key = "f",
	mods = "LEADER|CTRL",
	action = act.SendKey({ key = "f", mods = "CTRL" }),
})

-- =============================================================================
-- PANE MANAGEMENT
-- =============================================================================

-- Split panes (tmux lines 120-121)
table.insert(config.keys, {
	key = "s",
	mods = "LEADER",
	action = act.SplitVertical({ domain = "CurrentPaneDomain" }),
})

table.insert(config.keys, {
	key = "v",
	mods = "LEADER",
	action = act.SplitHorizontal({ domain = "CurrentPaneDomain" }),
})

-- Close pane (tmux line 28)
table.insert(config.keys, {
	key = "x",
	mods = "LEADER",
	action = act.CloseCurrentPane({ confirm = true }),
})

-- Resize panes (tmux lines 124-127)
table.insert(config.keys, {
	key = "<",
	mods = "LEADER",
	action = act.AdjustPaneSize({ "Left", 3 }),
})
table.insert(config.keys, {
	key = ">",
	mods = "LEADER",
	action = act.AdjustPaneSize({ "Right", 3 }),
})
table.insert(config.keys, {
	key = "+",
	mods = "LEADER",
	action = act.AdjustPaneSize({ "Up", 3 }),
})
table.insert(config.keys, {
	key = "-",
	mods = "LEADER",
	action = act.AdjustPaneSize({ "Down", 3 }),
})

-- Equalize panes (tmux line 128)
table.insert(config.keys, {
	key = "=",
	mods = "LEADER",
	action = act.PaneSelect({ mode = "SwapWithActive" }),
})

-- Swap panes (tmux lines 93-95)
table.insert(config.keys, {
	key = "J",
	mods = "LEADER|SHIFT",
	action = act.RotatePanes("Clockwise"),
})
table.insert(config.keys, {
	key = "K",
	mods = "LEADER|SHIFT",
	action = act.RotatePanes("CounterClockwise"),
})

-- Cycle panes (tmux line 98)
table.insert(config.keys, {
	key = "Tab",
	mods = "LEADER",
	action = act.ActivatePaneDirection("Next"),
})

-- =============================================================================
-- VIM-AWARE NAVIGATION (C-h/j/k/l)
-- =============================================================================

local function is_vim(pane)
	local process_name = pane:get_foreground_process_name()
	return process_name and (process_name:find("vim") or process_name:find("nvim") or process_name:find("view"))
end

local function navigate(direction)
	return wezterm.action_callback(function(window, pane)
		if is_vim(pane) then
			window:perform_action(act.SendKey({ key = direction, mods = "CTRL" }), pane)
		else
			local dir_map = {
				h = "Left",
				j = "Down",
				k = "Up",
				l = "Right",
			}
			window:perform_action(act.ActivatePaneDirection(dir_map[direction]), pane)
		end
	end)
end

-- Smart C-h/j/k/l navigation (tmux lines 203-217)
table.insert(config.keys, {
	key = "h",
	mods = "CTRL",
	action = navigate("h"),
})
table.insert(config.keys, {
	key = "j",
	mods = "CTRL",
	action = navigate("j"),
})
table.insert(config.keys, {
	key = "k",
	mods = "CTRL",
	action = navigate("k"),
})
table.insert(config.keys, {
	key = "l",
	mods = "CTRL",
	action = navigate("l"),
})

-- Leader+h/j/k/l as fallback (tmux lines 214-217)
table.insert(config.keys, {
	key = "h",
	mods = "LEADER",
	action = act.ActivatePaneDirection("Left"),
})
table.insert(config.keys, {
	key = "j",
	mods = "LEADER",
	action = act.ActivatePaneDirection("Down"),
})
table.insert(config.keys, {
	key = "k",
	mods = "LEADER",
	action = act.ActivatePaneDirection("Up"),
})
table.insert(config.keys, {
	key = "l",
	mods = "LEADER",
	action = act.ActivatePaneDirection("Right"),
})

-- =============================================================================
-- TAB MANAGEMENT
-- =============================================================================

-- New tab (tmux line 103)
table.insert(config.keys, {
	key = "c",
	mods = "LEADER",
	action = act.SpawnTab("CurrentPaneDomain"),
})

-- macOS: cmd+n, cmd+t for new tabs (kitty lines 6-7)
table.insert(config.keys, {
	key = "n",
	mods = "CMD",
	action = act.SpawnTab("CurrentPaneDomain"),
})
table.insert(config.keys, {
	key = "t",
	mods = "CMD",
	action = act.SpawnTab("CurrentPaneDomain"),
})

-- Rename tab (tmux line 107)
table.insert(config.keys, {
	key = "f",
	mods = "LEADER",
	action = act.PromptInputLine({
		description = "Enter new name for tab",
		action = wezterm.action_callback(function(window, pane, line)
			if line then
				window:active_tab():set_title(line)
			end
		end),
	}),
})

-- macOS: cmd+r to rename (kitty line 13)
table.insert(config.keys, {
	key = "r",
	mods = "CMD",
	action = act.PromptInputLine({
		description = "Enter new name for tab",
		action = wezterm.action_callback(function(window, pane, line)
			if line then
				window:active_tab():set_title(line)
			end
		end),
	}),
})

-- Navigate tabs (tmux lines 31-32)
table.insert(config.keys, {
	key = "n",
	mods = "LEADER|CTRL",
	action = act.ActivateTabRelative(1),
})
table.insert(config.keys, {
	key = "p",
	mods = "LEADER|CTRL",
	action = act.ActivateTabRelative(-1),
})

-- macOS: cmd+1-4 for direct tab access (kitty lines 9-12)
for i = 1, 9 do
	table.insert(config.keys, {
		key = tostring(i),
		mods = "CMD",
		action = act.ActivateTab(i - 1),
	})
end

-- macOS: cmd+p for previous tab (kitty line 8)
table.insert(config.keys, {
	key = "p",
	mods = "CMD",
	action = act.ActivateTabRelative(-1),
})

-- =============================================================================
-- WORKSPACE MANAGEMENT (tmux sessions)
-- =============================================================================

-- Rename workspace (tmux line 108)
table.insert(config.keys, {
	key = "w",
	mods = "LEADER",
	action = act.PromptInputLine({
		description = "Enter new name for workspace",
		action = wezterm.action_callback(function(window, pane, line)
			if line then
				wezterm.mux.rename_workspace(wezterm.mux.get_active_workspace(), line)
			end
		end),
	}),
})

-- New workspace (tmux line 104)
table.insert(config.keys, {
	key = "C",
	mods = "LEADER|SHIFT",
	action = act.PromptInputLine({
		description = "Enter name for new workspace",
		action = wezterm.action_callback(function(window, pane, line)
			if line then
				window:perform_action(
					act.SwitchToWorkspace({
						name = line,
					}),
					pane
				)
			end
		end),
	}),
})

-- =============================================================================
-- FUZZY FINDERS
-- =============================================================================

-- Tab switcher (tmux line 40: C-f)
table.insert(config.keys, {
	key = "f",
	mods = "LEADER|CTRL",
	action = wezterm.action_callback(function(window, pane)
		local tabs = window:mux_window():tabs()
		local choices = {}

		for idx, tab in ipairs(tabs) do
			local title = tab:get_title()
			local active_marker = tab:tab_id() == window:active_tab():tab_id() and "[active]" or ""
			table.insert(choices, {
				id = tostring(idx),
				label = string.format("%d | %s %s", idx - 1, title, active_marker),
			})
		end

		window:perform_action(
			act.InputSelector({
				action = wezterm.action_callback(function(inner_window, inner_pane, id, label)
					if id then
						inner_window:perform_action(act.ActivateTab(tonumber(id) - 1), inner_pane)
					end
				end),
				title = "Tabs (current workspace)",
				choices = choices,
				fuzzy = true,
			}),
			pane
		)
	end),
})

-- Workspace switcher (tmux line 41: C-w)
table.insert(config.keys, {
	key = "w",
	mods = "LEADER|CTRL",
	action = wezterm.action_callback(function(window, pane)
		local workspaces = wezterm.mux.get_workspace_names()
		local choices = {}

		for _, ws in ipairs(workspaces) do
			local active_marker = ws == wezterm.mux.get_active_workspace() and "(current)" or ""
			table.insert(choices, {
				id = ws,
				label = string.format("%s %s", ws, active_marker),
			})
		end

		window:perform_action(
			act.InputSelector({
				action = wezterm.action_callback(function(inner_window, inner_pane, id, label)
					if id then
						inner_window:perform_action(act.SwitchToWorkspace({ name = id }), inner_pane)
					end
				end),
				title = "Workspaces",
				choices = choices,
				fuzzy = true,
			}),
			pane
		)
	end),
})

-- =============================================================================
-- GOLDEN RATIO LAYOUT (38% / 62%)
-- =============================================================================

local function golden_ratio(window, pane, force)
	local tab = window:active_tab()
	if not tab then
		return
	end

	local panes = tab:panes_with_info()

	-- Only works with 2+ panes
	if #panes < 2 then
		return
	end

	-- Get dimensions
	local tab_size = tab:get_size()
	if not tab_size then
		return
	end

	-- Find leftmost pane
	local leftmost = nil
	local leftmost_x = 999999

	for _, pane_info in ipairs(panes) do
		if pane_info.left < leftmost_x then
			leftmost_x = pane_info.left
			leftmost = pane_info.pane
		end
	end

	if not leftmost then
		return
	end

	-- Calculate golden ratio width (38.2%)
	local target_width = math.floor(tab_size.cols * 0.382)

	-- Cap between min/max
	local MIN_COLUMNS = 60
	local MAX_COLUMNS = 180
	if target_width < MIN_COLUMNS then
		target_width = MIN_COLUMNS
	elseif target_width > MAX_COLUMNS then
		target_width = MAX_COLUMNS
	end

	-- Get current width
	local current_width = 0
	for _, pane_info in ipairs(panes) do
		if pane_info.pane:pane_id() == leftmost:pane_id() then
			current_width = pane_info.width
			break
		end
	end

	-- Skip if already at target (unless forced)
	if not force and math.abs(current_width - target_width) < 5 then
		return
	end

	-- Resize
	local diff = target_width - current_width
	leftmost:activate()
	if diff > 0 then
		window:perform_action(act.AdjustPaneSize({ "Right", math.abs(diff) }), leftmost)
	else
		window:perform_action(act.AdjustPaneSize({ "Left", math.abs(diff) }), leftmost)
	end
end

-- Golden ratio keybindings (tmux lines 131-132)
table.insert(config.keys, {
	key = "g",
	mods = "LEADER",
	action = wezterm.action_callback(function(window, pane)
		golden_ratio(window, pane, false)
	end),
})

table.insert(config.keys, {
	key = "G",
	mods = "LEADER|SHIFT",
	action = wezterm.action_callback(function(window, pane)
		golden_ratio(window, pane, true)
	end),
})

-- =============================================================================
-- MISC KEYBINDINGS
-- =============================================================================

-- Reload config (tmux line 83)
table.insert(config.keys, {
	key = "r",
	mods = "LEADER",
	action = act.ReloadConfiguration,
})

-- Copy mode (tmux lines 16-26)
table.insert(config.keys, {
	key = "[",
	mods = "LEADER",
	action = act.ActivateCopyMode,
})

-- macOS: Cmd+Q to close window (kitty line 33)
table.insert(config.keys, {
	key = "q",
	mods = "CMD",
	action = act.CloseCurrentPane({ confirm = true }),
})

-- macOS: Cmd+W to close tab (kitty line 34)
table.insert(config.keys, {
	key = "w",
	mods = "CMD",
	action = act.CloseCurrentTab({ confirm = true }),
})

-- =============================================================================
-- MISC SETTINGS
-- =============================================================================

-- Start tabs at index 0 (tmux line 143)
config.enable_tab_bar = true
config.hide_tab_bar_if_only_one_tab = true

-- URL handling (kitty lines 39-40)
config.hyperlink_rules = wezterm.default_hyperlink_rules()

-- macOS specific (kitty line 19)
config.quit_when_all_windows_are_closed = true

return config
