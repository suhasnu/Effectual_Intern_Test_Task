import sys
import requests
import pandas as pd
import numpy as np

# Use built-in tomllib for Python 3.11+, otherwise use tomli
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

def load_config(file_path="config.toml"):
    # Load configuration from TOML file.
    with open(file_path, "rb") as f:
        return tomllib.load(f)

def fetch_wb_country_mapping():
    """Fetch country names and ISO codes dynamically to avoid hardcoding."""
    url = "http://api.worldbank.org/v2/country?format=json&per_page=300"
    response = requests.get(url).json()
    mapping = {}
    for country in response[1]:
        mapping[country['name']] = country['id']
    return mapping

def fetch_wb_data(indicator, start_year, end_year):
    """Fetch data for a specific indicator from the World Bank API handling pagination."""
    url = f"http://api.worldbank.org/v2/country/all/indicator/{indicator}?date={start_year}:{end_year}&format=json&per_page=1000"
    
    response = requests.get(url).json()
    
    # Handle missing or invalid indicators safely
    if len(response) < 2:
        return []
        
    total_pages = response[0]['pages']
    all_data = response[1]
    
    # Handle pagination
    if total_pages > 1:
        for page in range(2, total_pages + 1):
            page_url = f"{url}&page={page}"
            page_response = requests.get(page_url).json()
            all_data.extend(page_response[1])
            
    return all_data

def process_main_dataset(raw_data, country_list, valid_countries, indicator_key):
    """Process raw API data into a structured pandas DataFrame."""
    records = []
    for item in raw_data:
        country_name = item['country']['value']
        
        # Only keep countries specified in the config
        if country_name in country_list or country_name in valid_countries:
            records.append({
                'country': country_name,
                'indicator': indicator_key,
                'year': int(item['date']),
                'value': item['value']
            })
            
    return pd.DataFrame(records)

def calculate_cagr(start_val, end_val, periods):
    # Calculate Compound Annual Growth Rate.
    if pd.isna(start_val) or pd.isna(end_val) or start_val <= 0 or periods <= 0:
        return np.nan
    return (end_val / start_val) ** (1 / periods) - 1

def run_pipeline():
    # 1. Load Configuration
    config = load_config()
    target_countries = config['countries']['list']
    start_year = config['time']['start_year']
    end_year = config['time']['end_year']
    series = config['series']
    
    # 2. Map Countries
    wb_mapping = fetch_wb_country_mapping()
    valid_countries = [c for c in target_countries if c in wb_mapping or c in wb_mapping.values()]

    # 3. Fetch and Process Data
    all_dfs = []
    for indicator_name, indicator_code in series.items():
        print(f"Fetching data for {indicator_name} ({indicator_code})...")
        raw_data = fetch_wb_data(indicator_code, start_year, end_year)
        df = process_main_dataset(raw_data, target_countries, valid_countries, indicator_name)
        all_dfs.append(df)
        
    combined_df = pd.concat(all_dfs, ignore_index=True)
    
    # 4. Reshape Main Dataset (Wide format)
    main_dataset = combined_df.pivot_table(
        index=['country', 'indicator'], 
        columns='year', 
        values='value',
        dropna=False
    ).reset_index()
    
    # Rename columns to year_YYYY format
    year_cols = [col for col in main_dataset.columns if isinstance(col, int)]
    rename_dict = {year: f"year_{year}" for year in year_cols}
    main_dataset = main_dataset.rename(columns=rename_dict)
    
    # Save main dataset to CSV
    main_dataset.to_csv("main_dataset.csv", index=False)
    print("Exported main_dataset.csv")

    # 5. Analysis & Summary Table
    # Re-pivot to get indicators as columns for easier calculation per country/year
    analysis_df = combined_df.pivot_table(
        index=['country', 'year'],
        columns='indicator',
        values='value'
    ).reset_index()

    summary_records = []
    periods = end_year - start_year
    
    for country in valid_countries:
        country_data = analysis_df[analysis_df['country'] == country]
        if country_data.empty:
            continue
            
        try:
            # Get start data strictly for start_year
            start_data = country_data[country_data['year'] == start_year]
            if start_data.empty:
                continue
            data_start = start_data.iloc[0]
            
            # Find the most recent year with valid gdp data (to avoid NaN 2025)
            valid_end_data = country_data.dropna(subset=['gdp_usd_real', 'industry_value_added_usd_const'])
            if valid_end_data.empty:
                continue
            data_end = valid_end_data.iloc[-1]
            
            # Use the actual end year for the calculation period
            actual_end_year = data_end['year']
            actual_periods = actual_end_year - start_year
            if actual_periods <= 0:
                continue
            
            # 1. Value-added shares
            ind_share_start = data_start['industry_value_added_usd_const'] / data_start['gdp_usd_real'] if data_start['gdp_usd_real'] else np.nan
            ind_share_end = data_end['industry_value_added_usd_const'] / data_end['gdp_usd_real'] if data_end['gdp_usd_real'] else np.nan
            
            man_share_start = data_start['manufacturing_value_added_usd_const'] / data_start['gdp_usd_real'] if data_start['gdp_usd_real'] else np.nan
            man_share_end = data_end['manufacturing_value_added_usd_const'] / data_end['gdp_usd_real'] if data_end['gdp_usd_real'] else np.nan
            
            # 2. Growth trends (CAGR)
            ind_cagr = calculate_cagr(data_start['industry_value_added_usd_const'], data_end['industry_value_added_usd_const'], actual_periods)
            man_cagr = calculate_cagr(data_start['manufacturing_value_added_usd_const'], data_end['manufacturing_value_added_usd_const'], actual_periods)
            gdp_cagr = calculate_cagr(data_start['gdp_usd_real'], data_end['gdp_usd_real'], actual_periods)
            
            summary_records.append({
                'country': country,
                f'industry_share_{start_year}': ind_share_start,
                f'industry_share_{end_year}': ind_share_end, # Keeping col name as 2025 per instructions
                f'manufacturing_share_{start_year}': man_share_start,
                f'manufacturing_share_{end_year}': man_share_end,
                'industry_cagr': ind_cagr,
                'manufacturing_cagr': man_cagr,
                'gdp_cagr': gdp_cagr
            })
        except Exception:
            continue

    summary_table = pd.DataFrame(summary_records)
    
    # Rename columns to match requirements precisely
    summary_table = summary_table.rename(columns={
        'industry_share_start': f'industry_share_{start_year}',
        'industry_share_end': f'industry_share_{end_year}',
        'manufacturing_share_start': f'manufacturing_share_{start_year}',
        'manufacturing_share_end': f'manufacturing_share_{end_year}'
    })

    summary_table.to_csv("summary_table.csv", index=False)
    print("Exported summary_table.csv")

if __name__ == "__main__":
    run_pipeline()