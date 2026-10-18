---
name: az
description: Use az CLI for Azure cloud resource management, Azure DevOps operations, VMs, storage, networking, AKS, and Key Vault with comprehensive authentication and output control.
---

# Azure CLI (az)

Standard `az` subcommands work as documented — consult `az <group> --help` rather than memorizing.
This file covers the conventions that keep `az` output usable and the steps that are easy to skip.

## Before anything else

```bash
az account show                       # verify identity AND subscription
az account set --subscription <name>  # multi-subscription tenants silently default wrong
```

A command that "doesn't find" a resource is usually pointed at the wrong subscription, not missing
the resource.

## Output discipline

`az` defaults to verbose JSON. Always pick a format deliberately:

- `-o table` — human review
- `-o tsv` + `--query` — capturing a single value into a shell variable; never parse table output
- `-o json` — feeding another tool

```bash
RESOURCE_ID=$(az resource show --name myapp -g myrg --query "id" -o tsv)
```

`--query` is JMESPath, not jq. The forms worth knowing:

```bash
--query "[?location=='eastus'].name"                  # filter
--query "[].{Name:name, State:powerState}"            # reshape, pairs well with -o table
--query "[0].id"                                      # first element
```

## Long-running and bulk operations

- `--no-wait` on create/delete so the call returns immediately; poll with `az resource wait`.
- Bulk by ID list rather than looping one command per resource:

  ```bash
  az vm start --ids $(az vm list -g myrg --query "[].id" -o tsv)
  ```

## Azure DevOps

`az devops` commands fail confusingly without defaults set. Set them once per session:

```bash
az devops configure --defaults organization=https://dev.azure.com/myorg project=MyProject
```

## Security defaults

- Managed identities over service principals.
- Secrets in Key Vault, never in app settings.
- Soft delete enabled on production Key Vaults.
- Azure RBAC over classic access policies.

## Cost hygiene

`az vm stop` still bills — use `az vm deallocate`. Clean up unused resource groups rather than
individual resources; deleting the group is the reliable teardown.
