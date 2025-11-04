use pyo3::prelude::*;

#[pyfunction]
fn hello_from_bin() -> String {
    "Hello from astrbox!".to_string()
}

#[pymodule]
mod core {
    use pyo3::prelude::*;

    #[pymodule_export]
    use super::hello_from_bin;

    #[pymodule]
    mod cli {
        #[pymodule_export]
        use super::hello_from_bin;
    }
}
