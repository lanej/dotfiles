# Select python check guidance

Read the installed `.source-code.json`, using its `languages` list rather than detected languages, skill selection, or desired TOML settings. When `python` is listed, read [installed profile guidance](profile-installed.md). Otherwise read [guidance without a generated profile](profile-uninstalled.md). Load only the matching reference.

Missing or malformed installed policy does not authorize adding or relaxing checks. Preserve existing repository requirements and resolve the missing configuration before claiming a generated gate is installed. Use the source-code management skill for installation or configuration changes.
