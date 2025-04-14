import pandas as pd
import numpy as np

def check_duplicates(df, file_name):
    """Check for duplicate offer_ids in a DataFrame and print results"""
    duplicates = df[df.duplicated(subset=['offer_id'], keep=False)]
    if len(duplicates) > 0:
        dup_count = len(duplicates['offer_id'].unique())
        total_dups = len(duplicates)
        print(f"⚠️ WARNING: {file_name} has {total_dups} duplicate rows ({dup_count} unique offer_ids)")
        print(f"Example duplicates: {duplicates['offer_id'].unique()[:5].tolist()}")
        
        # For the first duplicated ID, show a comparison of first vs last record
        first_dup_id = duplicates['offer_id'].iloc[0]
        dup_rows = df[df['offer_id'] == first_dup_id]
        if len(dup_rows) >= 2:
            print(f"\nFor offer_id {first_dup_id}, comparing first and last record:")
            first_record = dup_rows.iloc[0]
            last_record = dup_rows.iloc[-1]
            
            # Find differences between first and last record
            different_cols = []
            for col in dup_rows.columns:
                if first_record[col] != last_record[col] and not (pd.isna(first_record[col]) and pd.isna(last_record[col])):
                    different_cols.append(col)
            
            if different_cols:
                print(f"Columns with differences: {different_cols}")
                print("Sample differences:")
                for col in different_cols[:3]:  # Show at most 3 differences
                    print(f"  {col}: '{first_record[col]}' vs '{last_record[col]}'")
            else:
                print("No differences found between first and last record")
                
        return True
    else:
        print(f"✓ {file_name} has no duplicate offer_ids")
        return False

def process_price_history(file_name):
    """
    Process price history file to extract price statistics.
    
    Returns:
        pd.DataFrame: DataFrame with offer_id and price statistics
    """
    print(f"\nProcessing {file_name} for price statistics...")
    df_price = pd.read_csv(file_name)
    
    # Verify the structure
    if 'offer_id' not in df_price.columns or 'price_clean' not in df_price.columns:
        print(f"Error: {file_name} doesn't have required columns 'offer_id' and 'price_clean'")
        return pd.DataFrame({'offer_id': []})
    
    # Check for duplicates (info only, we expect duplicates in price history)
    check_duplicates(df_price, file_name)
    
    # Group by offer_id and calculate statistics
    price_stats = df_price.groupby('offer_id').agg(
        peak_price=('price_clean', 'max'),
        lowest_price=('price_clean', 'min'),
        first_recorded_price=('price_clean', lambda x: x.iloc[0]),
        last_recorded_price=('price_clean', lambda x: x.iloc[-1]),
        price_change_count=('price_clean', 'count')
    ).reset_index()
    
    # Calculate price difference
    price_stats['price_difference'] = price_stats['peak_price'] - price_stats['lowest_price']
    
    # Calculate percentage change from first to last price
    price_stats['price_percent_change'] = ((price_stats['last_recorded_price'] - 
                                           price_stats['first_recorded_price']) / 
                                           price_stats['first_recorded_price'] * 100).round(2)
    
    print(f"Extracted price statistics for {len(price_stats)} unique offer_ids")
    print(f"Average price difference: {price_stats['price_difference'].mean():.2f}")
    
    return price_stats

def merge_csv_files(handle_duplicates=True, include_price_history=True):
    """
    Merge specified CSV files using an outer join on offer_id with duplicate handling.
    
    Args:
        handle_duplicates: If True, removes duplicate offer_ids from source files before merging
        include_price_history: If True, includes price statistics from price_history.csv
        
    Returns:
        pd.DataFrame: Merged DataFrame containing data from all input CSV files
    """
    # Define file list and handling functions
    file_list = [
        'features.csv',
        'estimation.csv',
        'stats.csv',
        'apartment_details.csv',
        'building_details.csv', 
        'rental_terms.csv',
        'cian_apartments.csv'
    ]
    
    # Check all files for duplicates first
    print("Checking files for duplicate offer_ids:")
    for file_name in file_list:
        df = pd.read_csv(file_name)
        has_dups = check_duplicates(df, file_name)
    
    # Process price history separately if needed
    price_stats = None
    if include_price_history:
        price_stats = process_price_history('price_history.csv')
    
    # Start with base file
    df_features = pd.read_csv('features.csv')
    if handle_duplicates and check_duplicates(df_features, 'features.csv'):
        df_features = df_features.drop_duplicates(subset=['offer_id'], keep='last')
    merged_df = df_features
    print(f"Loaded features.csv with {len(merged_df)} rows and {len(merged_df.columns)} columns")
    
    # Merge estimation.csv
    df_estimation = pd.read_csv('estimation.csv')
    if handle_duplicates and check_duplicates(df_estimation, 'estimation.csv'):
        df_estimation = df_estimation.drop_duplicates(subset=['offer_id'], keep='last')
    merged_df = pd.merge(merged_df, df_estimation, on='offer_id', how='outer',
                        suffixes=('', '_estimation'))
    print(f"After merging estimation.csv: {len(merged_df)} rows and {len(merged_df.columns)} columns")
    
    # Merge stats.csv
    df_stats = pd.read_csv('stats.csv')
    if handle_duplicates and check_duplicates(df_stats, 'stats.csv'):
        df_stats = df_stats.drop_duplicates(subset=['offer_id'], keep='last')
    merged_df = pd.merge(merged_df, df_stats, on='offer_id', how='outer',
                        suffixes=('', '_stats'))
    print(f"After merging stats.csv: {len(merged_df)} rows and {len(merged_df.columns)} columns")
    
    # Merge apartment_details.csv
    df_apartment = pd.read_csv('apartment_details.csv')
    if handle_duplicates and check_duplicates(df_apartment, 'apartment_details.csv'):
        df_apartment = df_apartment.drop_duplicates(subset=['offer_id'], keep='last')
    merged_df = pd.merge(merged_df, df_apartment, on='offer_id', how='outer',
                        suffixes=('', '_apartment'))
    print(f"After merging apartment_details.csv: {len(merged_df)} rows and {len(merged_df.columns)} columns")
    
    # Merge building_details.csv
    df_building = pd.read_csv('building_details.csv')
    if handle_duplicates and check_duplicates(df_building, 'building_details.csv'):
        df_building = df_building.drop_duplicates(subset=['offer_id'], keep='last')
    merged_df = pd.merge(merged_df, df_building, on='offer_id', how='outer',
                        suffixes=('', '_building'))
    print(f"After merging building_details.csv: {len(merged_df)} rows and {len(merged_df.columns)} columns")
    
    # Merge rental_terms.csv - with specific suffix to handle duplicate columns
    df_terms = pd.read_csv('rental_terms.csv')
    if handle_duplicates and check_duplicates(df_terms, 'rental_terms.csv'):
        df_terms = df_terms.drop_duplicates(subset=['offer_id'], keep='last')
    merged_df = pd.merge(merged_df, df_terms, on='offer_id', how='outer',
                        suffixes=('', '_terms'))
    print(f"After merging rental_terms.csv: {len(merged_df)} rows and {len(merged_df.columns)} columns")
    
    # Merge cian_apartments.csv last as it has several duplicate columns
    df_cian = pd.read_csv('cian_apartments.csv')
    if handle_duplicates and check_duplicates(df_cian, 'cian_apartments.csv'):
        df_cian = df_cian.drop_duplicates(subset=['offer_id'], keep='last')
    merged_df = pd.merge(merged_df, df_cian, on='offer_id', how='outer',
                        suffixes=('', '_cian'))
    print(f"After merging cian_apartments.csv: {len(merged_df)} rows and {len(merged_df.columns)} columns")
    
    # Merge price history statistics if available
    if include_price_history and price_stats is not None and not price_stats.empty:
        merged_df = pd.merge(merged_df, price_stats, on='offer_id', how='left')
        print(f"After merging price statistics: {len(merged_df)} rows and {len(merged_df.columns)} columns")
    
    # Clean up column names - remove any empty suffixes that might have been added
    merged_df.columns = [col.replace('_', '') if col.endswith('_') else col 
                         for col in merged_df.columns]
    
    # Fill empty values in target columns with values from other columns
    print("\nFilling empty values and cleaning up columns...")
    
    # Check if both columns exist before attempting to fill
    column_pairs_to_fill = [
        ('commission', 'commission_value'),
        ('security_deposit', 'deposit_value'),
        ('estimated_price_clean', 'cian_estimation_value')
    ]
    
    for target_col, source_col in column_pairs_to_fill:
        if target_col in merged_df.columns and source_col in merged_df.columns:
            missing_before = merged_df[target_col].isna().sum()
            merged_df[target_col] = merged_df[target_col].fillna(merged_df[source_col])
            filled_count = missing_before - merged_df[target_col].isna().sum()
            print(f"- Filled {filled_count} missing values in '{target_col}' with values from '{source_col}'")
    
    # Handle price columns (these come from price history processing)
    if 'last_recorded_price' in merged_df.columns and 'price_value' in merged_df.columns:
        missing_before = merged_df['last_recorded_price'].isna().sum()
        merged_df['last_recorded_price'] = merged_df['last_recorded_price'].fillna(merged_df['price_value'])
        filled_count = missing_before - merged_df['last_recorded_price'].isna().sum()
        print(f"- Filled {filled_count} missing values in 'last_recorded_price' with values from 'price_value'")
    
    if 'first_recorded_price' in merged_df.columns and 'last_recorded_price' in merged_df.columns:
        missing_before = merged_df['first_recorded_price'].isna().sum()
        merged_df['first_recorded_price'] = merged_df['first_recorded_price'].fillna(merged_df['last_recorded_price'])
        filled_count = missing_before - merged_df['first_recorded_price'].isna().sum()
        print(f"- Filled {filled_count} missing values in 'first_recorded_price' with values from 'last_recorded_price'")
    
    # Columns to drop
    columns_to_drop = [
        'estimated_price', 'creation_date', 'updated_date', 'price_info',
        'rental_period_cian', 'commission_info', 'deposit_info', 'commission_value',
        'deposit_value', 'cian_estimation_value', 'price_difference_value', 'cian_estimation'
    ]
    
    # Filter to only include columns that actually exist in the DataFrame
    existing_columns_to_drop = [col for col in columns_to_drop if col in merged_df.columns]
    if existing_columns_to_drop:
        merged_df = merged_df.drop(columns=existing_columns_to_drop)
        print(f"- Dropped {len(existing_columns_to_drop)} unnecessary columns: {existing_columns_to_drop}")
    
    # Report final column count
    print(f"Final dataset has {len(merged_df.columns)} columns")
    
    return merged_df

def main():
    # Let user know what's happening
    print("\nRunning merge process with duplicate handling and price history analysis...\n")
    
    # Merge the CSV files with duplicate handling and price history
    merged_dataframe = merge_csv_files(handle_duplicates=True, include_price_history=True)
    
    # Check for any remaining duplicates in the final dataset
    print("\nChecking for duplicates in final merged dataset:")
    duplicates = merged_dataframe[merged_dataframe.duplicated(subset=['offer_id'], keep=False)]
    if len(duplicates) > 0:
        dup_count = len(duplicates['offer_id'].unique())
        total_dups = len(duplicates)
        print(f"⚠️ WARNING: Final dataset still has {total_dups} duplicate rows ({dup_count} unique offer_ids)")
        
        # Print a sample of the duplicate records
        print("\nSample of duplicate offer_ids in final dataset:")
        example_id = duplicates['offer_id'].iloc[0]
        print(f"Records for offer_id {example_id}:")
        print(merged_dataframe[merged_dataframe['offer_id'] == example_id].head(2))
    else:
        print("✓ Final dataset has no duplicate offer_ids")
    
    # Print information about price statistics
    if 'peak_price' in merged_dataframe.columns:
        price_stats_count = merged_dataframe['peak_price'].notna().sum()
        print(f"\nPrice history statistics added for {price_stats_count} offers")
        
        if price_stats_count > 0:
            # Calculate some averages for offers with price history
            price_data = merged_dataframe[merged_dataframe['peak_price'].notna()]
            avg_peak = price_data['peak_price'].mean()
            avg_low = price_data['lowest_price'].mean()
            avg_diff = price_data['price_difference'].mean()
            avg_change_pct = price_data['price_percent_change'].mean()
            
            print(f"Average peak price: {avg_peak:.2f}")
            print(f"Average lowest price: {avg_low:.2f}")
            print(f"Average price difference: {avg_diff:.2f} ({(avg_diff/avg_low*100):.2f}%)")
            print(f"Average price percent change: {avg_change_pct:.2f}%")
    
    # Print a list of columns with suffixes to help identify duplicates
    suffix_columns = [col for col in merged_dataframe.columns if '_terms' in col or '_cian' in col 
                      or '_estimation' in col or '_stats' in col or '_apartment' in col 
                      or '_building' in col]
    if suffix_columns:
        print("\nColumns with suffixes (indicating duplicates):")
        for col in suffix_columns:
            print(f"- {col}")
    
    # Save the merged DataFrame
    merged_dataframe.to_csv('merged_apartments_data.csv', index=False, encoding='utf-8')
    print("\nMerged data saved to 'merged_apartments_data.csv'")
    
    # Display information about the merged dataset
    print("\nMerged Dataset Information:")
    print(f"Total number of rows: {len(merged_dataframe)}")
    print(f"Total number of columns: {len(merged_dataframe.columns)}")
    
    # Print all column names
    print("\nColumns in the merged dataset:")
    print(merged_dataframe.columns.tolist())
    
    # Optional: Preview the data
    print("\nPreview of merged data (first 5 rows):")
    print(merged_dataframe.head(5))

if __name__ == '__main__':
    main()