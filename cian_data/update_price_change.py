import pandas as pd
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"apartment_update_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

# Read the CSV files
logger.info("Reading CSV files")
cian_apartments = pd.read_csv('cian_apartments.csv')
price_history = pd.read_csv('price_history.csv')

logger.info(f"Found {len(cian_apartments)} apartments and {len(price_history)} price history records")

# Debug: Print the first few rows and data types from each DataFrame
logger.info("First few apartments:")
logger.info(cian_apartments.head())
logger.info("\nFirst few price history entries:")
logger.info(price_history.head())

logger.info("\nData types in cian_apartments:")
logger.info(cian_apartments.dtypes)
logger.info("\nData types in price_history:")
logger.info(price_history.dtypes)

# Check for data type mismatches
cian_apt_ids = set(cian_apartments['offer_id'].astype(str))
price_hist_ids = set(price_history['offer_id'].astype(str))

logger.info(f"\nSample of offer_ids in cian_apartments: {list(cian_apt_ids)[:5]}")
logger.info(f"Sample of offer_ids in price_history: {list(price_hist_ids)[:5]}")

# Check for common IDs
common_ids = cian_apt_ids.intersection(price_hist_ids)
logger.info(f"\nNumber of common offer_ids: {len(common_ids)}")
logger.info(f"Common offer_ids: {common_ids}")

# Create a counter for changes
changes = {
    'offers_processed': 0,
    'offers_with_history': 0,
    'date_matches': 0,
    'date_mismatches': 0,
    'price_change_updates': 0,
    'updated_time_updates': 0
}

# Function to extract date part (yyyy-mm-dd) from a datetime string
def get_date_part(datetime_str):
    if pd.isna(datetime_str):
        return None
    return datetime_str.split(' ')[0]

# Process each apartment listing
for index, apartment in cian_apartments.iterrows():
    offer_id = str(apartment['offer_id'])
    changes['offers_processed'] += 1
    
    # Check if the offer_id exists in price_history
    offer_history = price_history[price_history['offer_id'].astype(str) == offer_id]
    
    if offer_history.empty:
        if index < 5:  # Log only first few for brevity
            logger.info(f"No price history found for offer ID: {offer_id}")
        continue
    
    changes['offers_with_history'] += 1
    logger.info(f"Found {len(offer_history)} price history records for offer ID: {offer_id}")
    
    # Find the most recent price history entry
    offer_history['date_iso_dt'] = pd.to_datetime(offer_history['date_iso'])
    most_recent_idx = offer_history['date_iso_dt'].idxmax()
    most_recent = offer_history.loc[most_recent_idx]
    
    # Compare the date part of updated_time with the date part of the most recent date_iso
    apartment_date = get_date_part(apartment['updated_time'])
    history_date = get_date_part(most_recent['date_iso'])
    
    logger.info(f"Apartment date: {apartment_date}, History date: {history_date}")
    old_price_change_value = apartment['price_change_value']
    
    if apartment_date == history_date:
        # If dates match, update price_change_value
        changes['date_matches'] += 1
        cian_apartments.at[index, 'price_change_value'] = most_recent['change_clean']
        logger.info(f"Dates match: Updated price_change_value from {old_price_change_value} to {most_recent['change_clean']}")
        changes['price_change_updates'] += 1
    else:
        # If dates don't match, update both updated_time and price_change_value
        changes['date_mismatches'] += 1
        old_updated_time = apartment['updated_time']
        cian_apartments.at[index, 'updated_time'] = most_recent['date_iso']
        cian_apartments.at[index, 'price_change_value'] = most_recent['change_clean']
        logger.info(f"Dates don't match: Updated updated_time from {old_updated_time} to {most_recent['date_iso']}")
        logger.info(f"Updated price_change_value from {old_price_change_value} to {most_recent['change_clean']}")
        changes['price_change_updates'] += 1
        changes['updated_time_updates'] += 1

# Save the updated data back to CSV
output_file = 'updated_cian_apartments.csv'
cian_apartments.to_csv(output_file, index=False)
logger.info(f"Updated data saved to '{output_file}'")

# Log summary statistics
logger.info("\n*** SUMMARY OF CHANGES ***")
logger.info(f"Total offers processed: {changes['offers_processed']}")
logger.info(f"Offers with price history: {changes['offers_with_history']}")
logger.info(f"Offers with matching dates: {changes['date_matches']}")
logger.info(f"Offers with mismatched dates: {changes['date_mismatches']}")
logger.info(f"Price change value updates: {changes['price_change_updates']}")
logger.info(f"Updated time field updates: {changes['updated_time_updates']}")