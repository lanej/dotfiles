local use = require('packer').use

return require('packer').startup({
  function()
    use 'wbthomason/packer.nvim'
    --[[ use {
      'krivahtoo/silicon.nvim',
      config = function() require('silicon').setup({ font = 'Hack', theme = '1337' }) end,
    } ]]
    use {
      'gbprod/nord.nvim',
      config = function()
        require("nord").setup({
          transparent = false,      -- Enable this to disable setting the background color
          terminal_colors = true,   -- Configure the colors used when opening a `:terminal` in Neovim
          diff = { mode = "fg" },   -- enables/disables colorful backgrounds when used in diff mode. values : [bg|fg]
          borders = true,           -- Enable the border between verticaly split windows visible
          errors = { mode = "bg" }, -- Display mode for errors and diagnostics
          styles = {
            comments = { italic = true },
          },
        })
      end,
    }
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
          clipboard = {
            enabled = true
          },
          tmux = {
            enabled = true,
            cmd = { 'tmux', 'set-buffer', '-w' }
          },
          osc52 = {
            enabled = true,
            ssh_only = true, -- OSC52 yank also in local sessions
            silent = true,   -- false to disable the "n chars copied" echo
          }
        }
      end
    }
    use {
      'christoomey/vim-tmux-navigator',
      config = function() require 'tmux-config' end,
    }
    use {
      'lanej/vim-phabricator',
      requires = { 'tpope/vim-fugitive' },
    }
    use 'dense-analysis/ale'
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
      'folke/noice.nvim',
      branch = 'main',
      config = function()
        require("noice").setup(
          {
            popupmenu = {
              enabled = false,
            },
            cmdline = {
              format = {
                conceal = false
              },
            },
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
      requires = {
        "MunifTanjim/nui.nvim",
        "rcarriga/nvim-notify",
        'neovim/nvim-lspconfig',
      }
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
            lualine_b = { 'branch', { 'diagnostics', sources = { 'nvim_lsp', 'ale' } } },
            lualine_c = { { 'filename', path = 1 }, { 'filetype', icon_only = true } },
            lualine_x = { "diff" },
            lualine_y = {},
            lualine_z = {}
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
      tag = 'release',
      config = function() require('gitsignsconfig') end,
    }
    use {
      'lukas-reineke/indent-blankline.nvim',
      requires = 'nvim-treesitter/nvim-treesitter',
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
        'hrsh7th/vim-vsnip',
        'simrat39/rust-tools.nvim',
        'kyazdani42/nvim-web-devicons',
        'onsails/lspkind.nvim',
      }
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
    use {
      'norcalli/nvim-colorizer.lua',
      requires = 'nvim-treesitter/nvim-treesitter',
    }
    use({
      'nvim-treesitter/nvim-treesitter',
      config = function() require 'treesitter' end,
    })
    use {
      'nvim-treesitter/nvim-treesitter-textobjects',
      requires = 'nvim-treesitter/nvim-treesitter',
    }
    use {
      'nvim-treesitter/playground',
      requires = 'nvim-treesitter/nvim-treesitter',
    }
    use {
      'phaazon/hop.nvim',
      config = function() require 'hopconfig' end,
    }
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
    use {
      'epwalsh/obsidian.nvim',
      tag = 'v1.*',
      config = function()
        require('obsidian').setup({
          dir = '~/share/work',
          completion = { nvim_cmp = true, },
          daily_notes = { folder = 'dailies' },
        })
      end,
    }
    use 'mbbill/undotree'
  end,
  config = {
    display = {
      open_fn = require('packer.util').float,
    },
  },
})
