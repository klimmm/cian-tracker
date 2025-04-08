from cian_parser import CianScraper
from cian_processor import CianDataProcessor
from details_fetcher import CianDetailFetcher
from listings_collector import CianListingCollector


if __name__ == '__main__':
    # Example usage
    csv_file = 'cian_apartments.csv'
    base_url = 'https://www.cian.ru/cat.php?currency=2&deal_type=rent&engine_version=2&maxprice=64000&metro%5B0%5D=118&minprice=64000&offer_type=flat&room1=1&room2=1&type=4'
    
    # Create scraper and run full workflow
    scraper = CianScraper(headless=True, csv_filename=csv_file)
    apartments = scraper.scrape(
        search_url=base_url,
        max_pages=20,
        max_distance_km=5
    )

    collector = CianListingCollector(base_url, self.chrome_options)



    
    print(f'Total apartments processed: {len(apartments)}')