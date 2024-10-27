use std::fs::File;
use std::io::{BufReader, BufRead};
use std::path::Path;
use regex::Regex;
use tokio_postgres::Client;
use sha2::{Sha256, Digest};
use elasticsearch::Elasticsearch;

use crate::database::{is_hash_processed, save_scrap_reference, update_scrap_state};

use super::elastic::save_chunk;

const CHUNK_SIZE: usize = 1_000_000;

pub async fn process_files(
    file_paths: Vec<std::path::PathBuf>,
    pg_client: &Client,
    es_client: &Elasticsearch,
    regexes: &Vec<(Regex, String)>
) -> Result<(), Box<dyn std::error::Error>> {
    for file_path in file_paths {
        process_file(file_path, pg_client, es_client, regexes).await?;
    }
    Ok(())
}

pub async fn process_files_offline(
    file_paths: Vec<std::path::PathBuf>,
    es_client: &Elasticsearch,
    regexes: &Vec<(Regex, String)>
) -> Result<(), Box<dyn std::error::Error>> {
    for file_path in file_paths {
        process_file_offline(file_path, es_client, regexes).await?;
    }
    Ok(())
}

async fn process_file(
    file_path: std::path::PathBuf,
    pg_client: &Client,
    es_client: &Elasticsearch,
    regexes: &Vec<(Regex, String)>
) -> Result<(), Box<dyn std::error::Error>> {
    let hash = compute_file_hash(&file_path)?;

    if is_hash_processed(pg_client, &hash).await? {
        println!("File {} already processed.", file_path.display());
        return Ok(());
    }

    let matches = scan_file_for_patterns(&file_path, regexes)?;

    if matches.is_empty() {
        println!("No patterns found in file {}.", file_path.display());
        return Ok(());
    }

    let scrap_id = save_scrap_reference(pg_client, &hash, &file_path).await?;
    save_chunks_to_elastic(es_client, scrap_id, &file_path, &matches).await?;
    update_scrap_state(pg_client, scrap_id, "PROCESSED").await?;

    println!("Processed file {}.", file_path.display());
    Ok(())
}

async fn process_file_offline(
    file_path: std::path::PathBuf,
    es_client: &Elasticsearch,
    regexes: &Vec<(Regex, String)>
) -> Result<(), Box<dyn std::error::Error>> {
    let matches = scan_file_for_patterns(&file_path, regexes)?;

    if matches.is_empty() {
        println!("No patterns found in file {}.", file_path.display());
        return Ok(());
    }

    let scrap_id = 0;
    save_chunks_to_elastic(es_client, scrap_id, &file_path, &matches).await?;

    println!("Processed file {} (Offline Mode).", file_path.display());
    Ok(())
}

fn compute_file_hash(file_path: &Path) -> Result<String, Box<dyn std::error::Error>> {
    let mut file = File::open(file_path)?;
    let mut hasher = Sha256::new();
    std::io::copy(&mut file, &mut hasher)?;
    let hash = hasher.finalize();
    Ok(format!("{:x}", hash))
}

pub fn scan_file_for_patterns(
    file_path: &Path,
    regexes: &Vec<(Regex, String)>
) -> Result<Vec<(String, String)>, Box<dyn std::error::Error>> {
    let file = File::open(file_path)?;
    let reader = BufReader::new(file);

    let mut matches = Vec::new();
    for line in reader.lines() {
        let line = line?;
        for (regex, class) in regexes {
            for mat in regex.find_iter(&line) {
                matches.push((mat.as_str().to_string(), class.clone()));
            }
        }
    }

    Ok(matches)
}

async fn save_chunks_to_elastic(
    es_client: &Elasticsearch,
    scrap_id: i32,
    file_path: &Path,
    matches: &Vec<(String, String)>
) -> Result<(), Box<dyn std::error::Error>> {
    let file = File::open(file_path)?;
    let reader = BufReader::new(file);

    let mut buffer = String::new();
    let mut buffer_size = 0;
    let mut chunk_number = 1;

    for line in reader.lines() {
        let line = line?;
        let line_size = line.len() + 1;

        if buffer_size + line_size > CHUNK_SIZE {
            save_chunk(es_client, scrap_id, file_path, &buffer, chunk_number, matches).await?;
            chunk_number += 1;

            buffer.clear();
            buffer_size = 0;
        }

        buffer.push_str(&line);
        buffer.push('\n');
        buffer_size += line_size;
    }

    if !buffer.is_empty() {
        save_chunk(es_client, scrap_id, file_path, &buffer, chunk_number, matches).await?;
    }

    Ok(())
}


