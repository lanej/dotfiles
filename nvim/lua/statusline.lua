require("galaxyline").short_line_list = { "NvimTree", "fugitive", "fugitiveblame", "help", "qf" }

local vi_mode_mapping = {
  [""] = { "Empty", "-" },
  ["!"] = { "Shell", "-" },
  [""] = { "CommonVisual", "B" },
  ["R"] = { "Replace", "R" },
  ["Rv"] = { "Normal", "-" },
  ["S"] = { "Normal", "-" },
  ["V"] = { "CommonVisual", "V" },
  ["c"] = { "Command", "C" },
  ["ce"] = { "Normal", "-" },
  ["cv"] = { "Normal", "-" },
  ["i"] = { "Insert", "I" },
  ["ic"] = { "Normal", "-" },
  ["n"] = { "Normal", "N" },
  ["no"] = { "Normal", "-" },
  ["r"] = { "Normal", "-" },
  ["r?"] = { "Normal", "-" },
  ["rm"] = { "Normal", "-" },
  ["s"] = { "Normal", "-" },
  ["t"] = { "Terminal", "T" },
  ["v"] = { "CommonVisual", "v" },
}

-- local colors = require("tokyonight.colors").setup({})
local colors = require("tender.colors")

-- Local helper functions
local mode_color = function()
  local mode_colors = {
    n = tostring(colors.cyan),
    i = tostring(colors.green),
    c = tostring(colors.orange),
    V = tostring(colors.yellow),
    [""] = tostring(colors.magenta),
    v = tostring(colors.blue),
    R = tostring(colors.red),
  }

  local color = mode_colors[vim.fn.mode()]

  if color == nil then color = tostring(colors.red) end

  return color
end

local gl = require("galaxyline")
local gls = gl.section

gls.left[1] = {
  ViMode = {
    provider = function()
      if vi_mode_mapping[vim.fn.mode()] == nil then
        return " -"
      else
        vim.api.nvim_command("hi GalaxyViMode guibg=" .. mode_color())
        return " " .. string.format("%s", vi_mode_mapping[vim.fn.mode()][2]) .. " "
      end
    end,
    highlight = { tostring(colors.bg), tostring(colors.bg) },
  },
}
gls.left[2] = {
  LeftGitBranch = {
    provider = function()
      if require("galaxyline.condition").check_git_workspace() then
        local branch = require("galaxyline.provider_vcs").get_git_branch()
        if branch == nil then
          return "   ?"
        else
          return "   " .. branch
        end
      else
        return "   "
      end
    end,
    highlight = { tostring(colors.purple), tostring(colors.bg) },
    separator = " ",
    separator_highlight = { tostring(colors.bg), tostring(colors.bg) },
  },
}
gls.left[3] = {
  LeftGitDiffSeparator = {
    provider = function() return "" end,
    separator = " ",
    highlight = { tostring(colors.purple), tostring(colors.bg) },
    separator_highlight = { tostring(colors.bg), tostring(colors.bg) },
  },
}
gls.left[4] = {
  LeftGitDiffAdd = {
    condition = require("galaxyline.condition").check_git_workspace,
    provider = function()
      if require("galaxyline.provider_vcs").diff_add() then
        vim.api.nvim_command("hi GalaxyLeftGitDiffAdd guifg=" .. tostring(colors.green))
        return "+" .. require("galaxyline.provider_vcs").diff_add()
      else
        vim.api.nvim_command("hi GalaxyLeftGitDiffAdd guifg=" .. tostring(colors.shadow))
        return "+0 "
      end
    end,
    highlight = { tostring(colors.fg), tostring(colors.bg) },
    separator_highlight = { tostring(colors.bg), tostring(colors.bg) },
  },
}
gls.left[5] = {
  LeftGitDiffModified = {
    condition = require("galaxyline.condition").check_git_workspace,
    provider = function()
      if require("galaxyline.provider_vcs").diff_modified() then
        vim.api.nvim_command("hi GalaxyLeftGitDiffModified guifg=" .. tostring(colors.orange))
        return "~" .. require("galaxyline.provider_vcs").diff_modified()
      else
        vim.api.nvim_command("hi GalaxyLeftGitDiffModified guifg=" .. tostring(colors.shadow))
        return "~0 "
      end
    end,
    highlight = { tostring(colors.fg), tostring(colors.bg) },
    separator_highlight = { tostring(colors.bg), tostring(colors.bg) },
  },
}
gls.left[6] = {
  LeftGitDiffRemove = {
    condition = require("galaxyline.condition").check_git_workspace,
    provider = function()
      if require("galaxyline.provider_vcs").diff_remove() then
        vim.api.nvim_command("hi GalaxyLeftGitDiffRemove guifg=" .. tostring(colors.red))
        return "-" .. require("galaxyline.provider_vcs").diff_remove()
      else
        vim.api.nvim_command("hi GalaxyLeftGitDiffRemove guifg=" .. tostring(colors.shadow))
        return "-0 "
      end
    end,
    highlight = { tostring(colors.fg), tostring(colors.bg) },
    separator_highlight = { tostring(colors.bg), tostring(colors.bg) },
  },
}

gls.mid[1] = {
  MidFileName = {
    provider = function()
      if vim.fn.expand "%:p" == 0 then return "-" end
      if vim.fn.winwidth(0) > 80 then
        return vim.fn.expand "%:~"
      else
        return vim.fn.expand "%:t"
      end
    end,
    highlight = { tostring(colors.fg), tostring(colors.bg) },
  },
}

gls.right[1] = {
  RightLspError = {
    provider = function()
      if #vim.tbl_keys(vim.lsp.buf_get_clients()) <= 0 then return end

      if vim.lsp.diagnostic.get_count(0, "Error") ~= 0 then
        vim.api.nvim_command("hi GalaxyRightLspError guifg=" .. tostring(colors.red))
        return "!" .. vim.lsp.diagnostic.get_count(0, "Error") .. " "
      end
    end,
    highlight = { tostring(colors.fg), tostring(colors.bg) },
    separator_highlight = { tostring(colors.bg), tostring(colors.bg) },
  },
}

gls.right[2] = {
  RightLspWarning = {
    provider = function()
      if #vim.tbl_keys(vim.lsp.buf_get_clients()) <= 0 then return end

      if vim.lsp.diagnostic.get_count(0, "Warning") ~= 0 then
        vim.api.nvim_command("hi GalaxyRightLspWarning guifg=" .. tostring(colors.orange))
        return "?" .. vim.lsp.diagnostic.get_count(0, "Warning") .. " "
      end

    end,
    highlight = { tostring(colors.fg), tostring(colors.bg) },
    separator_highlight = { tostring(colors.bg), tostring(colors.bg) },
  },
}

gls.right[3] = {
  RightLspInformation = {
    provider = function()
      if #vim.tbl_keys(vim.lsp.buf_get_clients()) <= 0 then return end

      if vim.lsp.diagnostic.get_count(0, "Information") ~= 0 then
        vim.api.nvim_command("hi GalaxyRightLspInformation guifg=" .. tostring(colors.blue))
        return "+" .. vim.lsp.diagnostic.get_count(0, "Information") .. " "
      end
    end,
    highlight = { tostring(colors.fg), tostring(colors.bg) },
    separator_highlight = { tostring(colors.bg), tostring(colors.bg) },
  },
}

gls.right[4] = {
  RightLspHint = {
    provider = function()
      if #vim.tbl_keys(vim.lsp.buf_get_clients()) <= 0 then return end

      if vim.lsp.diagnostic.get_count(0, "Hint") ~= 0 then
        vim.api.nvim_command("hi GalaxyRightLspHint guifg=" .. tostring(colors.green1))
        return "-" .. vim.lsp.diagnostic.get_count(0, "Hint") .. " "
      end

    end,
    highlight = { tostring(colors.fg), tostring(colors.bg) },
    separator_highlight = { tostring(colors.bg), tostring(colors.bg) },
  },
}

gls.right[5] = {
  RightLspHintSeparator = {
    provider = function() return "《" end,
    highlight = { tostring(colors.yellow), tostring(colors.bg) },
    separator_highlight = { tostring(colors.bg), tostring(colors.bg) },
  },
}

gls.right[6] = {
  RightLspClient = {
    provider = function()
      if #vim.tbl_keys(vim.lsp.buf_get_clients()) >= 1 then
        local lsp_client_name_first = vim.lsp.get_client_by_id(tonumber(
                                                                 vim.inspect(vim.tbl_keys(vim.lsp
                                                                                            .buf_get_clients())):match(
                                                                   "%d+"))).name:match("%l+")

        if lsp_client_name_first == nil then
          vim.api.nvim_command("hi GalaxyRightLspClient guifg=" .. tostring(colors.fg))
          return #vim.tbl_keys(vim.lsp.buf_get_clients()) .. ": "
        else
          vim.api.nvim_command("hi GalaxyRightLspClient guifg=" .. tostring(colors.yellow))
          return #vim.tbl_keys(vim.lsp.buf_get_clients()) .. ":" .. lsp_client_name_first .. " "
        end
      else
        return " "
      end
    end,
    separator = " ",
    highlight = { tostring(colors.fg), tostring(colors.bg) },
    separator_highlight = { tostring(colors.bg), tostring(colors.bg) },
  },
}

gls.right[7] = {
  RightPositionSeparator = {
    provider = function() return "  " end,
    highlight = { tostring(colors.fg), tostring(colors.bg) },
    separator_highlight = { tostring(colors.bg), tostring(colors.bg) },
  },
}

require("galaxyline").section.short_line_left = {
  {
    ShortLineLeftBufferType = {
      provider = function()
        local BufferTypeMap = {
          ["NvimTree"] = "D",
          ["fugitive"] = "G",
          ["fugitiveblame"] = "B",
          ["help"] = "H",
          ["qf"] = "Q",
          ["zsh"] = "T",
          ["bash"] = "T",
        }
        local name = BufferTypeMap[vim.bo.filetype] or "?"
        return string.format("  %s ", name)
      end,
      separator = " ",
    },
  },
  {
    ShortLineLeftFile = {
      provider = function()
        if vim.fn.expand "%:p" == 0 then return "-" end
        if vim.fn.winwidth(0) > 80 then
          return vim.fn.expand "%:~"
        else
          return vim.fn.expand "%:t"
        end
      end,
    },
  },
}

require("galaxyline").section.short_line_right = {
  {
    ShortLineRightBlank = {
      provider = function()
        if vim.bo.filetype == "toggleterm" then
          return " " .. vim.api.nvim_buf_get_var(0, "toggle_number") .. " "
        else
          return "  "
        end
      end,
      separator = "",
    },
  },
  {
    ShortLineRightInformational = {
      provider = function() return " Neovim " end,
      separator = "",
    },
  },
}