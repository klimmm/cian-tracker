import os, json, logging, re
from datetime import datetime
import pandas as pd
import numpy as np

logger = logging.getLogger('CianScraper')

class CianDataProcessor:
    def __init__(self, csv_filename):
        self.csv_filename = csv_filename

    def finalize_data(self, apartments, existing_df=None):
        if not apartments:
            return existing_df.to_dict('records') if existing_df is not None and not existing_df.empty else []

        try:
            for apt in apartments:
                apt.setdefault('status', 'active')
                apt.setdefault('unpublished_date', '--')

                pcv = apt.get('price_change_value')
                if pcv == 'new':
                    apt.update({'price_change_formatted': 'new', 'price_change': ''})
                elif isinstance(pcv, (int, float)) or str(pcv).replace('.', '', 1).isdigit():
                    price_diff = float(pcv)
                    apt.setdefault('price_change', f"Изменение цены: {price_diff:+,.0f} ₽".replace(',', ' '))
                    if 'price_change_formatted' not in apt or apt['price_change_formatted'] == 'nan':
                        sign = '' if price_diff >= 0 else '-'
                        apt['price_change_formatted'] = f"{sign}{int(abs(price_diff)):,}".replace(',', ' ') + ' ₽/мес.'

            df = pd.DataFrame([{k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict, np.ndarray)) else v for k, v in apt.items()} for apt in apartments])
            if 'offer_id' in df.columns:
                df['offer_id'] = df['offer_id'].astype(str)

            if existing_df is not None and not existing_df.empty:
                df = self.merge_dataframes(df, existing_df)

            df = self.calculate_fields(df)
            if 'updated_time' in df.columns:
                df['updated_time'] = pd.to_datetime(df['updated_time'], errors='coerce')
                df['sort_key'] = df['status'].apply(lambda x: 1 if x == 'active' else 2)
                df = df.sort_values(['sort_key', 'updated_time'], ascending=[True, False]).drop(columns='sort_key')

            result = df.drop_duplicates('offer_id').to_dict('records')
            self.save_data(result)
            return result

        except Exception as e:
            logger.error(f'Error in finalize_data: {e}')
            return apartments or []

    def merge_dataframes(self, current_df, existing_df):
        existing_df['offer_id'] = existing_df['offer_id'].astype(str)
        merged_df = existing_df.copy()
        for col in ['price_change', 'price_change_formatted', 'price_change_value']:
            if col not in merged_df.columns:
                merged_df[col] = ''


        unpublished = current_df[current_df['status'] == 'non active']
        unpub_ids = set(unpublished['offer_id'])

        for _, row in unpublished.iterrows():
            id = row['offer_id']
            idx = merged_df[merged_df['offer_id'] == id].index
            if not idx.empty:
                merged_df.loc[idx[0], ['status', 'unpublished_date']] = 'non active', row.get('unpublished_date', '--')
            else:
                merged_df = pd.concat([merged_df, pd.DataFrame([row])], ignore_index=True)

        for _, row in current_df[~current_df['offer_id'].isin(unpub_ids)].iterrows():
            try:
                id = str(row.get('offer_id', ''))
                if not id:
                    continue
                idx = merged_df[merged_df['offer_id'] == id].index
                if not idx.empty:
                    old_price = self._extract_price_value(merged_df.loc[idx[0], 'price'])
                    new_price = self._extract_price_value(row.get('price', ''))
                    price_changed = old_price is not None and new_price is not None and old_price != new_price

                    old_est = merged_df.loc[idx[0], 'cian_estimation'] if 'cian_estimation' in merged_df.columns else ''
                    new_est = row.get('cian_estimation', '')
                    est_updated = pd.isna(old_est) or str(old_est).strip().lower() in ('', 'nan')
                    est_updated = est_updated and new_est and str(new_est).strip().lower() not in ('', 'nan')

                    if price_changed or est_updated:
                        exclude = {'price_change', 'price_change_value', 'price_change_formatted', 'status', 'unpublished_date'}
                        for col in row.index:
                            if col in merged_df.columns and col not in exclude and pd.notna(row[col]) and row[col] != '':
                                merged_df.loc[idx[0], col] = row[col]

                        if price_changed:
                            diff = new_price - old_price
                            merged_df.loc[idx[0], 'price_change'] = f"From {old_price:,.0f} to {new_price:,.0f} ({diff:+,.0f} ₽)".replace(',', ' ')
                            merged_df.loc[idx[0], 'price_change_value'] = float(diff)
                            merged_df.loc[idx[0], 'price_change_formatted'] = f"{'' if diff >= 0 else '-'}{int(abs(diff)):,}".replace(',', ' ') + ' ₽/мес.'
                else:
                    row_dict = row.to_dict()
                    row_dict.setdefault('price_change_value', 'new')
                    row_dict.setdefault('price_change_formatted', 'new')
                    merged_df = pd.concat([merged_df, pd.DataFrame([row_dict])], ignore_index=True)
            except Exception as e:
                logger.error(f'Error processing row {row.get("offer_id", "unknown")}: {e}')

        for id in unpub_ids:
            idx = merged_df[merged_df['offer_id'] == id].index
            if not idx.empty and merged_df.loc[idx[0], 'status'] != 'non active':
                merged_df.loc[idx[0], 'status'] = 'non active'
                unpub_row = unpublished[unpublished['offer_id'] == id]
                merged_df.loc[idx[0], 'unpublished_date'] = unpub_row.iloc[0].get('unpublished_date', '--') if not unpub_row.empty else '--'

        return merged_df.drop_duplicates('offer_id')

    def calculate_fields(self, df):
        if {'price', 'cian_estimation'}.issubset(df.columns):
            df['price_value'] = df['price'].apply(self._extract_price_value)
            df['estimation_value'] = df['cian_estimation'].apply(self._extract_price_value)
            mask = df['price_value'].notna() & df['estimation_value'].notna()
            df.loc[mask, 'price_difference_value'] = df.loc[mask, 'estimation_value'] - df.loc[mask, 'price_value']
            df['price_difference'] = df['price_difference_value'].apply(lambda x: f"{int(x):,} ₽/мес.".replace(',', ' ') if pd.notna(x) else '')
            df.drop(columns=['price_value', 'estimation_value'], inplace=True, errors='ignore')

        if 'updated_time' in df.columns:
            df['days_active'] = (datetime.now() - pd.to_datetime(df['updated_time'], errors='coerce')).dt.days.astype('Int32')

        df['status'] = df['status'].fillna('active')
        df['unpublished_date'] = df['unpublished_date'].fillna('--')
        return df

    def save_data(self, apartments):
        if not apartments:
            return
        try:
            df = pd.DataFrame(apartments)
            priority_cols = ['offer_id', 'offer_url', 'title', 'updated_time', 'price_change', 'days_active',
                             'price', 'cian_estimation', 'price_difference', 'price_info', 'address',
                             'metro_station', 'neighborhood', 'district', 'description', 'status', 'unpublished_date']
            cols = [c for c in priority_cols if c in df.columns] + [c for c in df.columns if c not in priority_cols and c != 'image_urls']
            df = df[cols]

            for c in df.columns:
                df[c] = df[c].apply(lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, (list, dict, np.ndarray)) else x.strftime('%Y-%m-%d %H:%M:%S') if isinstance(x, pd.Timestamp) else x)

            with open(self.csv_filename + '.tmp', 'w', encoding='utf-8') as f:
                f.write(f'# last_updated={datetime.now().strftime("%Y-%m-%d %H:%M:%S")},record_count={len(df)}\n')
                df.to_csv(f, index=False, encoding='utf-8')
            os.replace(self.csv_filename + '.tmp', self.csv_filename)
            logger.info(f'Saved {len(df)} entries to {self.csv_filename}')

            with open('cian_apartments.json', 'w', encoding='utf-8') as f:
                json.dump([{k: (v.strftime('%Y-%m-%d %H:%M:%S') if isinstance(v, pd.Timestamp) else float(v) if isinstance(v, np.float64) else int(v) if isinstance(v, np.int64) else v) for k, v in apt.items()} for apt in apartments], f, ensure_ascii=False, indent=4)
            logger.info('Saved to cian_apartments.json')

        except Exception as e:
            logger.error(f'Save error: {e}')

    @staticmethod
    def _extract_price_value(price_str):
        if not price_str:
            return None
        if isinstance(price_str, (int, float)):
            return float(price_str)
        digits = re.sub(r'[^\d]', '', str(price_str))
        return float(digits) if digits else None