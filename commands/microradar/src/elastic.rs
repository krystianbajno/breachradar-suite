use std::path::Path;

use elasticsearch::{http::transport::Transport, Elasticsearch, IndexParts, SearchParts};
use serde_json::json;
use crate::config::Config;
use crate::utils::compute_file_hash;
use std::error::Error;

pub fn init_es_client(config: &Config) -> Result<Elasticsearch, Box<dyn std::error::Error>> {
    let transport = Transport::single_node(&config.es_url)?;
    let client = Elasticsearch::new(transport);
    Ok(client)
}

pub async fn save_chunk(
    es_client: &Elasticsearch,
    scrap_id: i32,
    file_path: &Path,
    chunk_content: &str,
    chunk_number: usize,
    matches: &Vec<(String, String)>
) -> Result<(), Box<dyn std::error::Error>> {
    let index_name = "scrapes_chunks";

    let document = json!({
        "scrap_id": scrap_id,
        "chunk_number": chunk_number,
        "content": chunk_content,
        "title": file_path.file_name().unwrap().to_string_lossy(),
        "hash": compute_file_hash(file_path)?,
        "matches": matches,
    });

    let response = es_client.index(IndexParts::Index(index_name))
        .body(document)
        .send()
        .await?;

    if !response.status_code().is_success() {
        eprintln!("Failed to index document in Elasticsearch.");
    }

    Ok(())
}


use colored::*; // Import the colored traits

pub async fn search_elastic(
    es_client: &Elasticsearch,
    term: &str,
) -> Result<(), Box<dyn Error>> {
    let query = json!({
        "query": {
            "match": {
                "content": term
            }
        },
        "_source": ["content"]
    });

    let response = es_client
        .search(SearchParts::Index(&["scrapes_chunks"]))
        .body(query)
        .send()
        .await?;

    let response_body = response.json::<serde_json::Value>().await?;

    let hits = response_body["hits"]["hits"]
        .as_array()
        .ok_or("No results found")?;

    if hits.is_empty() {
        println!("No results found.");
        return Ok(());
    }

    for hit in hits {
        let content_str = hit.get("_source")
            .and_then(|s| s.get("content"))
            .and_then(|c| c.as_str());

        if let Some(content) = content_str {
            for line in content.lines() {
                if line.contains(term) {
                    let highlighted_line = line.replace(
                        term,
                        &term.red().bold().to_string(),
                    );
                    println!("{}", highlighted_line);
                }
            }
        }
    }

    Ok(())
}
