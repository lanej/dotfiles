local use = require("packer").use

return require("packer").startup({
  function()
    use "wbthomason/packer.nvim"
    use {
      "christoomey/vim-tmux-navigator",
      config = function() require "tmux-config" end,
    }
    use "hrsh7th/cmp-nvim-lsp"
    use "hrsh7th/cmp-buffer"
    use "hrsh7th/cmp-path"
    use "hrsh7th/cmp-vsnip"
    use "hrsh7th/vim-vsnip"
    use {
      "hrsh7th/nvim-cmp",
      config = function() require "completion" end,
      requires = {
        "hrsh7th/cmp-nvim-lsp",
        "hrsh7th/cmp-buffer",
        "hrsh7th/cmp-path",
        "hrsh7th/cmp-vsnip",
      },
    }
    use {
      "David-Kunz/treesitter-unit",
      branch = "main",
    }
    use "dense-analysis/ale"
    use {
      "dhruvasagar/vim-prosession",
      requires = "tpope/vim-obsession",
    }
    use "editorconfig/editorconfig-vim"
    use {
      "folke/todo-comments.nvim",
      branch = "main",
      config = function() require("todo-comments").setup {} end,
    }
    use {
      "folke/tokyonight.nvim",
      config = function() require "tokyonight-config" end,
    }
    use {
      "lanej/tender",
      requires = { "rktjmp/lush.nvim" },
    }
    use {
      "glepnir/galaxyline.nvim",
      branch = "main",
      config = function() require "statusline" end,
      requires = { "kyazdani42/nvim-web-devicons", "lanej/tender" },
    }
    use {
      "ibhagwan/fzf-lua",
      config = function() require "fzfconfig" end,
      requires = { "vijaymarupudi/nvim-fzf", "kyazdani42/nvim-web-devicons" },
    }
    use "rktjmp/lush.nvim"
    use "janko-m/vim-test"
    use "junegunn/vim-easy-align"
    use {
      "kyazdani42/nvim-tree.lua",
      requires = "kyazdani42/nvim-web-devicons",
      config = function()
        require"nvim-tree".setup {};
        require "nvim-tree-config"
      end,
    }
    use "kyazdani42/nvim-web-devicons"
    use "lanej/vim-phab"
    use {
      "lewis6991/gitsigns.nvim",
      branch = "main",
      config = function() require("gitsigns").setup() end,
    }
    use "ludovicchabant/vim-gutentags"
    use {
      "lukas-reineke/indent-blankline.nvim",
      requires = "nvim-treesitter/nvim-treesitter",
    }
    use {
      "neovim/nvim-lspconfig",
      requires = "nvim-lua/lsp_extensions.nvim",
      config = function() require("lsp") end,
    }
    use {
      'glepnir/lspsaga.nvim',
      requires = 'neovim/nvim-lspconfig',
      config = function() require("lspsagaconfig") end,
    }
    use {
      "norcalli/nvim-colorizer.lua",
      requires = "nvim-treesitter/nvim-treesitter",
    }
    use { "nvim-lua/lsp_extensions.nvim" }
    use "nvim-lua/plenary.nvim"
    use "nvim-lua/popup.nvim"
    use {
      "nvim-treesitter/nvim-treesitter",
      config = function() require "treesitter" end,
    }
    use {
      "nvim-treesitter/nvim-treesitter-textobjects",
      requires = "nvim-treesitter/nvim-treesitter",
    }
    use {
      "nvim-treesitter/playground",
      requires = "nvim-treesitter/nvim-treesitter",
    }
    use {
      "phaazon/hop.nvim",
      config = function() require "hopconfig" end,
    }
    use "scrooloose/nerdcommenter"
    use "tpope/vim-dotenv"
    use "tpope/vim-eunuch"
    use "tpope/vim-fugitive"
    use "tpope/vim-markdown"
    use "tpope/vim-obsession"
    use "tpope/vim-rhubarb"
    use "tpope/vim-surround"
    use {
      "https://gitlab.com/yorickpeterse/nvim-window.git",
      config = function() require "nvim-window-config" end,
    }
    --use {
      --"romgrk/nvim-treesitter-context",
      --requires = "nvim-lua/lsp_extensions.nvim",
    --}
    -- https://github.com/b3nj5m1n/kommentary
  end,
  config = {
    display = {
      open_fn = require("packer.util").float,
    },
  },
})
