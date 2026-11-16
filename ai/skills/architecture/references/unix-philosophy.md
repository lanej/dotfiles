# Unix philosophy

Use these principles as design heuristics within Pragmatic Hexagonal Architecture. For example, a filter can keep its output composable by writing records to standard output and diagnostics to standard error. The PHA contract still determines what its caller must learn if processing stops halfway.

The following rules paraphrase Eric S. Raymond’s *The Art of Unix Programming*.

1. **Modularity:** Build simple components with clean interfaces.
2. **Clarity:** Prefer readable code over clever code.
3. **Composition:** Make programs easy to connect.
4. **Separation:** Keep policy apart from mechanism, and interfaces apart from engines.
5. **Simplicity:** Add complexity only when necessary.
6. **Parsimony:** Build large programs only when smaller solutions cannot work.
7. **Transparency:** Make behavior visible and easy to inspect.
8. **Robustness:** Reliability follows from simplicity and transparency.
9. **Representation:** Put knowledge into data so logic can stay simple.
10. **Least Surprise:** Make interfaces behave as users expect.
11. **Silence:** Produce no output when there's nothing useful to report.
12. **Repair:** Recover where possible; otherwise fail early and clearly.
13. **Economy:** Prioritize programmer time over machine time.
14. **Generation:** Automate repetitive programming work.
15. **Optimization:** Make it work before tuning performance.
16. **Diversity:** Be skeptical of any supposedly universal approach.
17. **Extensibility:** Design to accommodate future changes.
