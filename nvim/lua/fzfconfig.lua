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
  winopts = {
    border = 'single',
    preview = {
      flip_columns = 120, -- #cols to switch to horizontal on flex
    }
  },
  lsp = {
    code_actions = {
      -- prompt           = 'Code Actions> ',
      -- async_or_timeout = 5000,
      -- when git-delta is installed use "codeaction_native" for beautiful diffs
      -- try it out with `:FzfLua lsp_code_actions previewer=codeaction_native`
      -- scroll up to `previewers.codeaction{_native}` for more previewer options
      previewer = "codeaction_native",
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

vim.keymap.set('n', '<leader>aw', function() require("fzf-lua").grep_cword() end, { noremap = true, silent = true })
vim.keymap.set('n', '<leader>ag', function() require("fzf-lua").grep() end, { noremap = true, silent = true })
vim.keymap.set({ 'n', 'v' }, '<leader>ac', function() require("fzf-lua").commands() end,
  { noremap = true, silent = true })
vim.keymap.set('n', '<leader>ab', function() require("fzf-lua").builtin() end, { noremap = true, silent = true })
vim.keymap.set('n', '<leader>al', function() require("fzf-lua").lines() end, { noremap = true, silent = true })
vim.keymap.set('n', '<leader>az', function() require("fzf-lua").live_grep_resume() end, { noremap = true, silent = true })
vim.keymap.set('n', '<leader>aa', function() require("fzf-lua").grep() end, { noremap = true, silent = true })
vim.keymap.set('n', '<leader>at', function() require("fzf-lua").tags() end, { noremap = true, silent = true })
vim.keymap.set('n', '<leader>ff', function() require("fzf-lua").files() end, { noremap = true, silent = true })
vim.keymap.set('n', '<leader>af', function() require("fzf-lua").files({ cwd = vim.fn.expand('%:p:h') }) end,
  { noremap = true, silent = true })
vim.keymap.set('n', '<leader>rr', function() require("fzf-lua").command_history() end, { noremap = true, silent = true })
vim.keymap.set('n', '<leader>rf', function() require("fzf-lua").oldfiles() end, { noremap = true, silent = true })
vim.keymap.set('n', '<leader>bl', function() require("fzf-lua").blines() end, {
  noremap = true,
  silent = true,
})
vim.keymap.set('n', '<leader>bt', function() require("fzf-lua").btags() end, { noremap = true, silent = true })
vim.keymap.set('n', '<leader>bc', function() require("fzf-lua").git_bcommits() end, { noremap = true, silent = true })
vim.keymap.set('n', '<leader>gf', function() require("fzf-lua").git_files() end, { noremap = true, silent = true })
vim.keymap.set('n', '<leader>sf', function() require("fzf-lua").git_status() end, { noremap = true, silent = true })
vim.keymap.set('n', '<leader>qf', function() require("fzf-lua").quickfix() end, { noremap = true, silent = true })
vim.keymap.set('n', '<leader>bb', function() require("fzf-lua").buffers() end, { noremap = true, silent = true })
vim.keymap.set('n', '<leader>gc', function() require("fzf-lua").git_commits() end, { noremap = true, silent = true })
vim.keymap.set('n', '<leader>bp', function() require("fzf-lua").git_branches() end, { noremap = true, silent = true })
vim.keymap.set('n', '<leader>bs', function() require("fzf-lua").lsp_document_symbols() end,
  { noremap = true, silent = true })
vim.keymap.set('n', '<leader>cj', function() require("fzf-lua").lsp_incoming_calls() end,
  { noremap = true, silent = true })
vim.keymap.set('n', '<leader>ck', function() require("fzf-lua").lsp_outgoing_calls() end,
  { noremap = true, silent = true })
vim.keymap.set('n', '<leader>as', function() require("fzf-lua").lsp_workspace_symbols() end,
  { noremap = true, silent = true })
vim.keymap.set('n', '<leader>ss', function() require("fzf-lua").spell_suggest() end, { noremap = true, silent = true })
vim.keymap.set('n', '<leader>jj', function() require("fzf-lua").jumps() end, { noremap = true, silent = true })
vim.keymap.set('n', '<leader>ah', function() require("fzf-lua").help_tags() end, {
  noremap = true,
  silent = true,
})
vim.keymap.set({ 'n', 'v' }, '<leader>ca', function() require("fzf-lua").lsp_code_actions({ pager = false }) end, {
  noremap = true,
  silent = true,
})

vim.keymap.set({ 'n' }, '<leader>dc', function()
  require "fzf-lua".fzf_exec({
    prompt = "Diff Comments> ",
    previewer = false,
    -- preview = require 'fzf-lua'.shell.raw_preview_action_cmd(function(items) return vim.inspect(items) end),
    fn_transform = function(x)
      return require 'fzf-lua'.make_entry.file(x, { file_icons = true, color_icons = true })
    end,
  }, function(callback)
    local comments = require("phab").get_comments()
    print(vim.inspect(comments))

    for _, comment in ipairs(comments) do
      callback(comment.author .. ": " .. comment.comment)
    end

    callback()
  end)
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
    require 'fzf-lua'.files(
      {
        cmd = "git diff $(git merge-base --fork-point origin/master) --name-only --diff-filter=AM",
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
