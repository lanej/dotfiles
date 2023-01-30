local use = require('packer').use

return require('packer').startup({
  function()
    use 'wbthomason/packer.nvim'
    use { 'krivahtoo/silicon.nvim' }
    use {
      'ibhagwan/smartyank.nvim',
      config = function()
        require('smartyank').setup {
          highlight = {
            enabled = true, -- highlight yanked text
            higroup = "IncSearch", -- highlight group of yanked text
            timeout = 2000, -- timeout for clearing the highlight
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
            silent = true, -- false to disable the "n chars copied" echo
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
    use {
      'beauwilliams/focus.nvim',
      config = function()
        vim.api.nvim_command('set wiw=100')
        require('focus').setup({
          signcolumn = false,
          excluded_filetypes = { 'toggleterm', 'terminal', 'nvimtree', 'fzf', 'nofile' },
        })
      end,
    }
    use {
      'nvim-neorg/neorg',
      config = function() require('orgmode') end,
      requires = 'nvim-lua/plenary.nvim',
    }
    use 'dense-analysis/ale'
    use {
      'lanej/vim-prosession',
      requires = 'tpope/vim-obsession',
    }
    use 'editorconfig/editorconfig-vim'
    use {
      'folke/todo-comments.nvim',
      branch = 'main',
      config = function() require('todo-comments').setup {} end,
    }
    --[[ use {
      "~/src/tender",
      requires = { "rktjmp/lush.nvim" },
    } ]]
    use {
      'lanej/tender',
      requires = { 'rktjmp/lush.nvim', 'lewis6991/gitsigns.nvim' },
    }
    use {
      'folke/noice.nvim',
      tag = 'v1.5.1',
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
        vim.api.nvim_command('hi Cursor gui=reverse')
      end,
      requires = {
        "MunifTanjim/nui.nvim",
        "rcarriga/nvim-notify",
        'neovim/nvim-lspconfig',
      }
    }
    use {
      'glepnir/galaxyline.nvim',
      branch = 'main',
      config = function() require 'statusline' end,
      requires = { 'kyazdani42/nvim-web-devicons', 'lanej/tender' },
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
      tag = 'v0.6',
      config = function() require('gitsignsconfig') end,
    }
    use {
      'lukas-reineke/indent-blankline.nvim',
      requires = 'nvim-treesitter/nvim-treesitter',
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
    use 'nvim-lua/popup.nvim'
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
    use 'b3nj5m1n/kommentary'
  end,
  config = {
    display = {
      open_fn = require('packer.util').float,
    },
  },
})
