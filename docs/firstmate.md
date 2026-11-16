# Firstmate retired

Use [Paseo Tasks](paseo-tasks.md) for task ownership, worker conversations and PR maintenance. Firstmate installation, launchers and supervision extensions have been removed. Existing tool switches run retirement cleanup instead of installing it.

Run `make firstmate-retire` to remove only this checkout's Firstmate extension registrations, launcher symlink and Paseo provider. Saved checkouts, task records, sessions, credentials and running processes are retained. The Tasks importer remains available for old work; stop its recorded owner before transferring it. Shared question and model-router modules retain their historical filenames for compatibility.
