local fzf_lua = require 'fzf-lua'
local actions = require 'fzf-lua.actions'
local utils = require "fzf-lua.utils"
local path = require "fzf-lua.path"

local action_test = function(selected, opts)
  if #selected == 1 then
    actions.default(selected, opts)
    return
  end

  local qf_list = {}
  for i = 1, #selected do
    local file = path.entry_to_file(selected[i], opts)
    local text = selected[i]:match(":%d+:%d?%d?%d?%d?:?(.*)$")
    table.insert(qf_list, {
      filename = file.bufname or file.path,
      lnum = file.line,
      col = file.col,
      text = text,
    })
  end
  if is_loclist then
    vim.fn.setloclist(0, qf_list)
    vim.cmd "Trouble loclist"
  else
    vim.fn.setqflist(qf_list)
    vim.cmd ":Trouble quickfix"
  end
end

-- TODO: git diff --cached

require('fzf-lua').setup {
  keymap = {
    builtin = {
      ['<C-f>'] = 'toggle-fullscreen',
      ['<C-h>'] = 'toggle-preview',
      ['<C-r>'] = 'toggle-preview-cw',
      ['<C-j>'] = 'half-page-down',
      ['<C-k>'] = 'half-page-up',
    },
    fzf = {
      ['ctrl-b'] = 'toggle-all',
    },
  },
  --[[ actions = {
    files = {
      ['default'] = action_test,
    },
  }, ]]
  winopts = {
    preview = {
      flip_columns = 180, -- #cols to switch to horizontal on flex
    },
  },
  git = {
    branches = {
      prompt = 'Branches❯ ',
      cmd = 'git for-each-ref --format=\'%(refname:short)\' --sort=-committerdate refs/heads/ | grep -v \'phabricator\'',
      preview = 'git diff --stat --summary --color -p "$(git merge-base --fork-point origin/master)"...{} | delta',
      actions = {
        ['default'] = { actions.git_switch, function(_) vim.cmd('ProsessionReset') end },
      },
    },
    commits = {
      preview = 'echo {} | awk \'{ print $1 }\' | xargs git show | delta',
      actions = {
        ['default'] = actions.git_buf_edit,
        ['ctrl-s'] = actions.git_buf_split,
        ['ctrl-v'] = actions.git_buf_vsplit,
        ['ctrl-t'] = actions.git_buf_tabedit,
        ['ctrl-c'] = actions.git_checkout,
      },
    },
  },
}

-- Registers (paste register or apply macro)
local extract_register_from = function(result)
  -- `selected[1]` is going to be "[2] contents of register 2"
  return result:match('^%[(.)%]')
end

vim.keymap.set('n', '<leader>rp', function()
  fzf_lua.registers({
    actions = {
      ['default'] = function(selected)
        local register = extract_register_from(selected[1])
        vim.cmd('normal "' .. register .. 'p')
      end,
      ['@'] = function(selected)
        local register = extract_register_from(selected[1])
        vim.cmd('normal @' .. register)
      end,
    },
  })
end, {
  desc = 'fzf_lua.registers',
})

vim.api.nvim_set_keymap('n', '<leader>aw', '<cmd>lua require("fzf-lua").grep_cword()<CR>', {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap('n', '<leader>ag', '<cmd>lua require("fzf-lua").grep()<CR>', {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap('n', '<leader>ac', '<cmd>lua require("fzf-lua").commands()<CR>', {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap('n', '<leader>ab', '<cmd>lua require("fzf-lua").builtin()<CR>', {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap('n', '<leader>al', '<cmd>lua require("fzf-lua").lines()<CR>', {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap('n', '<leader>az', '<cmd>lua require("fzf-lua").live_grep_resume()<CR>', {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap('n', '<leader>aa', '<cmd>lua require("fzf-lua").grep()<CR>', {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap('n', '<leader>at', '<cmd>lua require("fzf-lua").tags()<CR>', {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap('n', '<leader>f', '<cmd>lua require("fzf-lua").files()<CR>', {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap('n', '<leader>af',
  '<cmd>lua require("fzf-lua").files({ cwd = vim.fn.expand(\'%:p:h\') })<CR>',
  {
    noremap = true,
    silent = true,
  })
vim.api.nvim_set_keymap('n', '<leader>rr', '<cmd>lua require("fzf-lua").command_history()<CR>', {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap('n', '<leader>rf', '<cmd>lua require("fzf-lua").oldfiles()<CR>', {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap('n', '<leader>bl', '<cmd>lua require("fzf-lua").grep_curbuf()<CR>', {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap('n', '<leader>bt', '<cmd>lua require("fzf-lua").btags()<CR>', {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap('n', '<leader>bc', '<cmd>lua require("fzf-lua").git_bcommits()<CR>', {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap('n', '<leader>gf', '<cmd>lua require("fzf-lua").git_files()<CR>', {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap('n', '<leader>sf', '<cmd>lua require("fzf-lua").git_status()<CR>', {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap('n', '<leader>qf', '<cmd>lua require("fzf-lua").quickfix()<CR>', {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap('n', '<leader>bb', '<cmd>lua require("fzf-lua").buffers()<CR>', {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap('n', '<leader>gc', '<cmd>lua require("fzf-lua").git_commits()<CR>', {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap('n', '<leader>bp', '<cmd>lua require("fzf-lua").git_branches()<CR>', {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap('n', '<leader>bs', '<cmd>lua require("fzf-lua").lsp_document_symbols()<CR>', {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap('n', '<leader>as', '<cmd>lua require("fzf-lua").lsp_workspace_symbols()<CR>', {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap('n', '<leader>ss', '<cmd>lua require("fzf-lua").spell_suggest()<CR>', {
  noremap = true,
  silent = true,
})
vim.api.nvim_set_keymap('n', '<leader>j', '<cmd>lua require("fzf-lua").jumps()<CR>', {
  noremap = true,
  silent = true,
})

-- https://github.com/ibhagwan/fzf-lua/wiki/Advanced#keybind-handlers
vim.api.nvim_set_keymap('n', '<leader>cf', '<cmd>lua require("fzf-lua").files({ cmd = "git diff $(git merge-base --fork-point origin/master) --name-only", preview = "echo {} | xargs -n 1 -I {} git diff $(git merge-base --fork-point origin/master) --shortstat --no-prefix -U25 -- {} | delta", actions = require("fzf-lua").defaults.actions.files })<CR>', {
  noremap = true,
  silent = true,
})
