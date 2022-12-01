use clap::Parser;
use reqwest::StatusCode;
use serde_json::Value;
use std::error;
use std::fs::File;
use std::io;
use std::io::{BufRead, Write};
use std::path;

#[derive(Parser, PartialEq, Debug)]
#[command(author, version, about, long_about = None)]
struct Options {
    #[arg(short, long, default_value_t = 3_000)]
    entry_limit: usize,

    #[arg(short, long)]
    compendia_path: path::PathBuf,

    #[arg(short, long)]
    output_dir: path::PathBuf,

    #[arg(short, long)]
    file_name: Vec<String>,
}
#[tokio::main]
async fn main() -> Result<(), Box<dyn error::Error>> {
    let options = Options::parse();

    let output_dir = options.output_dir;
    std::fs::create_dir_all(&output_dir).ok();

    let compendia_identifier_data = parse_file(&options.compendia_path)?;

    for file_name in options.file_name.iter() {
        let mut output: path::PathBuf = output_dir.clone();
        output.push(file_name);

        let file = File::create(output.as_path()).unwrap();
        let mut writer = io::BufWriter::new(file);

        let conflation_data_response = reqwest::get(format!("https://stars.renci.org/var/babel_outputs/2022oct13/conflation/{}", file_name)).await?;

        match conflation_data_response.status() {
            StatusCode::OK => {
                let content = conflation_data_response.text().await?;
                let mut cache = vec![];
                for line in content.lines() {
                    let json: Value = serde_json::from_str(line).expect("could not parse line to json");
                    if json.is_array() {
                        let identifier = json[0].as_str().unwrap();
                        if compendia_identifier_data.contains(&identifier.to_string()) {
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

fn parse_file(file_path: &path::PathBuf) -> Result<Vec<String>, Box<dyn error::Error>> {
    let mut results = vec![];
    let reader = io::BufReader::new(File::open(file_path.as_path())?);

    for line in reader.lines() {
        let line = line.unwrap();
        let json: Value = serde_json::from_str(line.as_str()).expect("could not parse line to json");
        if json["identifiers"].is_array() {
            let identifiers = json["identifiers"].as_array().expect("could not convert to array");
            let identifier = identifiers[0]["i"].as_str().unwrap();
            results.push(identifier.to_string());
        }
    }
    Ok(results)
}
