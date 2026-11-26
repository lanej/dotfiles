// Resolve the retry policy without allocating.
trait Policy {
    fn delay(&self, attempt: u32) -> Option<u64>;
}
enum Outcome<'a> { Retry(u64), Stop(&'a str) }

fn decide<'a>(p: &impl Policy, n: u32) -> Outcome<'a> {
    match p.delay(n) {
        Some(ms) if n < 3 => Outcome::Retry(ms),
        _ => Outcome::Stop("budget exhausted"),
    }
}
