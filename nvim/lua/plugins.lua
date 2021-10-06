return require('packer').startup(function()
	use 'wbthomason/packer.nvim'
	use 'AndrewRadev/splitjoin.vim'
	use 'christoomey/vim-tmux-navigator'
	use { 'David-Kunz/treesitter-unit', branch ='main'}
	use 'dense-analysis/ale'
	use 'dhruvasagar/vim-prosession'
	use 'editorconfig/editorconfig-vim'
	use {
		'folke/todo-comments.nvim',
		branch='main',
		config = function() require("todo-comments").setup { } end
	}
	use 'ghifarit53/tokyonight-vim'
	use {
		'glepnir/galaxyline.nvim',
		branch = 'main',
		config = function() require'statusline' end,
		requires = {'kyazdani42/nvim-web-devicons'},
	}
	use {
		'ibhagwan/fzf-lua',
		config = function() require'fzfconfig' end,
		requires = { 'vijaymarupudi/nvim-fzf', 'kyazdani42/nvim-web-devicons' },
	}
	use 'idanarye/vim-merginal'
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
		branch='main',
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
	use 'norcalli/nvim-colorizer.lua'
	use 'nvim-lua/completion-nvim'
	use 'nvim-lua/lsp_extensions.nvim'
	use 'nvim-lua/plenary.nvim'
	use 'nvim-lua/popup.nvim'
	use {
		'nvim-treesitter/nvim-treesitter',
		config = function() require'treesitter' end,
	}
	use 'nvim-treesitter/nvim-treesitter-textobjects'
	use 'nvim-treesitter/playground'
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
end )
