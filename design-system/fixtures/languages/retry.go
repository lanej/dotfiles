package retry

import "fmt"

type Policy interface {
    Delay(attempt int) (int, error)
}
type Decision struct { DelayMS int; Retry bool }

func Decide(p Policy, n int) (Decision, error) {
    ms, err := p.Delay(n)
    if err != nil {
        return Decision{Retry: false}, fmt.Errorf("retry: %w", err)
    }
    return Decision{DelayMS: ms, Retry: true}, nil
}
