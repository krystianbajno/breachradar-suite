use std::env;

pub struct Config {
    pub pg_user: String,
    pub pg_password: String,
    pub pg_db: String,
    pub pg_host: String,
    pub pg_port: String,
    pub es_url: String,
}

impl Config {
    pub fn new() -> Self {
        dotenv::dotenv().ok();
        Config {
            pg_user: env::var("POSTGRES_USER").unwrap_or("cti_user".to_string()),
            pg_password: env::var("POSTGRES_PASSWORD").unwrap_or("cti_password".to_string()),
            pg_db: env::var("POSTGRES_DB").unwrap_or("cti_breach_hunter".to_string()),
            pg_host: env::var("POSTGRES_HOST").unwrap_or("localhost".to_string()),
            pg_port: env::var("POSTGRES_PORT").unwrap_or("5432".to_string()),
            es_url: env::var("ELASTICSEARCH_HOST").unwrap_or("http://localhost:9200".to_string()),
        }
    }
}
