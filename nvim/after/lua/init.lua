vim.cmd('colorscheme nord')

vim.keymap.set('n', 'gf', function()
  if require('obsidian').util.cursor_on_markdown_link() then
    return '<cmd>ObsidianFollowLink<CR>'
  else
    return 'gf'
  end
end, { noremap = false, expr = true })

vim.api.nvim_create_autocmd({ 'BufEnter' }, {
  pattern = "*.txt",
  command = "NoiceDisable"
})
