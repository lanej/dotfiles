# Bedrock router

The router is maintained in [lanej/bedrock-router](https://github.com/lanej/bedrock-router), with its own CI and versioned releases.

```sh
git clone https://github.com/lanej/bedrock-router.git ~/src/bedrock-router
cd ~/src/bedrock-router
go run . install --config ./config.json --keep-env
```

The installed binary, configuration, and session database remain under `~/.codex/bedrock-router`. Moving the source checkout does not require restarting the service. Personal shell shortcuts, including `cxd`, remain in dotfiles.
