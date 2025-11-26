require('gitsigns').setup({
  signs = {
    topdelete = {
      text = '^',
    },
  },
  -- Enable inline diff highlighting by default (word-level only)
  word_diff = true, -- Show word-level diffs by default (toggle with <leader>hd)
  diff_opts = {
    internal = true, -- Use internal diff library for better performance
  },
  -- Don't show deleted lines as virtual text by default (toggle with <leader>hD)
  show_deleted = false,
  -- Automatically set base to origin/HEAD (main/master) on BufEnter
  on_attach = function(bufnr)
    local gitsigns = require('gitsigns')

    -- Get the default branch (origin/HEAD -> origin/main or origin/master)
    local origin_head = vim.fn.systemlist('git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null')[1]
    if origin_head and origin_head ~= '' then
      -- Extract just the branch name (e.g., "refs/remotes/origin/main" -> "origin/main")
      local default_branch = origin_head:match('refs/remotes/(.*)')
      if default_branch then
        -- Get merge base between current branch and default branch
        local merge_base = vim.fn.systemlist(string.format('git merge-base HEAD %s 2>/dev/null', default_branch))[1]
        if merge_base and merge_base ~= '' then
          -- Set base to the merge-base commit
          gitsigns.change_base(merge_base, true) -- true = global (affects all buffers)
        end
      end
    end
  end,
})

-- Set highlights after a delay to ensure they override colorscheme defaults
vim.defer_fn(function()
  -- Disable line-level backgrounds entirely, only show word-level diffs
  -- The gutter signs are sufficient for indicating which lines changed
  vim.api.nvim_set_hl(0, 'GitSignsAddLn', { bg = 'NONE', fg = 'NONE' })
  vim.api.nvim_set_hl(0, 'GitSignsChangeLn', { bg = 'NONE', fg = 'NONE' })
  vim.api.nvim_set_hl(0, 'GitSignsDeleteLn', { bg = 'NONE', fg = 'NONE' })
  vim.api.nvim_set_hl(0, 'GitSignsAdd', { bg = 'NONE', fg = 'NONE' })
  vim.api.nvim_set_hl(0, 'GitSignsChange', { bg = 'NONE', fg = 'NONE' })
  vim.api.nvim_set_hl(0, 'GitSignsDelete', { bg = 'NONE', fg = 'NONE' })

  -- Extremely subtle word-level diff highlighting using Nord palette tints
  -- Base background is nord0 (#2E3440), these are barely-visible tints
  -- Gutter signs already indicate line-level changes, so we focus on word-level precision
  vim.api.nvim_set_hl(0, 'GitSignsAddInline', { bg = '#303740', fg = 'NONE' })       -- Barely-visible green tint
  vim.api.nvim_set_hl(0, 'GitSignsDeleteInline', { bg = '#30363F', fg = 'NONE' })    -- Barely-visible red tint
  vim.api.nvim_set_hl(0, 'GitSignsChangeInline', { bg = '#313740', fg = 'NONE' })    -- Barely-visible yellow tint
end, 100)

vim.keymap.set('n', '<leader>gw', require('gitsigns').stage_buffer, { silent = true, noremap = true })
vim.keymap.set('n', '<leader>gl', require('gitsigns').blame_line, { silent = true, noremap = true })
vim.keymap.set('n', ']c', require('gitsigns').next_hunk, { silent = true, noremap = true })
vim.keymap.set('n', '[c', require('gitsigns').prev_hunk, { silent = true, noremap = true })
vim.keymap.set('n', '<leader>hp', require('gitsigns').preview_hunk, { silent = true, noremap = true })
vim.keymap.set('n', '<leader>hs', require('gitsigns').stage_hunk, { silent = true, noremap = true })
vim.keymap.set('n', '<leader>hr', require('gitsigns').reset_hunk, { silent = true, noremap = true })
vim.keymap.set('n', '<leader>hR', require('gitsigns').reset_buffer, { silent = true, noremap = true })
vim.keymap.set('n', '<leader>hu', require('gitsigns').undo_stage_hunk, { silent = true, noremap = true })
vim.keymap.set('n', '<leader>hU', require('gitsigns').reset_buffer_index, { silent = true, noremap = true })
vim.keymap.set('n', 'vh', require('gitsigns').select_hunk, { silent = true, noremap = true })

-- Toggle inline diff highlighting (shows changes highlighted in buffer)
vim.keymap.set('n', '<leader>hd', require('gitsigns').toggle_word_diff, { silent = true, noremap = true, desc = 'Toggle inline word diff' })
vim.keymap.set('n', '<leader>hD', require('gitsigns').toggle_deleted, { silent = true, noremap = true, desc = 'Toggle deleted lines' })

-- Toggle between comparing against HEAD (uncommitted changes) and merge-base (branch changes)
vim.keymap.set('n', '<leader>gb', function()
  require('gitsigns').change_base(nil, true) -- Reset to default (HEAD/index)
  vim.notify('Gitsigns: comparing against HEAD (uncommitted changes)', vim.log.levels.INFO)
end, { silent = true, noremap = true, desc = 'Compare against HEAD' })

vim.keymap.set('n', '<leader>gB', function()
  local origin_head = vim.fn.systemlist('git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null')[1]
  if origin_head and origin_head ~= '' then
    local default_branch = origin_head:match('refs/remotes/(.*)')
    if default_branch then
      local merge_base = vim.fn.systemlist(string.format('git merge-base HEAD %s 2>/dev/null', default_branch))[1]
      if merge_base and merge_base ~= '' then
        require('gitsigns').change_base(merge_base, true)
        vim.notify('Gitsigns: comparing against ' .. default_branch .. ' (branch changes)', vim.log.levels.INFO)
      end
    end
  end
end, { silent = true, noremap = true, desc = 'Compare against default branch' })
