use std::fs::File;
use std::path::Path;
use sha2::{Sha256, Digest};
use std::io::Result;

pub fn compute_file_hash(file_path: &Path) -> Result<String> {
    let mut file = File::open(file_path)?;
    let mut hasher = Sha256::new();
    std::io::copy(&mut file, &mut hasher)?;
    let hash = hasher.finalize();
    Ok(format!("{:x}", hash))
}
