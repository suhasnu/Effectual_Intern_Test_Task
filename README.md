# World Bank Macroeconomic Data Collection & Analysis

## Project Purpose
This project provides a reproducible, configuration-driven Python data pipeline that automatically collects, reshapes, and analyzes annual macroeconomic data from the World Bank API. It focuses on evaluating structural economic changes—specifically the shares and growth of industry and manufacturing value added relative to overall GDP.

## Configuration (config.toml)
The data collection process is entirely configuration-driven via `config.toml`. It dictates:
* `[countries]`: The specific countries to query.
* `[time]`: The time horizon (start and end years).
* `[series]`: The specific World Bank indicator codes to retrieve.

No countries, years, or indicators are hard-coded in the Python source code. To change the scope of the analysis, you only need to modify the `config.toml` file.

## Instructions to Run the Project
1. Clone this repository to your local machine.
2. Install the required dependencies using: `pip install -r requirements.txt`
3. Run the main pipeline script: `python main.py`
4. The outputs (`main_dataset.csv` and `summary_table.csv`) will be generated in the root directory.

## Description of Outputs
* **`main_dataset.csv`**: A wide-format dataset where each row represents a unique country and indicator combination. Missing values from the API are represented explicitly as blank/NaN. Each year within the configured time horizon is represented as a separate column (e.g., `year_2000`).
* **`summary_table.csv`**: A compact analytical table showing one row per country. It details the industry and manufacturing value-added shares for the start and end years, alongside the Compound Annual Growth Rate (CAGR) for industry, manufacturing, and real GDP. 
* **`analysis.md`**: A separate Markdown file containing a short interpretation answering the specific analytical questions regarding de-industrialization and structural trends.

## Assumptions and Limitations
* **Handling Missing Current-Year Data:** Because the World Bank API has not yet released complete macroeconomic data for the year 2025 (returning `NaN` for all countries), the script is designed to dynamically identify and compute growth rates using the *latest available valid year* (e.g., 2023 or 2024) for each respective country, while maintaining the requested column names for the output format to satisfy downstream requirements.
* **API Coverage:** It is assumed that the World Bank API has comprehensive coverage for the selected countries. For some years, specific indicators may be published as `NaN` due to reporting lags by national statistical agencies.
* **CAGR Calculations:** The CAGR formula requires valid numerical values for both the start and end years. If a country is entirely missing data for the absolute start year boundary, the growth trend and start-shares calculate as `NaN` (e.g., the United States missing industrial value added in 2000).
* **Country Naming Convention:** The script dynamically links common country names in the TOML to World Bank ISO codes but relies on accurate spelling (e.g., using "Turkiye" instead of "Turkey" in alignment with recent World Bank updates).