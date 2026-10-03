.PHONY: fmt check-fmt install

fmt:
	golangci-lint run --fix ./...
	gofmt -w *.go

check-fmt:
	@files=$$(gofmt -l *.go) || exit $$?; \
	if [ -n "$$files" ]; then \
		printf 'Run make fmt to format:\n%s\n' "$$files"; \
		exit 1; \
	fi
	golangci-lint run ./...

install:
	go run . install --config ./config.json
