local M = {}

-- Configuration with defaults
M.config = {
  remarkable_cli = vim.fn.expand("~/src/remarkable-mcp/bin/remarkable"),
  pandoc_bin = "/opt/homebrew/bin/pandoc",
  default_folder = "", -- empty = root
  temp_dir = vim.fn.stdpath("cache") .. "/remarkable",
  pandoc_options = {
    "--pdf-engine=weasyprint",
  },
  save_pdf_locally = false,
  local_pdf_dir = nil, -- if save_pdf_locally, where to save (nil = same dir as md)
}

-- Setup function for user configuration
function M.setup(opts)
  M.config = vim.tbl_deep_extend("force", M.config, opts or {})

  -- Create temp directory
  vim.fn.mkdir(M.config.temp_dir, "p")
end

-- Main upload function
function M.upload_current_buffer()
  local bufnr = vim.api.nvim_get_current_buf()
  local filepath = vim.api.nvim_buf_get_name(bufnr)

  -- Validate markdown file
  if vim.bo[bufnr].filetype ~= "markdown" then
    vim.notify("Not a markdown file", vim.log.levels.ERROR)
    return
  end

  if filepath == "" or vim.fn.filereadable(filepath) == 0 then
    vim.notify("Buffer not saved to file", vim.log.levels.ERROR)
    return
  end

  -- Save buffer if modified
  if vim.bo[bufnr].modified then
    vim.cmd("write")
  end

  -- Generate PDF path
  local filename = vim.fn.fnamemodify(filepath, ":t:r") -- filename without extension
  local pdf_path

  if M.config.save_pdf_locally and M.config.local_pdf_dir then
    pdf_path = M.config.local_pdf_dir .. "/" .. filename .. ".pdf"
  elseif M.config.save_pdf_locally then
    pdf_path = vim.fn.fnamemodify(filepath, ":p:h") .. "/" .. filename .. ".pdf"
  else
    pdf_path = M.config.temp_dir .. "/" .. filename .. ".pdf"
  end

  -- Build pandoc command
  local pandoc_cmd = {
    M.config.pandoc_bin,
    filepath,
    "-o", pdf_path,
  }
  vim.list_extend(pandoc_cmd, M.config.pandoc_options)

  -- Show progress
  vim.notify("Converting to PDF...", vim.log.levels.INFO)

  -- Run pandoc conversion
  local result = vim.fn.system(pandoc_cmd)
  if vim.v.shell_error ~= 0 then
    vim.notify("Pandoc conversion failed: " .. result, vim.log.levels.ERROR)
    return
  end

  vim.notify("Uploading to reMarkable...", vim.log.levels.INFO)

  -- Build remarkable upload command
  local upload_cmd = {
    M.config.remarkable_cli,
    "upload",
    pdf_path,
  }

  if M.config.default_folder ~= "" then
    table.insert(upload_cmd, "--folder")
    table.insert(upload_cmd, M.config.default_folder)
  end

  -- Run upload
  result = vim.fn.system(upload_cmd)
  if vim.v.shell_error ~= 0 then
    vim.notify("Upload failed: " .. result, vim.log.levels.ERROR)
    return
  end

  vim.notify("Successfully uploaded to reMarkable!", vim.log.levels.INFO)

  -- Clean up temp PDF if configured
  if not M.config.save_pdf_locally then
    vim.fn.delete(pdf_path)
  else
    vim.notify("PDF saved to: " .. pdf_path, vim.log.levels.INFO)
  end
end

-- Interactive upload with folder selection
function M.upload_with_folder()
  vim.ui.input({
    prompt = "Destination folder (empty for root): ",
    default = M.config.default_folder,
  }, function(folder)
    if folder == nil then return end -- user cancelled

    local original_folder = M.config.default_folder
    M.config.default_folder = folder
    M.upload_current_buffer()
    M.config.default_folder = original_folder
  end)
end

return M
