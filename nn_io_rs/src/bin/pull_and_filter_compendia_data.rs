use clap::Parser;
use reqwest::StatusCode;
use serde_json::Value;
use std::error;
use std::fs::File;
use std::io::{BufWriter, Write};
use std::path;

#[derive(Parser, PartialEq, Debug)]
#[command(author, version, about, long_about = None)]
struct Options {
    #[arg(short, long, default_value_t = 3_000)]
    entry_limit: usize,

    #[arg(short, long, long_help = "identifiers greater than", default_value_t = 2)]
    identifier_floor: usize,

    #[arg(short, long)]
    output_dir: path::PathBuf,

    #[arg(short, long)]
    file_name: Vec<String>,
}
#[tokio::main]
async fn main() -> Result<(), Box<dyn error::Error>> {
    let options = Options::parse();

    let output_dir: path::PathBuf = options.output_dir.to_path_buf();
    std::fs::create_dir_all(&output_dir).ok();

    for file_name in options.file_name.iter() {
        let mut output: path::PathBuf = output_dir.clone();
        output.push(file_name);

        let file = File::create(output.as_path()).unwrap();
        let mut writer = BufWriter::new(file);

        let cell_data_response = reqwest::get(format!("https://stars.renci.org/var/babel_outputs/2022oct13/compendia/{}", file_name)).await?;

        match cell_data_response.status() {
            StatusCode::OK => {
                let content = cell_data_response.text().await?;
                let mut cache = vec![];
                for line in content.lines() {
                    let json: Value = serde_json::from_str(line).expect("could not parse line to json");
                    if json["identifiers"].is_array() {
                        let identifiers = json["identifiers"].as_array().expect("could not convert to array");
                        if identifiers.len() >= options.identifier_floor {
                            cache.push(line);
                        }
                    }
                    if cache.len() == options.entry_limit {
                        break;
                    }
                }

                cache.iter().for_each(|line| {
                    writer.write(format!("{}\n", line).as_bytes()).expect("Unable to write data");
                });
            }
            _ => {
                print!("response status was not OK (200)");
            }
        }
    }

    Ok(())
}
