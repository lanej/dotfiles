local use = require('packer').use

return require('packer').startup({
  function()
    use 'subnut/nvim-ghost.nvim'
    use {
      'epwalsh/obsidian.nvim',
      tag = 'v1.*',
      config = function()
        require('obsidian').setup({
          dir = '~/share/work',
          -- https://github.com/epwalsh/obsidian.nvim/issues/126
          completion = { nvim_cmp = true, },
          daily_notes = { folder = 'dailies' },
        })

        vim.keymap.set("n", "gf", function()
          if require("obsidian").util.cursor_on_markdown_link() then
            return "<cmd>ObsidianFollowLink<CR>"
          else
            return "gf"
          end
        end, { noremap = false, expr = true })
      end,
      after = { 'nvim-treesitter', "nvim-cmp" },
      requires = {
        "nvim-lua/plenary.nvim",
        "hrsh7th/nvim-cmp",
        "ibhagwan/fzf-lua",
      },
    }
    use 'liuchengxu/vista.vim'
    use 'https://git.sr.ht/~soywod/himalaya-vim'
    use { '~/src/phab.nvim' }
    use 'wbthomason/packer.nvim'
    -- use {
    --   'krivahtoo/silicon.nvim',
    --   config = function() require('silicon').setup({ font = 'Hack', theme = '1337' }) end,
    -- }
    use 'IndianBoy42/tree-sitter-just'
    use({
      "iamcco/markdown-preview.nvim",
      run = function() vim.fn["mkdp#util#install"]() end,
    })
    use {
      'gbprod/nord.nvim',
      as = 'nord',
      config = function()
        require("nord").setup({
          transparent = true, -- Enable this to disable setting the background color
          terminal_colors = true,
          diff = { mode = "fg" },
          borders = true,           -- Enable the border between verticaly split windows visible
          errors = { mode = "fg" }, -- Display mode for errors and diagnostics
          styles = { comments = { italic = false } },
          search = { theme = "vim" }, -- theme for highlighting search results
          on_highlights = function(highlights, colors)
            highlights['@symbol'] = { fg = colors.aurora.orange }
            highlights['@string.special.symbol'] = highlights['@symbol']
            highlights['@variable.member'] = { fg = colors.aurora.yellow }
            highlights['@error'] = { sp = colors.aurora.red, undercurl = true }
            highlights['@constant'] = { fg = colors.aurora.purple }
            highlights['@text.uri'] = { underline = true }
            highlights['@error'] = { undercurl = true }
            highlights['@spell.bad'] = { undercurl = true }

            return highlights
          end,
        })
        vim.api.nvim_command('colorscheme nord')
      end,
    }
    -- use({
    --   "Pocco81/true-zen.nvim",
    --   config = function()
    --     require("true-zen").setup {
    --       -- your config goes here
    --       -- or just leave it empty :)
    --     }
    --     local api = vim.api
    --
    --     api.nvim_set_keymap("n", "<leader>zn", ":TZNarrow<CR>", {})
    --     api.nvim_set_keymap("v", "<leader>zn", ":'<,'>TZNarrow<CR>", {})
    --     api.nvim_set_keymap("n", "<leader>zf", ":TZFocus<CR>", {})
    --     api.nvim_set_keymap("n", "<leader>zm", ":TZMinimalist<CR>", {})
    --     api.nvim_set_keymap("n", "<leader>za", ":TZAtaraxis<CR>", {})
    --
    --     -- or
    --     local truezen = require('true-zen')
    --     local keymap = vim.keymap
    --
    --     keymap.set('n', '<leader>zn', function()
    --       local first = 0
    --       local last = vim.api.nvim_buf_line_count(0)
    --       truezen.narrow(first, last)
    --     end, { noremap = true })
    --     keymap.set('v', '<leader>zn', function()
    --       local first = vim.fn.line('v')
    --       local last = vim.fn.line('.')
    --       truezen.narrow(first, last)
    --     end, { noremap = true })
    --     keymap.set('n', '<leader>zf', truezen.focus, { noremap = true })
    --     keymap.set('n', '<leader>zm', truezen.minimalist, { noremap = true })
    --     keymap.set('n', '<leader>za', truezen.ataraxis, { noremap = true })
    --   end,
    -- })
    use {
      'beauwilliams/focus.nvim',
      config = function()
        -- vim.api.nvim_command('set wiw=100')
        require('focus').setup({
          signcolumn = false,
          excluded_filetypes = { 'toggleterm', 'terminal', 'nvimtree', 'fzf', 'nofile' },
        })
      end,
    }
    use({
      'Wansmer/treesj',
      requires = { 'nvim-treesitter' },
      config = function()
        require('treesj').setup({
          use_default_keymaps = false,
        })
        vim.keymap.set('n', 'gJ', require('treesj').join)
        vim.keymap.set('n', 'gS', require('treesj').split)
      end,
    })
    use {
      'ibhagwan/smartyank.nvim',
      config = function()
        require('smartyank').setup {
          highlight = {
            enabled = true,        -- highlight yanked text
            higroup = "IncSearch", -- highlight group of yanked text
            timeout = 2000,        -- timeout for clearing the highlight
          },
          tmux = {
            enabled = true,
            cmd = { 'tmux', 'set-buffer', '-w' },
          },
          clipboard = { enabled = true },
          osc52 = {
            enabled = true,
            ssh_only = true, -- OSC52 yank also in local sessions
            silent = true,   -- false to disable the "n chars copied" echo
          },
        }
      end,
    }
    use {
      'christoomey/vim-tmux-navigator',
      config = function()
        require 'tmux-config'
      end,
    }
    use 'dense-analysis/ale'
    -- TODO: https://github.com/gennaro-tedesco/nvim-possession
    use {
      'lanej/vim-prosession',
      requires = 'tpope/vim-obsession',
    }
    use {
      'folke/todo-comments.nvim',
      branch = 'main',
      config = function()
        require('todo-comments').setup({
          keywords = {
            WTF = { icon = "🤨", color = "warning", alt = { "DAFUQ", "GAH" } },
          }
        })
      end,
    }
    use {
      "smjonas/inc-rename.nvim",
      config = function()
        require("inc_rename").setup()
        vim.keymap.set("n", "<leader>ri", ":IncRename ")
      end,
    }
    use {
      'folke/noice.nvim',
      branch = 'main',
      config = function()
        require("noice").setup({
          routes = {
            { -- filter write messages "xxxL, xxxB"
              filter = {
                event = "msg_show",
                find = "%dL",
              },
              opts = { skip = true },
            },
          },
          popupmenu = { enabled = false },
          cmdline = {
            format = {
              conceal = false
            },
          },
          lsp = {
            override = {
              ["vim.lsp.util.convert_input_to_markdown_lines"] = true,
              ["vim.lsp.util.stylize_markdown"] = true,
              ["cmp.entry.get_documentation"] = true,
            },
          },
          notify = { enabled = true },
          presets = { inc_rename = true },
          views = {
            cmdline_popup = {
              border = {
                style = "none",
                padding = { 2, 3 },
              },
              filter_options = {},
              win_options = {
                winhighlight = "NormalFloat:NormalFloat,FloatBorder:FloatBorder",
              },
            },
          },
        })
      end,
      requires = { 'MunifTanjim/nui.nvim', 'rcarriga/nvim-notify', 'neovim/nvim-lspconfig' },
    }
    use {
      'nvim-lualine/lualine.nvim',
      requires = { 'kyazdani42/nvim-web-devicons' },
      config = function()
        require('lualine').setup {
          options = {
            icons_enabled = true,
            theme = 'nord',
            component_separators = { left = '', right = '' },
            section_separators = { left = '', right = '' },
            disabled_filetypes = {
              statusline = {},
              winbar = {},
            },
            ignore_focus = {},
            always_divide_middle = true,
            globalstatus = false,
            refresh = {
              statusline = 1000,
              tabline = 1000,
              winbar = 1000,
            }
          },
          sections = {
            lualine_a = { 'mode' },
            lualine_b = { 'branch', "diff", },
            lualine_c = {
              { 'filetype', jcon_only = true },
              { 'filename', path = 1 },
            },
            lualine_x = {
              { 'diagnostics', sources = { 'nvim_lsp', 'ale' } },
              {
                require("noice").api.status.command.get,
                cond = require("noice").api.status.command.has,
                color = { fg = "#ff9e64" },
              },
              {
                require("noice").api.status.mode.get,
                cond = require("noice").api.status.mode.has,
                color = { fg = "#ff9e64" },
              },
            },
            lualine_y = {},
            lualine_z = {}
          },
          inactive_sections = {
            lualine_a = {},
            lualine_b = {},
            lualine_c = {},
            lualine_x = { 'branch', 'diff' },
            lualine_y = {},
            lualine_z = { { 'filename', path = 1 }, { 'filetype', icon_only = true } },
          },
        }
      end,
    }
    use {
      'ibhagwan/fzf-lua',
      config = function() require 'fzfconfig' end,
      branch = 'main',
      requires = { 'vijaymarupudi/nvim-fzf', 'kyazdani42/nvim-web-devicons' },
    }
    use 'vim-test/vim-test'
    use 'junegunn/vim-easy-align'
    use {
      'kyazdani42/nvim-tree.lua',
      requires = 'kyazdani42/nvim-web-devicons',
      config = function() require 'nvim-tree-config' end,
    }
    use {
      'lewis6991/gitsigns.nvim',
      requires = { 'nvim-lua/plenary.nvim' },
      -- tag = 'release',
      config = function() require('gitsignsconfig') end,
    }
    use {
      'lukas-reineke/indent-blankline.nvim',
      requires = 'nvim-treesitter/nvim-treesitter',
      config = function()
        require("indent_blankline").setup {
          show_end_of_line = true,
          show_current_context = true,
          show_current_context_start = true,
        }
      end,
    }
    use {
      'ludovicchabant/vim-gutentags',
      config = function()
        vim.g.markdown_fenced_languages = { 'html', 'python', 'bash=sh', 'ruby', 'go' }
        vim.g.gutentags_enabled = 1
        vim.g.gutentags_exclude_filetypes = { 'gitcommit', 'gitrebase' }
        vim.g.gutentags_generate_on_empty_buffer = 0
        vim.g.gutentags_ctags_exclude = { '.eggs', '.mypy_cache', 'venv', 'tags', 'tags.temp', '.ijwb', 'bazel-*', }
        vim.g.gutentags_project_info = {}
      end,
    }
    use {
      'neovim/nvim-lspconfig',
      config = function() require('lsp') end,
      requires = {
        'hrsh7th/cmp-buffer',
        'hrsh7th/cmp-path',
        'hrsh7th/cmp-cmdline',
        'hrsh7th/nvim-cmp',
        'hrsh7th/cmp-nvim-lsp',
        'hrsh7th/cmp-vsnip',
        'andersevenrud/cmp-tmux',
        'hrsh7th/vim-vsnip',
        'simrat39/rust-tools.nvim',
        'kyazdani42/nvim-web-devicons',
        'onsails/lspkind.nvim',
      },
    }
    use {
      'glepnir/lspsaga.nvim',
      branch = 'main',
      requires = 'neovim/nvim-lspconfig',
      config = function() require('lspsagaconfig') end,
    }
    use {
      'folke/trouble.nvim',
      requires = 'kyazdani42/nvim-web-devicons',
      config = function() require 'troubleconfig' end,
    }
    use { 'norcalli/nvim-colorizer.lua', requires = 'nvim-treesitter/nvim-treesitter' }
    use 'nvim-lua/popup.nvim'
    use { 'nvim-treesitter/nvim-treesitter', config = function() require 'treesitter' end }
    use { 'nvim-treesitter/nvim-treesitter-textobjects', requires = 'nvim-treesitter/nvim-treesitter' }
    use { 'nvim-treesitter/playground', requires = 'nvim-treesitter/nvim-treesitter' }
    use { 'phaazon/hop.nvim', config = function() require 'hopconfig' end }
    use 'tpope/vim-dotenv'
    use 'tpope/vim-fugitive'
    use 'tpope/vim-eunuch'
    use 'tpope/vim-surround'
    use 'tpope/vim-repeat'
    use {
      'numToStr/Comment.nvim',
      config = function()
        require('Comment').setup()
      end
    }
    use 'RRethy/vim-illuminate'
    use "sindrets/diffview.nvim"
    use 'mbbill/undotree'
  end,
  config = {
    autoremove = true,
    display = { open_fn = require('packer.util').float },
  },
})
