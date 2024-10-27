use microradar::processing::process_files_offline;
use microradar::elastic;
use microradar::database;
use microradar::config;
use microradar::processing;
use microradar::patterns::PATTERNS;

use clap::{Parser, Subcommand};
use config::Config;
use database::init_pg_client;
use elastic::{init_es_client, search_elastic};
use processing::{process_files, scan_file_for_patterns};
use regex::Regex;
use walkdir::WalkDir;
use std::path::Path;

#[derive(Parser)]
#[command(name = "MicroRadar")]
#[command(about = "CLI for ingesting files, searching, and scanning.", long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    Ingest {
        input_directory: String,
        #[arg(short, long)]
        offline: bool,
    },
    Search {
        term: String,
    },
    Scan {
        file_path: String,
        #[arg(short, long)]
        offline: bool,
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let cli = Cli::parse();
    let config = Config::new();

    match cli.command {
        Commands::Ingest { input_directory, offline } => {
            let regexes: Vec<(Regex, String)> = if offline {
                PATTERNS.iter()
                    .map(|(pattern_str, class)| {
                        let regex = Regex::new(pattern_str).expect("Invalid regex pattern");
                        (regex, class.to_string())
                    })
                    .collect()
            } else {
                let (pg_client, pg_connection) = init_pg_client(&config).await?;
                tokio::spawn(async move {
                    if let Err(e) = pg_connection.await {
                        eprintln!("PostgreSQL connection error: {}", e);
                    }
                });
    
                let patterns = database::load_patterns(&pg_client).await?;
                patterns.into_iter()
                    .map(|(pattern_str, class)| {
                        let regex = Regex::new(&pattern_str).expect("Invalid regex pattern");
                        (regex, class)
                    })
                    .collect()
            };
    
            let es_client = init_es_client(&config)?;
    
            let file_paths: Vec<_> = WalkDir::new(&input_directory)
                .into_iter()
                .filter_map(|e| e.ok())
                .filter(|e| e.file_type().is_file())
                .map(|e| e.path().to_owned())
                .collect();
    
            if offline {
                process_files_offline(file_paths, &es_client, &regexes).await?;
            } else {
                let (pg_client, pg_connection) = init_pg_client(&config).await?;
                tokio::spawn(async move {
                    if let Err(e) = pg_connection.await {
                        eprintln!("PostgreSQL connection error: {}", e);
                    }
                });
                process_files(file_paths, &pg_client, &es_client, &regexes).await?;
            }
        }
        Commands::Search { term } => {
            let es_client = init_es_client(&config)?;
            search_elastic(&es_client, &term).await?;
        }
        Commands::Scan { file_path, offline } => {
            let regexes: Vec<(Regex, String)> = if offline {
                PATTERNS.iter()
                    .map(|(pattern_str, class)| {
                        let regex = Regex::new(pattern_str).expect("Invalid regex pattern");
                        (regex, class.to_string())
                    })
                    .collect()
            } else {
                let (pg_client, pg_connection) = init_pg_client(&config).await?;
                tokio::spawn(async move {
                    if let Err(e) = pg_connection.await {
                        eprintln!("PostgreSQL connection error: {}", e);
                    }
                });
    
                let patterns = database::load_patterns(&pg_client).await?;
                patterns.into_iter()
                    .map(|(pattern_str, class)| {
                        let regex = Regex::new(&pattern_str).expect("Invalid regex pattern");
                        (regex, class)
                    })
                    .collect()
            };
    
            let matches = scan_file_for_patterns(Path::new(&file_path), &regexes)?;
            if matches.is_empty() {
                println!("- No credentials or sensitive data found in file: {}", file_path);
            } else {
                println!("+ Sensitive data found in file: {}", file_path);
                for (found, class) in matches {
                    println!("(Class: {}) {}", class, found);
                }
            }
        }
    }
    
    
    Ok(())
}
