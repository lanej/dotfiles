# Legacy Protobuf profile selection

For an older directory-linked installation, read `.source-code.json` from the consuming repository. With valid installed policy, read [the installed check profile](profile-installed.md) when `languages` includes `protobuf`, or [existing repository checks](profile-uninstalled.md) when it does not. Missing or invalid policy preserves existing gates and grants no new authority; report the gap without provisioning generated tools. Setup or upgrade replaces this selector with the selected profile.
