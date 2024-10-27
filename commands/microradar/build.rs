use serde::Deserialize;
use std::fs::{File, OpenOptions};
use std::io::{BufReader, Write};

#[derive(Debug, Deserialize)]
struct Pattern {
    pattern: String,
    class: String,
}

fn main() {
    if let Err(e) = generate_patterns_rs() {
        eprintln!("Error generating patterns.rs: {}", e);
        std::process::exit(1);
    }
}

fn generate_patterns_rs() -> Result<(), Box<dyn std::error::Error>> {
    let file = File::open("patterns.json")?;
    let reader = BufReader::new(file);
    let patterns: Vec<Pattern> = serde_json::from_reader(reader)?;

    let mut output = OpenOptions::new()
        .write(true)
        .create(true)
        .truncate(true)
        .open("src/patterns.rs")?;

    writeln!(
        output,
        "pub static PATTERNS: &[(&str, &str)] = &{:#?};",
        patterns
            .iter()
            .map(|p| (p.pattern.as_str(), p.class.as_str()))
            .collect::<Vec<(&str, &str)>>()
    )?;

    Ok(())
}
