use shortpath::{Options, Shortener};
use std::env;
use std::io::{self, BufRead, IsTerminal, Write};
use std::process::ExitCode;

const HELP: &str = "shortpath [OPTIONS] [--] [PATH ...]

Shorten each path component to its shortest unique prefix among filesystem
siblings. Output is a display label, not a directly usable filesystem path.
With no paths, read one path per line from stdin. Paths must exist and be UTF-8.

Options:
  -m, --min-length N  Minimum Unicode characters per shortened component [1]
  -k, --keep N        Keep the last N normal components in full [1; 0 allows all]
  -0, --null          Read and write NUL-delimited records
  -h, --help          Print help
  -V, --version       Print version

Use -- before paths beginning with '-'. Relative paths stay relative.
Uniqueness uses exact sibling spellings, including hidden entries, and a
per-invocation directory snapshot. Full names remain full if they prefix
another sibling. Errors go to stderr; other input paths still run.
";

fn run() -> io::Result<bool> {
    let mut options = Options::default();
    let mut delimiter = b'\n';
    let mut paths = Vec::new();
    let mut positional = false;
    let mut args = env::args_os().skip(1);
    while let Some(arg) = args.next() {
        let arg = arg
            .into_string()
            .map_err(|_| invalid("arguments must be UTF-8"))?;
        if positional {
            paths.push(arg);
            continue;
        }
        match arg.as_str() {
            "--" => positional = true,
            "-h" | "--help" => {
                io::stdout().lock().write_all(HELP.as_bytes())?;
                return Ok(true);
            }
            "-V" | "--version" => {
                writeln!(
                    io::stdout().lock(),
                    "shortpath {}",
                    env!("CARGO_PKG_VERSION")
                )?;
                return Ok(true);
            }
            "-0" | "--null" => delimiter = 0,
            "-m" | "--min-length" | "-k" | "--keep" => {
                let value = args
                    .next()
                    .and_then(|s| s.into_string().ok())
                    .and_then(|s| s.parse::<usize>().ok())
                    .ok_or_else(|| invalid(&format!("{arg} requires a nonnegative integer")))?;
                if arg == "-m" || arg == "--min-length" {
                    if value == 0 {
                        return Err(invalid("minimum length must be positive"));
                    }
                    options.min_length = value;
                } else {
                    options.keep = value;
                }
            }
            _ if arg.starts_with('-') => return Err(invalid(&format!("unknown option: {arg}"))),
            _ => paths.push(arg),
        }
    }
    let mut shortener = Shortener::default();
    let mut output = io::BufWriter::new(io::stdout().lock());
    let mut success = true;
    let mut emit = |path: &str| -> io::Result<bool> {
        if path.as_bytes().contains(&delimiter) {
            eprintln!(
                "shortpath: {path:?}: path contains output delimiter; use --null for newlines"
            );
            return Ok(false);
        }
        match shortener.shorten(path, options) {
            Ok(short) => {
                output.write_all(short.as_bytes())?;
                output.write_all(&[delimiter])?;
            }
            Err(error) => {
                eprintln!("shortpath: {path:?}: {error}");
                return Ok(false);
            }
        }
        Ok(true)
    };
    if paths.is_empty() {
        if io::stdin().is_terminal() {
            return Err(invalid("provide paths or pipe paths on stdin; see --help"));
        }
        let mut input = io::stdin().lock();
        let mut record = Vec::new();
        while input.read_until(delimiter, &mut record)? != 0 {
            if record.last() == Some(&delimiter) {
                record.pop();
            }
            match std::str::from_utf8(&record) {
                Ok(path) => success &= emit(path)?,
                Err(_) => {
                    eprintln!("shortpath: input path must be UTF-8");
                    success = false;
                }
            }
            record.clear();
        }
    } else {
        for path in paths {
            success &= emit(&path)?;
        }
    }
    output.flush()?;
    Ok(success)
}

fn invalid(message: &str) -> io::Error {
    io::Error::new(io::ErrorKind::InvalidInput, message)
}

fn main() -> ExitCode {
    match run() {
        Ok(true) => ExitCode::SUCCESS,
        Ok(false) => ExitCode::FAILURE,
        Err(error) if error.kind() == io::ErrorKind::BrokenPipe => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("shortpath: {error}");
            ExitCode::FAILURE
        }
    }
}
