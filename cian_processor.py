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
    if not price_str:
        return None
    if isinstance(price_str, (int, float)):
        return float(price_str)
    digits = re.sub(r"[^\d]", "", str(price_str))
    try:
        return float(digits) if digits else None
    except ValueError:
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
        self.merge_with_existing_data()
        
        if not skip_distance_calculation:
            self.add_distances()
            
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
                for _, row in self.existing_df.iterrows():
                    id = str(row.get("offer_id", ""))
                    if id:
                        self.existing_data[id] = row.to_dict()
                logger.info(f" data processor - Loaded {len(self.existing_data)} existing entries")
            except Exception as e:
                logger.error(f"Error loading data: {e}")
                self.existing_data = {}
                self.existing_df = pd.DataFrame()
        else:
            self.existing_data = {}
            self.existing_df = pd.DataFrame()
        return self.existing_data
    def add_price_difference(self):
        """Calculate price difference between listing price and Cian's estimation"""
        logger.info("Adding price difference calculations...")
        for apt in self.apartments:
            try:
                pv = extract_price_value(apt.get("price", ""))
                # Create cian_estimation_value from cian_estimation
                ev = extract_price_value(apt.get("cian_estimation", ""))
                if ev is not None:
                    apt["cian_estimation_value"] = ev
                    # Remove the formatted cian_estimation field
                    if "cian_estimation" in apt:
                        del apt["cian_estimation"]
                    
                if pv is not None and ev is not None:
                    diff = ev - pv
                    apt["price_difference_value"] = diff
                    # No longer create price_difference (formatted version)
                else:
                    apt["price_difference_value"] = None
            except Exception as e:
                logger.error(f"Error calculating price diff: {e}")
                apt["price_difference_value"] = None
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

    def merge_with_existing_data(self):
        """
        Merge newly scraped data with existing data to ensure no apartments are lost
        """
        logger.info("Merging with existing data...")
        
        # If no existing data, nothing to merge
        if not hasattr(self, "existing_df") or self.existing_df is None or self.existing_df.empty:
            logger.info("No existing data to merge")
            return self.apartments
            
        # If no new data but we have existing data, use existing data
        if not self.apartments:
            logger.info("No new apartments, using existing data")
            self.apartments = self.existing_df.to_dict("records")
            return self.apartments
        
        # Convert new data to DataFrame for easier merging
        current_df = pd.DataFrame(self.apartments)
        
        # Create merged DataFrame starting with existing data
        merged_df = self.existing_df.copy()
        
        # Ensure offer_id is string type for consistent comparison
        for df in [current_df, merged_df]:
            if "offer_id" in df.columns:
                df["offer_id"] = df["offer_id"].astype(str)

        for _, row in current_df.iterrows():
            id = row.get("offer_id", "")
            if not id:
                continue
                
            idx = merged_df[merged_df["offer_id"] == id].index
            if len(idx) > 0:
                # Check if this is a full update or partial update
                cols_with_data = [col for col in row.index if pd.notna(row[col]) and row[col] != ""]
                
                # If it's a partial update (like just cian_estimation), only update those fields
                for col in cols_with_data:
                    if col in merged_df.columns:
                        merged_df.loc[idx[0], col] = row[col]
            else:
                # New apartment
                merged_df = pd.concat([merged_df, pd.DataFrame([row])], ignore_index=True)

        # Cleanup and sort the data
        merged_df = merged_df.drop_duplicates(subset=["offer_id"], keep="first")
        if "updated_time" in merged_df.columns:
            merged_df["updated_time"] = pd.to_datetime(
                merged_df["updated_time"],
                format="%Y-%m-%d %H:%M:%S",
                errors="coerce"
            )
            merged_df = merged_df.sort_values("updated_time", ascending=False)
        
        self.apartments = merged_df.to_dict("records")
        logger.info(f"Merged data contains {len(self.apartments)} apartments")
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
            logger.debug(f"Reference coordinates for distance calculation: {reference_coords}")
            
            # Process each apartment
            for apt in self.apartments:
                # Check existing distance value
                distance = apt.get("distance")
                logger.warning(f" distance {distance}")
                # Case 1: Distance exists and might be valid
                if distance is not None and distance != "":
                    try:
                        # Convert to float if needed
                        if isinstance(distance, str):
                            distance_val = float(distance)
                        else:
                            distance_val = distance
                        logger.debug(f" distance_val {distance_val}")
                        # Check if the value is valid (not NaN or infinite)
                        if not np.isnan(distance_val) and not np.isinf(distance_val):
                            # Valid distance - preserve it
                            logger.debug(f"preserved distance_val {distance_val}")
                                
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
                        logger.debug(f"Missing address for apartment {apt.get('offer_id', 'unknown')}")
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
            # Define columns to save
            cols = [
                "offer_id",
                "offer_url",
                "title",
                "updated_time",
                "days_active",
                "price",
                "price_difference",
                "price_difference_value",
                "price_info",
                "address",
                "metro_station",
                "neighborhood",
                "district",
                "description",
            ]
            df = pd.DataFrame(self.apartments)
    
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
                
            # Replace the original file with the temp file
            os.replace(filename + ".tmp", filename)
            logger.info(f"Saved to {filename}: {len(df)} entries with metadata")
        except Exception as e:
            logger.error(f"CSV save error: {e}")
            logger.warning(traceback.format_exc()) 

    def save_to_json(self, filename="cian_apartments.json"):
        """Save processed data to JSON file"""
        if not self.apartments:
            logger.warning("No data to save")
            return
        for apt in self.apartments:
            for k, v in apt.items():
                if isinstance(v, pd.Timestamp):
                    apt[k] = v.strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(self.apartments, f, ensure_ascii=False, indent=4)
            logger.info(f"Saved to {filename}")
        except Exception as e:
            logger.error(f"JSON save error: {e}")


if __name__ == "__main__":
    # Example of using the processor independently (without scraping)
    # This is useful for reprocessing existing data or applying new calculations
    
    processor = CianDataProcessor(csv_filename="cian_apartments.csv")
    processor.load_existing_data()
    
    # Add or update specific calculations
    processor.add_distances()  
    processor.add_days_from_last_update()
    
    # Save the reprocessed data
    processor.save_to_csv()
    processor.save_to_json()
    
    logger.info("Reprocessing complete")