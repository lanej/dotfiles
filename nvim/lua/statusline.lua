  require ('galaxyline').short_line_list = {
  'Mundo',
  'MundoDiff',
  'NvimTree',
  'fugitive',
  'fugitiveblame',
  'help',
  'minimap',
  'qf',
  'tabman',
  'tagbar',
  'toggleterm'
}

local vi_mode_mapping = {
  ['']   = {'Empty',        '-'},
  ['!']  = {'Shell',        '-'},
  [''] = {'CommonVisual', 'B'}, -- NOTE: You'll have to remove '^V' and input a 'real' '^V' sequence. You can do that with the following key sequence: <SHIFT-i> + <CTRL-v> + <CTRL-v> (don't be slow with the double <CTRL-v>)
  ['R']  = {'Replace',      'R'},
  ['Rv'] = {'Normal',       '-'},
  ['S']  = {'Normal',       '-'},
  ['V']  = {'CommonVisual', 'V'},
  ['c']  = {'Command',      'C'},
  ['ce'] = {'Normal',       '-'},
  ['cv'] = {'Normal',       '-'},
  ['i']  = {'Insert',       'I'},
  ['ic'] = {'Normal',       '-'},
  ['n']  = {'Normal',       'N'},
  ['no'] = {'Normal',       '-'},
  ['r']  = {'Normal',       '-'},
  ['r?'] = {'Normal',       '-'},
  ['rm'] = {'Normal',       '-'},
  ['s']  = {'Normal',       '-'},
  ['t']  = {'Terminal',     'T'},
  ['v']  = {'CommonVisual', 'v'}
}

local colors = {
  bg = '#1a1b26',
  black = '#32344a',
  blue = '#7aa2f7',
  cyan = '#449dab',
  fg = '#a9b1d6',
  green = '#9ece6a',
  magenta = '#ad8ee6',
  orange = '#ff9e64',
  red = '#f7768e',
  white = '#787c99',
  yellow = '#e0af68',
}

-- Local helper functions
local mode_color = function()
  local mode_colors = {
    n = colors.cyan,
    i = colors.green,
    c = colors.orange,
    V = colors.yellow,
    [''] = colors.magenta,
    v = colors.blue,
    R = colors.red
  }

  local color = mode_colors[vim.fn.mode()]

  if color == nil then color = colors.red end

  return color
end


local gl = require('galaxyline')
local gls = gl.section

gls.left[1] = {
  ViMode = {
     provider = function()
       if vi_mode_mapping[vim.fn.mode()] == nil then
         return ' -'
       else
         vim.api.nvim_command('hi GalaxyViMode guibg=' .. mode_color())
         return ' ' .. string.format('%s', vi_mode_mapping[vim.fn.mode()][2]) .. ' '
       end
     end,
    highlight = {colors.bg, colors.bg},
  }
}
gls.left[2] = {
  LeftGitBranch = {
    provider = function()
      if require('galaxyline.condition').check_git_workspace() then
        return '   ' .. require('galaxyline.provider_vcs').get_git_branch()
      else
        return '   '
      end
    end,
    highlight = {colors.magenta, colors.bg},
    separator = ' ',
    separator_highlight = {colors.bg, colors.bg},
  }
}
gls.left[3] = {
  LeftGitDiffSeparator = {
    provider = function()
      return ''
    end,
    separator = ' ',
    highlight = { colors.magenta },
  }
}
gls.left[4] = {
  LeftGitDiffAdd = {
    condition = require("galaxyline.condition").check_git_workspace,
    provider = function()
      if require('galaxyline.provider_vcs').diff_add() then
        vim.api.nvim_command('hi GalaxyLeftGitDiffAdd guifg=' .. colors.green)
        return '+' .. require('galaxyline.provider_vcs').diff_add()
      else
        return '+0 '
      end
    end
  }
}
gls.left[5] = {
  LeftGitDiffModified = {
    condition = require("galaxyline.condition").check_git_workspace,
    provider = function()
      if require('galaxyline.provider_vcs').diff_modified() then
        vim.api.nvim_command('hi GalaxyLeftGitDiffModified guifg=' .. colors.cyan)
        return '~' .. require('galaxyline.provider_vcs').diff_modified()
      else
        return '~0 '
      end
    end
  }
}
gls.left[6] = {
  LeftGitDiffRemove = {
    condition = require("galaxyline.condition").check_git_workspace,
    provider = function()
      if require('galaxyline.provider_vcs').diff_remove() then
        vim.api.nvim_command('hi GalaxyLeftGitDiffRemove guifg=' .. colors.red)
        return '-' .. require('galaxyline.provider_vcs').diff_remove()
      else
        return '-0 '
      end
    end
  }
}

gls.mid[1] = {
  MidFileName = {
    provider = function()
      if vim.fn.expand '%:p' == 0 then
        return '-'
      end
      if vim.fn.winwidth(0) > 50 then
        return vim.fn.expand '%:~'
      else
        return vim.fn.expand '%:t'
      end
    end,
    highlight = { colors.fg, colors.black },
  }
}

gls.right[1] = {
  RightLspError = {
    provider = function()
      if #vim.tbl_keys(vim.lsp.buf_get_clients()) <= 0 then
         return
      end

      if vim.lsp.diagnostic.get_count(0, 'Error') == 0 then
        vim.api.nvim_command('hi GalaxyRightLspError guifg=' .. colors.fg)
      else
        vim.api.nvim_command('hi GalaxyRightLspError guifg=' .. colors.red)
      end

      return '!' .. vim.lsp.diagnostic.get_count(0, 'Error') .. ' '
    end
  }
}

gls.right[2] = {
  RightLspWarning = {
    provider = function()
      if #vim.tbl_keys(vim.lsp.buf_get_clients()) <= 0 then
         return
      end

      if vim.lsp.diagnostic.get_count(0, 'Warning') == 0 then
        vim.api.nvim_command('hi GalaxyRightLspWarning guifg=' .. colors.fg)
      else
        vim.api.nvim_command('hi GalaxyRightLspWarning guifg=' .. colors.orange)
      end

      return '?' .. vim.lsp.diagnostic.get_count(0, 'Warning') .. ' '
    end
  }
}

gls.right[3] = {
 RightLspInformation = {
   provider = function()
     if #vim.tbl_keys(vim.lsp.buf_get_clients()) <= 0 then
        return
     end

     if vim.lsp.diagnostic.get_count(0, 'Information') == 0 then
        vim.api.nvim_command('hi GalaxyRightLspInformation guifg=' .. colors.fg)
     else
        vim.api.nvim_command('hi GalaxyRightLspInformation guifg=' .. colors.blue)
     end

     return '+' .. vim.lsp.diagnostic.get_count(0, 'Information') .. ' '
   end
 }
}

gls.right[4] = {
  RightLspHint = {
    provider = function()
      if #vim.tbl_keys(vim.lsp.buf_get_clients()) <= 0 then
         return
      end

      if vim.lsp.diagnostic.get_count(0, 'Hint') == 0 then
        vim.api.nvim_command('hi GalaxyRightLspHint guifg=' .. colors.fg)
      else
        vim.api.nvim_command('hi GalaxyRightLspHint guifg=' .. colors.yellow)
      end

      return '-' .. vim.lsp.diagnostic.get_count(0, 'Hint') .. ' '
    end
  }
}

gls.right[5] = {
 RightLspHintSeparator = {
   highlight = { colors.yellow, colors.bg },
   provider = function()
     return ''
   end,
 }
}

gls.right[6] = {
  RightLspClient = {
    highlight = { colors.fg, colors. bg },
    provider = function()
      if #vim.tbl_keys(vim.lsp.buf_get_clients()) >= 1 then
        local lsp_client_name_first = vim.lsp.get_client_by_id(tonumber(vim.inspect(vim.tbl_keys(vim.lsp.buf_get_clients())):match('%d+'))).name:match('%l+')

        if lsp_client_name_first == nil then
          vim.api.nvim_command('hi GalaxyRightLspClient guifg=' .. colors.fg)
          return #vim.tbl_keys(vim.lsp.buf_get_clients()) .. ': '
        else
          vim.api.nvim_command('hi GalaxyRightLspClient guifg=' .. colors.yellow)
          return #vim.tbl_keys(vim.lsp.buf_get_clients()) .. ':' .. lsp_client_name_first .. ' '
        end
      else
        return ' '
      end
    end,
    separator = ' ',
  }
}

gls.right[7] = {
 RightPositionSeparator = {
   provider = function()
     return '  '
   end
 }
}

require ('galaxyline').section.short_line_left = {
  {
    ShortLineLeftBufferType = {
      highlight = 'GalaxyMapperCommon2',
      provider = function ()
        local BufferTypeMap = {
          ['Mundo'] = 'Mundo History',
          ['MundoDiff'] = 'Mundo Diff',
          ['NvimTree'] = 'Nvim Tree',
          ['fugitive'] = 'Fugitive',
          ['fugitiveblame'] = 'Fugitive Blame',
          ['help'] = 'Help',
          ['minimap'] = 'Minimap',
          ['qf'] = 'Quick Fix',
          ['tabman'] = 'Tab Manager',
          ['tagbar'] = 'Tagbar',
          ['toggleterm'] = 'Terminal'
        }
        local name = BufferTypeMap[vim.bo.filetype] or 'Editor'
        return string.format('  %s ', name)
      end,
      separator = ' ',
      separator_highlight = 'GalaxyMapperCommon7'
    }
  },
  {
    ShortLineLeftWindowNumber = {
      highlight = 'GalaxyMapperCommon6',
      provider = function()
        return '  ' .. vim.api.nvim_win_get_number(vim.api.nvim_get_current_win()) .. ' '
      end,
      separator = '',
      separator_highlight = 'GalaxyMapperCommon1'
    }
  }
}

require ('galaxyline').section.short_line_right = {
  {
    ShortLineRightBlank = {
      highlight = 'GalaxyMapperCommon6',
      provider = function()
        if vim.bo.filetype == 'toggleterm' then
          return ' ' .. vim.api.nvim_buf_get_var(0, 'toggle_number') .. ' '
        else
          return '  '
        end
      end,
      separator = '',
      separator_highlight = 'GalaxyMapperCommon1'
    }
  },
  {
    ShortLineRightInformational = {
      highlight = 'GalaxyMapperCommon2',
      provider = function()
        return ' Neovim '
      end,
      separator = '',
      separator_highlight = 'GalaxyMapperCommon7'
    }
  }
}
