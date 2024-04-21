local fzf_lua = require 'fzf-lua'
local actions = require 'fzf-lua.actions'

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
  -- winopts = {
  --   height  = 0.85,             -- window height
  --   width   = 0.80,             -- window width
  --   row     = 0.35,             -- window row position (0=top, 1=bottom)
  --   col     = 0.50,             -- window col position (0=left, 1=right)
  --   preview = {
  --     vertical   = 'down:62%',  -- up|down:size
  --     horizontal = 'right:62%', -- right|left:size
  --   },
  -- },
  buffers = {
    sort_lastused = true,
    ignore_current_buffer = true,
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
      preview = "echo {} | awk '{ print $1 }' | xargs git show | delta",
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

vim.keymap.set({ 'n' }, '<leader>dc', function()
  require "fzf-lua".fzf_exec(function(callback)
    local comments = require("phab").get_comments()
    print(vim.inspect(comments))

    for _, comment in ipairs(comments) do
      callback(comment.author .. ": " .. comment.comment)
    end

    callback()
  end, {
    prompt = "Diff Comments> ",
    previewer = false,
    -- preview = require 'fzf-lua'.shell.raw_preview_action_cmd(function(items) return vim.inspect(items) end),
    fn_transform = function(x)
      return require 'fzf-lua'.make_entry.file(x, { file_icons = true, color_icons = true })
    end,
  })
end, { noremap = true, silent = true })

-- Mtag = function(x, opts)
--   local name, file, text = x:match("([^\t]+)\t([^\t]+)\t(.*)")
--   if not file or not name or not text then return x end
--   text = text:match([[(.*);"]]) or text -- remove ctag comments
--   -- unescape ctags special chars
--   -- '\/' -> '/'
--   -- '\\' -> '\'
--   for _, s in ipairs({ "/", "\\" }) do
--     text = text:gsub([[\]] .. s, s)
--   end
--   local line, tag = text:match("(%d-);?(/.*/)")
--   line = line and #line > 0 and tonumber(line)
--   return ("%s%s: %s %s"):format(
--     M.file(file, opts),
--     not line and "" or ":" .. utils.ansi_codes.green(tostring(line)),
--     utils.ansi_codes.magenta(name),
--     utils.ansi_codes.green(tag)
--   ), line
-- end


-- https://github.com/ibhagwan/fzf-lua/wiki/Advanced#keybind-handlers
vim.keymap.set({ 'n' }, '<leader>cf', function()
    require 'fzf-lua'.fzf_exec(
      "git diff $(git merge-base --fork-point origin/master) --name-only --diff-filter=AM",
      {
        actions = require("fzf-lua").defaults.actions.files,
        preview =
        "echo {} | xargs -n 1 -I {} git diff $(git merge-base --fork-point origin/master) --shortstat --no-prefix -U25 -- {} | delta",
      }
    )
  end,
  {
    noremap = true,
    silent = true,
  })
