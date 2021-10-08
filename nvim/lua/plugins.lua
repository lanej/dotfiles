return require('packer').startup({function()
	use 'wbthomason/packer.nvim'
	use 'AndrewRadev/splitjoin.vim'
	use {
	    	'christoomey/vim-tmux-navigator',
	 	config = function() require'tmux-config' end,
  	}

	use { 
		'David-Kunz/treesitter-unit', 
		branch ='main',
	}
	use 'dense-analysis/ale'
	use {
		'dhruvasagar/vim-prosession',
		requires = 'tpope/vim-obsession',
	}
	use 'editorconfig/editorconfig-vim'
	use {
		'folke/todo-comments.nvim',
		branch='main',
		config = function() require("todo-comments").setup { } end
	}
	use {
		'folke/tokyonight.nvim',
		config = function() require'tokyonight-config' end,
	}
	use {
		'glepnir/galaxyline.nvim',
		branch = 'main',
		config = function() require'statusline' end,
		requires = {'kyazdani42/nvim-web-devicons', 'folke/tokyonight.nvim'},
	}
	use {
		'ibhagwan/fzf-lua',
		config = function() require'fzfconfig' end,
		requires = { 'vijaymarupudi/nvim-fzf', 'kyazdani42/nvim-web-devicons' },
	}
	use 'janko-m/vim-test'
	use 'junegunn/vim-easy-align'
	use {
		'kyazdani42/nvim-tree.lua',
		requires = 'kyazdani42/nvim-web-devicons',
		config = function() require'nvim-tree'.setup {}; require'nvim-tree-config' end
	}
	use 'kyazdani42/nvim-web-devicons'
	use 'lanej/vim-phab'
	use {
		'lewis6991/gitsigns.nvim',
		branch = 'main',
		config = function() require('gitsigns').setup() end,
	}
	use 'ludovicchabant/vim-gutentags'
	use {
		'lukas-reineke/indent-blankline.nvim',
		requires = 'nvim-treesitter/nvim-treesitter',
	}
	use {
		'neovim/nvim-lspconfig',
		config = function() require'lsp' end,
		requires = 'nvim-treesitter/nvim-treesitter',
	}
	use {
		'norcalli/nvim-colorizer.lua',
		requires = 'nvim-treesitter/nvim-treesitter',
	}
	use {
		'nvim-lua/completion-nvim',
		requires = 'neovim/nvim-lspconfig',
	}
	use {
		'nvim-lua/lsp_extensions.nvim',
		requires = 'neovim/nvim-lspconfig',
	}
	use 'nvim-lua/plenary.nvim'
	use 'nvim-lua/popup.nvim'
	use {
		'nvim-treesitter/nvim-treesitter',
		config = function() require'treesitter' end,
	}
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
		config = function() require'hopconfig' end,
	}
	use 'scrooloose/nerdcommenter'
	use 'tpope/vim-dotenv'
	use 'tpope/vim-eunuch'
	use 'tpope/vim-fugitive'
	use 'tpope/vim-markdown'
	use 'tpope/vim-obsession'
	use 'tpope/vim-rhubarb'
	use 'tpope/vim-surround'
	use {
		'https://gitlab.com/yorickpeterse/nvim-window.git',
		config = function() require'nvim-window-config' end,
	}
	--https://github.com/b3nj5m1n/kommentary
end,
	config = {
	  display = {
	    open_fn = require('packer.util').float,
	  }
}})
