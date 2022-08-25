#[macro_use]
extern crate serde_derive;

use pyo3::prelude::*;
use std::path::{Path, PathBuf};
use itertools::Itertools;
use serde_json::Value;
use std::error::Error;

// {"type": "biolink:Cell", "ic": "100", "identifiers": [{"i": "CL:0002010", "l": "pre-conventional dendritic cell"}]}

#[derive(Serialize, Deserialize, Debug)]
pub struct CompendiaIdentifier {
    #[serde(rename = "i")]
    pub id: String,
    #[serde(rename = "l", skip_serializing_if = "String::is_empty")]
    pub label: String,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct CompendiaEntry {
    #[serde(rename = "type")]
    pub compendia_type: String,
    #[serde(rename = "ic", skip_serializing_if = "Option::is_none")]
    pub information_content: Option<String>,
    pub identifiers: Vec<CompendiaIdentifier>,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct SSSOMEntry {
    pub subject_id: String,
    pub subject_label: String,
    pub subject_category: String,
    pub predicate_id: String,
    pub object_id: String,
    pub object_label: String,
    pub object_category: String,
    pub match_type: String,
    pub other: String,
}

#[pyfunction]
pub fn sssom_to_legacy_format(path: &str) -> PyResult<Vec<String>> {
    let path_instance = PathBuf::from(path);
    let data = read_sssom_file(path_instance.as_path()).unwrap();
    let mut ret = vec![];

    let grouping = data.iter().map(|a| ((a.subject_category.clone(), a.subject_id.clone(), a.subject_label.clone()), a)).into_group_map();
    for (key, values) in grouping.iter() {

        let mut identifiers = vec![
            CompendiaIdentifier {
                id: key.1.clone(),
                label: key.2.clone(),
            }
        ];

        let mut ic_values = values
            .iter()
            .map(|a| a.other.clone())
            .map(|a| {
                let json: Value = serde_json::from_str(a.as_str()).unwrap();
                match json["subject_information_content"].is_null() {
                    true => None,
                    false => Some(json["subject_information_content"].to_string()),
                }
            })
            .flatten()
            .collect_vec();

        ic_values.dedup();

        values.iter().filter(|a| key.1 != a.object_id).for_each(|a| identifiers.push(CompendiaIdentifier {
            id: a.object_id.clone(),
            label: a.object_label.clone(),
        }));

        let compendia_entry = CompendiaEntry {
            compendia_type: key.0.clone(),
            information_content: ic_values.into_iter().next(),
            identifiers
        };
        ret.push(serde_json::to_string(&compendia_entry).unwrap());
    }

    Ok(ret)
}

// conflations of chemicals and chemicals
// conflations of chemicals and drug

fn read_sssom_file(path: &Path) -> Result<Vec<SSSOMEntry>, Box<dyn Error>> {
    let raw_data = std::fs::read_to_string(path).unwrap();
    let raw_data_str = raw_data.as_str();
    let mut data_reader = csv::ReaderBuilder::new().delimiter(b'\t').has_headers(true).from_reader(raw_data_str.as_bytes());
    let mut data = vec![];
    for record in data_reader.deserialize() {
        let record: SSSOMEntry = record.unwrap();
        data.push(record);
    }
    Ok(data)
}


/// A Python module implemented in Rust.
#[pymodule]
fn nn_io_rs(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(sssom_to_legacy_format, m)?)?;
    Ok(())
}
