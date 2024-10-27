use rusqlite::Connection;
use tokio_postgres::{Client, Error, NoTls, Socket};
use crate::config::Config;

pub async fn init_pg_client(config: &Config) -> Result<(Client, tokio_postgres::Connection<Socket, tokio_postgres::tls::NoTlsStream>), Error> {
    let pg_conn_str = format!(
        "host={} port={} user={} password={} dbname={}",
        config.pg_host, config.pg_port, config.pg_user, config.pg_password, config.pg_db
    );

    let (client, connection) = tokio_postgres::connect(&pg_conn_str, NoTls).await?;
    Ok((client, connection))
}

pub async fn is_hash_processed(pg_client: &Client, hash: &str) -> Result<bool, Box<dyn std::error::Error>> {
    let row = pg_client.query_one(
        "SELECT EXISTS (SELECT 1 FROM scrapes WHERE hash = $1 AND state = 'PROCESSED') AS exists",
        &[&hash]
    ).await?;
    let exists: bool = row.get("exists");
    Ok(exists)
}

pub async fn save_scrap_reference(pg_client: &Client, hash: &str, file_path: &std::path::Path) -> Result<i32, Box<dyn std::error::Error>> {
    let filename = file_path.file_name().unwrap().to_string_lossy();
    let file_path_str = file_path.to_string_lossy();
    let row = pg_client.query_one(
        "INSERT INTO scrapes (hash, source, filename, scrape_time, file_path, state) VALUES ($1, $2, $3, NOW(), $4, $5) RETURNING id",
        &[&hash, &"local", &filename, &file_path_str, &"PROCESSING"]
    ).await?;
    let id: i32 = row.get("id");
    Ok(id)
}

pub async fn update_scrap_state(pg_client: &Client, scrap_id: i32, state: &str) -> Result<(), Box<dyn std::error::Error>> {
    pg_client.execute(
        "UPDATE scrapes SET state = $1 WHERE id = $2",
        &[&state, &scrap_id]
    ).await?;
    Ok(())
}

pub async fn sync_patterns_to_postgres(pg_client: &Client, db_path: &str) -> Result<(), Box<dyn std::error::Error>> {
    let conn = Connection::open(db_path)?;

    let mut stmt = conn.prepare("SELECT pattern, class FROM patterns")?;
    let pattern_iter = stmt.query_map([], |row| {
        let pattern_str: String = row.get(0)?;
        let class: String = row.get(1)?;
        Ok((pattern_str, class))
    })?;

    for pattern in pattern_iter {
        let (pattern_str, class) = pattern?;
        pg_client
            .execute(
                "INSERT INTO classifier_patterns (pattern, class) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                &[&pattern_str, &class],
            )
            .await?;
    }

    Ok(())
}

pub async fn load_patterns(pg_client: &Client) -> Result<Vec<(String, String)>, Box<dyn std::error::Error>> {
    let rows = pg_client.query("SELECT pattern, class FROM classifier_patterns", &[]).await?;
    let patterns = rows.iter()
        .map(|row| {
            let pattern: String = row.get("pattern");
            let class: String = row.get("class");
            (pattern, class)
        })
        .collect();
    Ok(patterns)
}
