# MenuBar Stats

This preset saves the CPU, memory, disk, network and GPU display settings, their combined-window order, and the application appearance. Bluetooth remains disabled. The battery module is explicitly disabled (`moduleStatus = 2`, `showInMenuBar = 0`); deleting its preferences would let it use its defaults again.

MenuBar Stats 3.9 on this Mac running macOS 27.2.1 crashed in `mbsBATTERY` when inserting a missing `Condition` value into a dictionary. Disabling the module allowed the app to launch. This is a workaround for that observed crash; it does not repair the battery module.

Quit MenuBar Stats, then restore from this checkout:

```sh
make menubar-stats
open -a "MenuBar Stats"
```

The target is explicit and is not included in routine setup. It checks that the application is closed, merges the preset into the shared preferences through macOS `defaults`, and verifies the saved result. Existing preferences are exported to an owner-only `.backup-*.plist` file beside the original before writing. The merge retains unlisted keys, including device settings and application metadata. A failed restore may leave a partial or unconfirmed change; retain the printed backup path.

The preset excludes device identifiers, registration metadata, launch history and widget state. Do not symlink the live preference plist into the repository. To customize the portable settings, edit `settings.plist` and run the target with MenuBar Stats closed.

To restore a backup, quit MenuBar Stats and substitute the printed backup filename:

```sh
defaults import "$HOME/Library/Group Containers/3EYN7PPTPF.com.fabriceleyne.menubarstats/Library/Preferences/3EYN7PPTPF.com.fabriceleyne.menubarstats" "/path/to/backup.plist"
```

`MENUBAR_STATS_PREFS` overrides the preferences path without the `.plist` suffix, allowing the target to be exercised against a disposable file. The target requires macOS and Python 3.
