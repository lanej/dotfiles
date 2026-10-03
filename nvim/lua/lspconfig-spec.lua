-- Language server defaults, overrides, and activation.
return {
	"neovim/nvim-lspconfig",
	dependencies = {
		"saghen/blink.cmp",
		"nvim-tree/nvim-web-devicons",
		"onsails/lspkind.nvim",
		"Decodetalkers/csharpls-extended-lsp.nvim",
		"williamboman/mason-lspconfig.nvim",
	},
	opts = {
		servers = {
			lua_ls = {
				settings = {
					Lua = {
						hint = {
							enable = true,
							enableType = true,
							enableFunction = true,
						},
					},
				},
				capabilities = {
					textDocument = {
						semanticTokens = {
							full = false,
							delta = false,
						},
					},
				},
			},
			csharp_ls = {
				capabilities = {
					textDocument = {
						semanticTokens = {
							full = false,
							delta = false,
						},
					},
				},
				settings = {
					csharp = {
						enableRoslynAnalyzers = true,
						enableEditorConfigSupport = true,
						enableMsBuildLoadProjectsOnDemand = true,
						enableImportCompletion = true,
						enableFormatOnType = true,
						enableFormatOnSave = true,
					},
				},
			},
			ts_ls = {
				settings = {
					completions = {
						completeFunctionCalls = true,
					},
					typescript = {
						inlayHints = {
							includeInlayParameterNameHints = "all",
							includeInlayParameterNameHintsWhenArgumentMatchesName = false,
							includeInlayFunctionParameterTypeHints = true,
							includeInlayVariableTypeHints = true,
							includeInlayVariableTypeHintsWhenTypeMatchesName = false,
							includeInlayPropertyDeclarationTypeHints = true,
							includeInlayFunctionLikeReturnTypeHints = true,
							includeInlayEnumMemberValueHints = true,
						},
					},
					javascript = {
						inlayHints = {
							includeInlayParameterNameHints = "all",
							includeInlayParameterNameHintsWhenArgumentMatchesName = false,
							includeInlayFunctionParameterTypeHints = true,
							includeInlayVariableTypeHints = true,
							includeInlayVariableTypeHintsWhenTypeMatchesName = false,
							includeInlayPropertyDeclarationTypeHints = true,
							includeInlayFunctionLikeReturnTypeHints = true,
							includeInlayEnumMemberValueHints = true,
						},
					},
				},
				capabilities = {
					textDocument = {
						semanticTokens = {
							full = false,
							delta = false,
						},
					},
				},
			},
			gopls = {
				hints = {
					rangeVariableTypes = true,
					parameterNames = true,
					constantValues = true,
					assignVariableTypes = true,
					compositeLiteralFields = true,
					compositeLiteralTypes = true,
					functionTypeParameters = true,
				},
			},
			ruby_lsp = {},
			jsonls = {
				settings = {
					json = {
						format = {
							enable = true,
						},
					},
					validate = { enable = true },
				},
			},
			-- marksman = {},
			-- 				pkm_lsp = {
			-- 					cmd = { "pkm", "lsp" },
			-- 					filetypes = { "markdown" },
			-- 					autostart = true,
			-- 					single_file_support = true,
			-- 					root_dir = function(fname)
			-- 						return vim.fs.root(fname, { ".lancedb", ".git" }) or vim.fn.getcwd()
			-- 					end,
			-- 					init_options = {
			-- 						dbPath = ".lancedb",
			-- 						debounceMs = 1000,
			-- 					},
			-- 					settings = {},
			-- 				},
			pylsp = {},
			html = {},
			yamlls = {},
			bashls = {
				filetypes = { "sh", "zsh", "bash" },
			},
			zls = {},
			tinymist = {},
			texlab = {},
			lemminx = {
				-- XML Language Server
				init_options = {
					settings = {
						xml = {
							format = {
								enabled = true,
								splitAttributes = false,
								joinCDATALines = false,
								joinCommentLines = false,
								joinContentLines = false,
								spaceBeforeEmptyCloseTag = true,
								preservedNewlines = 1,
							},
							completion = {
								autoCloseTags = true,
							},
							validation = {
								enabled = true,
							},
							symbols = {
								enabled = true,
							},
						},
					},
				},
			},
		},
		opts = {
			inlay_hints = { enabled = true },
		},
	},
	config = function(_, opts)
		require("lsp") -- NOTE: this is requried to get keybinds for fallback registration
		for server, config in pairs(opts.servers) do
			-- passing config.capabilities to blink.cmp merges with the capabilities in your
			-- `opts[server].capabilities, if you've defined it
			config.capabilities = require("blink.cmp").get_lsp_capabilities(config.capabilities)
			vim.lsp.config(server, config)

			-- Skip auto-enabling markdown LSPs - our autocmd handles them conditionally
			if server ~= "marksman" then
				vim.lsp.enable(server)
			end
		end

		-- Capture server configs for autocmd closure
		-- 			local pkm_config = opts.servers.pkm_lsp
		-- 			local marksman_config = opts.servers.marksman
		--
		-- 			-- Smart LSP selection: pkm_lsp in PKM workspaces, Marksman elsewhere
		-- 			vim.api.nvim_create_autocmd("FileType", {
		-- 				pattern = "markdown",
		-- 				callback = function(args)
		-- 					local root_dir = vim.fs.root(args.file, { ".lancedb", ".git", ".marksman.toml" })
		-- 					local is_pkm_workspace = root_dir and vim.fn.isdirectory(root_dir .. "/.lancedb") == 1
		--
		-- 					if is_pkm_workspace and pkm_config then
		-- 						-- PKM workspace: use pkm_lsp for wikilink completions
		-- 						local config = vim.tbl_deep_extend("force", {
		-- 							name = "pkm_lsp",
		-- 							cmd = pkm_config.cmd,
		-- 							filetypes = pkm_config.filetypes,
		-- 							root_dir = root_dir,
		-- 							init_options = pkm_config.init_options,
		-- 							settings = pkm_config.settings,
		-- 						}, { capabilities = require("blink.cmp").get_lsp_capabilities(pkm_config.capabilities) })
		--
		-- 						vim.lsp.start(config)
		-- 					elseif marksman_config and root_dir then
		-- 						-- Regular markdown: use Marksman
		-- 						local config = vim.tbl_deep_extend("force", {
		-- 							name = "marksman",
		-- 							cmd = marksman_config.cmd or { "marksman", "server" },
		-- 							filetypes = { "markdown" },
		-- 							root_dir = root_dir,
		-- 						}, {
		-- 							capabilities = require("blink.cmp").get_lsp_capabilities(marksman_config.capabilities),
		-- 						})
		--
		-- 						vim.lsp.start(config)
		-- 					end
		-- 				end,
		-- 			})
		-- NOTE: Smart LSP selection for pkm-lsp and Marksman moved to ~/.config/nvim/lua/pkm-lsp.lua (loaded via require)

		require("csharpls_extended").buf_read_cmd_bind()
	end,
}
