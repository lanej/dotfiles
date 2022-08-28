local use = require('packer').use

return require('packer').startup({
  function()
    use 'wbthomason/packer.nvim'
    use {
      'christoomey/vim-tmux-navigator',
      config = function() require 'tmux-config' end,
    }
    use {
      'lanej/vim-phabricator',
      requires = {'tpope/vim-fugitive'},
    }
    use {
      'beauwilliams/focus.nvim',
      config = function()
        require('focus').setup({
          excluded_filetypes = {'toggleterm', 'terminal', 'nvimtree', 'fzf', 'nofile'},
        })
      end,
    }
    use {
      'ms-jpq/coq_nvim',
      branch = 'coq',
    }
    use {
      'ms-jpq/coq.artifacts',
      branch = 'artifacts',
    }
    use {
      'nvim-neorg/neorg',
      config = function() require('orgmode') end,
      requires = 'nvim-lua/plenary.nvim',
    }
    use {
      'David-Kunz/treesitter-unit',
      branch = 'main',
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
      requires = {'rktjmp/lush.nvim'},
    }
    use {
      'glepnir/galaxyline.nvim',
      branch = 'main',
      config = function() require 'statusline' end,
      requires = {'kyazdani42/nvim-web-devicons', 'lanej/tender'},
    }
    use {
      'ibhagwan/fzf-lua',
      config = function() require 'fzfconfig' end,
      branch = 'main',
      requires = {'vijaymarupudi/nvim-fzf', 'kyazdani42/nvim-web-devicons'},
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
      requires = {'nvim-lua/plenary.nvim'},
      tag = 'release',
      config = function() require('gitsigns').setup() end,
    }
    use {
      'lukas-reineke/indent-blankline.nvim',
      requires = 'nvim-treesitter/nvim-treesitter',
    }
    use {
      'neovim/nvim-lspconfig',
      requires = 'nvim-lua/lsp_extensions.nvim',
      config = function() require('lsp') end,
    }
    use({
      'glepnir/lspsaga.nvim',
      branch = 'main',
      requires = 'neovim/nvim-lspconfig',
      config = function() require('lspsagaconfig') end,
    })
    use 'folke/lsp-colors.nvim'
    use {
      'folke/trouble.nvim',
      requires = 'kyazdani42/nvim-web-devicons',
      config = function() require 'troubleconfig' end,
    }
    use {
      'norcalli/nvim-colorizer.lua',
      requires = 'nvim-treesitter/nvim-treesitter',
    }
    use {'nvim-lua/lsp_extensions.nvim'}
    use 'nvim-lua/popup.nvim'
    use({
      'nvim-treesitter/nvim-treesitter',
      config = function() require 'treesitter' end,
    })
    use({
      'j-hui/fidget.nvim',
      config = function() require('fidget').setup {} end,
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
