local use = require("packer").use

return require("packer").startup({
  function()
    use "wbthomason/packer.nvim"
    use {
      "christoomey/vim-tmux-navigator",
      config = function() require "tmux-config" end,
    }
    use {
      "ms-jpq/coq_nvim",
      branch = "coq",
    }
    use {
      "ms-jpq/coq.artifacts",
      branch = "artifacts",
    }
    --[[ use {
      "nvim-orgmode/orgmode",
      config = function() require("orgmode-treesitter") end,
      requires = "nvim-treesitter/nvim-treesitter",
    } ]]
    use {
      "nvim-neorg/neorg",
      config = function()
        local parser_configs = require('nvim-treesitter.parsers').get_parser_configs()

        -- These two are optional and provide syntax highlighting
        -- for Neorg tables and the @document.meta tag
        parser_configs.norg_meta = {
          install_info = {
            url = "https://github.com/nvim-neorg/tree-sitter-norg-meta",
            files = {
              "src/parser.c",
            },
            branch = "main",
          },
        }

        parser_configs.norg_table = {
          install_info = {
            url = "https://github.com/nvim-neorg/tree-sitter-norg-table",
            files = {
              "src/parser.c",
            },
            branch = "main",
          },
        }

        require('neorg').setup {
          load = {
            ["core.defaults"] = {},
            ["core.norg.dirman"] = {
              config = {
                workspaces = {
                  work = "~/share/notes/work",
                  home = "~/share/notes/home",
                  gtd = "~/share/notes/gtd",
                },
              },
            },
            ["core.norg.concealer"] = {},
            -- ["core.norg.completion"] = {},
            ["core.gtd.base"] = {
              config = {
                workspace = "gtd",
                inbox = "inbox.norg",
              },
            },
            ["core.gtd.ui"] = {},
          },
        }
      end,
      requires = "nvim-lua/plenary.nvim",
    }
    use {
      "ms-jpq/coq.thirdparty",
      branch = "3p",
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
      "lanej/tender",
      requires = {
        "rktjmp/lush.nvim",
      },
    }
    use {
      "glepnir/galaxyline.nvim",
      branch = "main",
      config = function() require "statusline" end,
      requires = {
        "kyazdani42/nvim-web-devicons",
        "lanej/tender",
      },
    }
    use {
      "ibhagwan/fzf-lua",
      config = function() require "fzfconfig" end,
      requires = {
        "vijaymarupudi/nvim-fzf",
        "kyazdani42/nvim-web-devicons",
      },
    }
    use "rktjmp/lush.nvim"
    use "janko-m/vim-test"
    use "junegunn/vim-easy-align"
    use {
      "kyazdani42/nvim-tree.lua",
      requires = "kyazdani42/nvim-web-devicons",
      config = function() require "nvim-tree-config" end,
    }
    use "kyazdani42/nvim-web-devicons"
    use "lanej/vim-phab"
    use {
      "lewis6991/gitsigns.nvim",
      requires = {
        'nvim-lua/plenary.nvim',
      },
      tag = 'release',
      config = function() require("gitsigns").setup() end,
    }
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
      "glepnir/lspsaga.nvim",
      requires = "neovim/nvim-lspconfig",
      config = function() require("lspsagaconfig") end,
    }
    use {
      "norcalli/nvim-colorizer.lua",
      fequires = "nvim-treesitter/nvim-treesitter",
    }
    use {
      "nvim-lua/lsp_extensions.nvim",
    }
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
    use "tpope/vim-dotenv"
    use "tpope/vim-fugitive"
    use "tpope/vim-eunuch"
    use "tpope/vim-markdown"
    use "tpope/vim-obsession"
    use "tpope/vim-surround"
    use {
      "https://gitlab.com/yorickpeterse/nvim-window.git",
      config = function() require "nvim-window-config" end,
    }
    use "b3nj5m1n/kommentary"
  end,
  config = {
    display = {
      open_fn = require("packer.util").float,
    },
  },
})
