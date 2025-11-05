use pyo3::prelude::*;

pub mod cli;

#[pymodule]
mod core {
    use pyo3::prelude::*;

    #[pyfunction]
    fn hello_from_bin() -> String {
        "Hello from astrbox!".to_string()
    }






}
