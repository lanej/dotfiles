#!/usr/bin/env python3
"""Run the headless bootstrap entrypoint; plugin download APIs are fixtures."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile


def main():
    root = Path(__file__).resolve().parents[1]
    nvim = shutil.which("nvim")
    assert nvim, "Install Neovim before running this detector."
    with tempfile.TemporaryDirectory(prefix="bootstrap-nvim-test-") as temporary:
        home = Path(temporary)
        checkout = home / ".files"
        for name in ("bootstrap.sh", "scripts/bootstrap-nvim.lua"):
            target = checkout / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / name, target)
        config = home / ".config/nvim"
        config.mkdir(parents=True)
        lock = checkout / "nvim/lazy-lock.json"
        lock.parent.mkdir()
        lock.write_text("{}\n")
        (config / "init.lua").write_text(r'''
local function saved(name)
  vim.fn.writefile({ "installed" }, vim.env.HOME .. "/" .. name)
end
local plugin = { _ = { installed = false } }
package.preload["lazy"] = function()
  return { install = function()
    plugin._.installed = true
    saved("plugin")
    vim.fn.writefile({ "changed" }, vim.env.DOTFILES_NVIM_BOOTSTRAP_LOCK)
  end }
end
package.preload["lazy.core.config"] = function() return { plugins = { fixture = plugin } } end
package.preload["lazy.core.plugin"] = function() return { has_errors = function() return false end } end
package.preload["treesitter"] = function() return {} end
package.preload["treesitter-parsers"] = function() return { "lua" } end
local parsed = false
package.preload["nvim-treesitter"] = function()
  return { install = function()
    vim.defer_fn(function() parsed = true; saved("parser") end, 100)
    return { pwait = function(_, timeout)
      return vim.wait(timeout, function() return parsed end), parsed
    end }
  end }
end
vim.treesitter.language.add = function() return parsed end
local installed, installing = false, false
local server_package = {
  name = "fixture",
  is_installed = function() return installed end,
  is_installing = function() return installing end,
  install = function()
    installing = true
    vim.defer_fn(function()
      installed, installing = true, false
      saved("language-server")
    end, 100)
  end,
}
package.preload["mason-registry"] = function()
  return {
    refresh = function(callback) vim.defer_fn(function() callback(true) end, 100) end,
    get_package = function() return server_package end,
  }
end
package.preload["mason-lspconfig.mappings"] = function()
  return { get_mason_map = function() return { lspconfig_to_package = { fixture = "fixture" } } end }
end
package.preload["mason-lspconfig.settings"] = function()
  return { current = { ensure_installed = { "fixture" } } }
end
package.preload["mason-core.package"] = function() return { Parse = function(name) return name end } end
''')
        binary = home / "bin"
        binary.mkdir()
        (binary / "nvim").symlink_to(nvim)
        env = dict(os.environ, HOME=str(home), PATH=f"{binary}:/usr/bin:/bin", BASH_ENV="/dev/null")
        result = subprocess.run(
            ["/bin/bash", "-c", 'source "$1"; setup_neovim', "bash", str(checkout / "bootstrap.sh")],
            env=env, capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert (home / "plugin").read_text() == "installed\n"
        assert (home / "parser").read_text() == "installed\n"
        assert (home / "language-server").read_text() == "installed\n"
        assert lock.read_text() == "{}\n", "Bootstrap modified the checked-in plugin lockfile."
        print("PASS: headless bootstrap finishes plugin, parser, and language-server installation.")


if __name__ == "__main__":
    main()
