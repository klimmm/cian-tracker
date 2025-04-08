import re, os, json, logging, traceback
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from distance import get_coordinates, calculate_distance

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("CianProcessor")


def extract_price_value(price_str):
    """Extract numeric value from price string"""
    if price_str is None:
        return None
        
    # If already numeric, just return it
    if isinstance(price_str, (int, float)) and not np.isnan(price_str):
        return float(price_str)
        
    # Handle string values
    try:
        # Remove all non-digit characters
        digits = re.sub(r"[^\d]", "", str(price_str))
        return float(digits) if digits else None
    except (ValueError, TypeError):
        return None


class CianDataProcessor:
    def __init__(self, apartments=None, csv_filename="cian_apartments.csv"):
        self.apartments = apartments or []
        self.csv_filename = csv_filename
        self.existing_data = {}
        self.existing_df = None
        
        # ALWAYS load existing data, regardless of whether apartments are passed
        self.load_existing_data(csv_filename)
        
    def process_and_save_data(self, skip_distance_calculation=False):
        """Main method to process all data and save results"""
        logger.info("Starting data processing...")
        self.add_price_difference()
        self.add_days_from_last_update()
        
        self.sort_by_updated_time(descending=True)
        self.save_to_csv(self.csv_filename)
        self.save_to_json("cian_apartments.json")
        logger.info(f"Data processing complete. Processed {len(self.apartments)} apartments.")
        return self.apartments

    def load_existing_data(self, csv_filename="cian_apartments.csv"):
        """Load existing data for merging and analysis"""
        self.existing_data = {}
        self.existing_df = None
        if os.path.exists(csv_filename):
            try:
                self.existing_df = pd.read_csv(csv_filename, encoding="utf-8", comment="#")
                logger.info(f"Loaded CSV with columns: {self.existing_df.columns.tolist()}")
                
                for _, row in self.existing_df.iterrows():
                    id = str(row.get("offer_id", ""))
                    if id:
                        self.existing_data[id] = row.to_dict()
                logger.info(f"Data processor - Loaded {len(self.existing_data)} existing entries")
            except Exception as e:
                logger.error(f"Error loading data: {e}")
                logger.error(traceback.format_exc())
                self.existing_data = {}
                self.existing_df = pd.DataFrame()
        else:
            logger.warning(f"CSV file {csv_filename} does not exist")
            self.existing_data = {}
            self.existing_df = pd.DataFrame()
        return self.existing_data
        
    def add_price_difference(self):
        """Calculate price difference between listing price and Cian's estimation"""
        logger.info("Adding price difference calculations...")
        
        # Count for logging
        processed_count = 0
        created_count = 0
        error_count = 0
        
        # Log column existence before processing
        if self.apartments:
            columns_before = list(self.apartments[0].keys()) if self.apartments else []
            logger.info(f"Columns before processing: {columns_before}")
        
        for apt in self.apartments:
            try:
                # Extract price value
                pv = extract_price_value(apt.get("price", ""))
                
                # Create cian_estimation_value from cian_estimation if needed
                ev = None
                
                # Check if we already have cian_estimation_value (from previous processing)
                if "cian_estimation_value" in apt and apt["cian_estimation_value"] is not None:
                    # Use existing value but ensure it's numeric
                    try:
                        ev = float(apt["cian_estimation_value"])
                        processed_count += 1
                    except (ValueError, TypeError):
                        # If it's not convertible to float, extract it again
                        original_value = apt["cian_estimation_value"]
                        ev = extract_price_value(original_value)
                        apt["cian_estimation_value"] = ev
                        logger.warning(f"Fixed non-numeric cian_estimation_value: '{original_value}' -> {ev}")
                        created_count += 1
                
                # If we don't have cian_estimation_value, extract it from cian_estimation
                elif "cian_estimation" in apt:
                    cian_est = apt.get("cian_estimation", "")
                    ev = extract_price_value(cian_est)
                    apt["cian_estimation_value"] = ev
                    
                    # Log what we're doing for infoging
                    logger.info(f"Created cian_estimation_value={ev} from cian_estimation='{cian_est}'")
                    created_count += 1
                
                # Always ensure cian_estimation_value exists (even if null)
                if "cian_estimation_value" not in apt:
                    apt["cian_estimation_value"] = None
                
                # Calculate price difference if possible
                if pv is not None and ev is not None:
                    diff = ev - pv
                    apt["price_difference_value"] = diff
                    logger.info(f"Calculated price_difference_value={diff} from price={pv} and cian_estimation_value={ev}")
                else:
                    apt["price_difference_value"] = None
                    
            except Exception as e:
                logger.error(f"Error calculating price diff: {e}")
                logger.error(traceback.format_exc())
                # Ensure these fields exist even in case of error
                apt["cian_estimation_value"] = None
                apt["price_difference_value"] = None
                error_count += 1
        
        # Log stats and check the results
        logger.info(f"Price difference calculation complete: {processed_count} processed, "
                    f"{created_count} created, {error_count} errors")
        
        # Verify columns after processing
        if self.apartments:
            sample_apt = self.apartments[0]
            columns_after = list(sample_apt.keys())
            logger.info(f"Columns after processing: {columns_after}")
            logger.info(f"cian_estimation_value exists in first apartment: {'cian_estimation_value' in sample_apt}")
            logger.info(f"Sample cian_estimation_value: {sample_apt.get('cian_estimation_value')}")
        
        return self.apartments

    def add_days_from_last_update(self):
        """Calculate how many days the listing has been active"""
        logger.info("Calculating days active for all listings...")
        now = datetime.now()
        for apt in self.apartments:
            t_str = apt.get("updated_time", "")
            if t_str:
                try:
                    t = datetime.strptime(t_str, "%Y-%m-%d %H:%M:%S")
                    apt["days_active"] = (now - t).days
                except (ValueError, TypeError):
                    apt["days_active"] = None
            else:
                apt["days_active"] = None
        return self.apartments

    def sort_by_updated_time(self, descending=True):
        """Sort apartments by update time"""
        logger.info("Sorting apartments by update time...")
        def parse_date(d):
            if not d:
                return datetime(1900, 1, 1)
            try:
                return datetime.strptime(d, "%Y-%m-%d %H:%M:%S")
            except:
                return datetime(1900, 1, 1)

        self.apartments.sort(
            key=lambda x: parse_date(x.get("updated_time", "")), reverse=descending
        )
        return self.apartments


    def add_distances(self, reference_address="Москва, переулок Большой Саввинский, 3"):
        """
        Process all apartment distances:
        1. Preserve valid existing distance values
        2. Calculate distances only for apartments with missing or invalid values
        """
        logger.info("Processing distances for all apartments...")
        
        # Count statistics
        preserved_count = 0
        invalid_count = 0
        calculated_count = 0
        error_count = 0
        
        try:
            # Get reference coordinates once (outside the loop)
            reference_coords = get_coordinates(reference_address)
            logger.info(f"Reference coordinates for distance calculation: {reference_coords}")
            
            # Process each apartment
            for apt in self.apartments:
                # Check existing distance value
                distance = apt.get("distance")
                logger.info(f"Processing apartment with distance {distance}")
                
                # Case 1: Distance exists and might be valid
                if distance is not None and distance != "":
                    try:
                        # Convert to float if needed
                        if isinstance(distance, str):
                            distance_val = float(distance)
                        else:
                            distance_val = distance
                        
                        # Check if the value is valid (not NaN or infinite)
                        if not np.isnan(distance_val) and not np.isinf(distance_val):
                            # Valid distance - preserve it
                            apt["distance"] = distance_val  # Store as float
                            preserved_count += 1
                            continue
                        else:
                            # Invalid numerical value
                            invalid_count += 1
                    except (ValueError, TypeError):
                        # Conversion failed
                        invalid_count += 1
                
                # If we get here, we need to calculate the distance
                try:
                    # Get the address
                    address = apt.get("address", "")
                    if not address:
                        logger.info(f"Missing address for apartment {apt.get('offer_id', 'unknown')}")
                        error_count += 1
                        continue
    
                    # Add city to address if not present
                    full_address = address
                    if "Москва" not in address:
                        full_address = f"Москва, {address}"
    
                    distance_km = calculate_distance(
                        from_point=reference_coords,
                        to_address=full_address
                    )

                    apt["distance"] = round(distance_km, 2)
                    calculated_count += 1
                    
                    # Log progress periodically
                    if (calculated_count + preserved_count) % 10 == 0:
                        logger.info(f"Processed {calculated_count + preserved_count}/{len(self.apartments)} distances")
                    
                except Exception as e:
                    logger.error(f"Error calculating distance for {address}: {e}")
                    error_count += 1
            
            # Final statistics
            logger.info(f"Distance processing complete:")
            logger.info(f"  - Preserved: {preserved_count} valid distances")
            logger.info(f"  - Calculated: {calculated_count} new distances")
            logger.info(f"  - Failed: {error_count} addresses")
            logger.info(f"  - Invalid values found: {invalid_count}")
            
        except Exception as e:
            logger.error(f"Error in distance calculation process: {e}")
            logger.error(traceback.format_exc())
        
        return self.apartments

    def format_price(self, value):
        """Format price value to human-readable string"""
        if value is None:
            return ""
        return f"{'{:,}'.format(int(value)).replace(',', ' ')} ₽/мес."

    def save_to_csv(self, filename="cian_apartments.csv"):
        """Save processed data to CSV file with metadata"""
        try:
            if not self.apartments:
                logger.warning("No data to save")
                return
                
            # Define columns to save - explicitly include cian_estimation_value
            cols = [
                "offer_id",
                "offer_url",
                "title",
                "updated_time",
                "days_active",
                "price",
                "cian_estimation_value",  # Explicitly include this
                "price_difference_value", # Explicitly include this
                "price_info",
                "address",
                "metro_station",
                "neighborhood",
                "district",
                "description",
            ]
            
            df = pd.DataFrame(self.apartments)
            
            # Log columns in the DataFrame before saving
            logger.info(f"Columns in DataFrame before saving: {df.columns.tolist()}")
            logger.info(f"cian_estimation_value in DataFrame: {'cian_estimation_value' in df.columns}")
            
            # If cian_estimation_value doesn't exist, create it with None values
            if 'cian_estimation_value' not in df.columns:
                logger.warning("cian_estimation_value missing in DataFrame, creating it with NaN values")
                df['cian_estimation_value'] = np.nan
            
            # Count non-null values
            if 'cian_estimation_value' in df.columns:
                non_null = df['cian_estimation_value'].notna().sum()
                logger.info(f"cian_estimation_value: {non_null}/{len(df)} non-null values")
                # Log some sample values
                sample_values = df['cian_estimation_value'].head(5).tolist()
                logger.info(f"Sample cian_estimation_value: {sample_values}")

            # Add any columns in df that aren't in cols list
            cols = [c for c in cols if c in df.columns]
            for c in df.columns:
                if c not in cols and c != "image_urls":
                    cols.append(c)

            df_save = df[cols].copy()

            # Modified serialization function to handle arrays properly
            for c in df_save.columns:
                def serialize(x):
                    try:
                        if isinstance(x, np.ndarray):
                            return json.dumps(x.tolist(), ensure_ascii=False)
                        elif isinstance(x, (list, dict)):
                            return json.dumps(x, ensure_ascii=False)
                        elif isinstance(
                            x, (str, int, float, bool, type(None), np.generic)
                        ):
                            return x
                        else:
                            return str(x)
                    except Exception as e:
                        return str(x)

                df_save[c] = df_save[c].apply(serialize)

            # Create a temporary file with metadata
            with open(filename + ".tmp", "w", encoding="utf-8") as f:
                # Write metadata as a comment line
                update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                record_count = len(df_save)
                f.write(f"# last_updated={update_time},record_count={record_count}\n")
                
                # Write the actual data without index
                df_save.to_csv(f, index=False, encoding="utf-8")
                
            # Check the temp file to ensure cian_estimation_value was written
            try:
                df_check = pd.read_csv(filename + ".tmp", comment="#", encoding="utf-8")
                logger.info(f"Columns in temp CSV: {df_check.columns.tolist()}")
                logger.info(f"cian_estimation_value in temp CSV: {'cian_estimation_value' in df_check.columns}")
            except Exception as e:
                logger.error(f"Error checking temp CSV: {e}")
                
            # Replace the original file with the temp file
            os.replace(filename + ".tmp", filename)
            logger.info(f"Saved to {filename}: {len(df)} entries with metadata")
        except Exception as e:
            logger.error(f"CSV save error: {e}")
            logger.error(traceback.format_exc())

    def save_to_json(self, filename="cian_apartments.json"):
        """Save processed data to JSON file"""
        if not self.apartments:
            logger.warning("No data to save")
            return
        
        # Ensure all apartments have cian_estimation_value
        for apt in self.apartments:
            if "cian_estimation_value" not in apt:
                apt["cian_estimation_value"] = None
                
            # Convert timestamps
            for k, v in apt.items():
                if isinstance(v, pd.Timestamp):
                    apt[k] = v.strftime("%Y-%m-%d %H:%M:%S")
                    
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(self.apartments, f, ensure_ascii=False, indent=4)
            logger.info(f"Saved to {filename}")
        except Exception as e:
            logger.error(f"JSON save error: {e}")
            logger.error(traceback.format_exc())


if __name__ == "__main__":
    # Example of using the processor independently (without scraping)
    # This is useful for reprocessing existing data or applying new calculations
    
    processor = CianDataProcessor(csv_filename="cian_apartments.csv")
    processor.load_existing_data()
    
    # Add or update specific calculations
    processor.add_price_difference()  # Make sure this runs first
    processor.add_days_from_last_update()
    
    # Save the reprocessed data
    processor.save_to_csv()
    processor.save_to_json()
    
    logger.info("Reprocessing complete")