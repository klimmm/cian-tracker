import re
from datetime import datetime, timedelta

def parse_updated_time(time_str):
    """Parse Cian time format to datetime string"""
    if not time_str:
        return ''
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    months = {
        'янв': 1, 'фев': 2, 'мар': 3, 'апр': 4, 'май': 5, 'июн': 6,
        'июл': 7, 'авг': 8, 'сен': 9, 'окт': 10, 'ноя': 11, 'дек': 12,
    }
    try:
        if 'сегодня' in time_str.lower():
            h, m = map(int, time_str.split(', ')[1].split(':'))
            return today.replace(hour=h, minute=m).strftime('%Y-%m-%d %H:%M:%S')
        if 'вчера' in time_str.lower() and ', ' in time_str:
            h, m = map(int, time_str.split(', ')[1].split(':'))
            return (today - timedelta(days=1)).replace(hour=h, minute=m).strftime('%Y-%m-%d %H:%M:%S')
        if any(x in time_str.lower() for x in ['минут', 'секунд']):
            now = datetime.now()
            if 'минут' in time_str.lower():
                min = int(re.search(r'(\d+)\s+минут', time_str).group(1))
                return (now - timedelta(minutes=min)).strftime('%Y-%m-%d %H:%M:%S')
            sec = int(re.search(r'(\d+)\s+секунд', time_str).group(1))
            return (now - timedelta(seconds=sec)).strftime('%Y-%m-%d %H:%M:%S')
        if ', ' in time_str and any(m in time_str.lower() for m in months.keys()):
            date_part, time_part = time_str.split(', ')
            day = int(re.search(r'(\d+)', date_part).group(1))
            month = next((n for name, n in months.items() if name in date_part.lower()), None)
            if not month:
                return time_str
            h, m = map(int, time_part.split(':'))
            year = today.year
            dt = datetime(year, month, day, h, m)
            if dt > datetime.now() + timedelta(days=1):
                dt = dt.replace(year=year - 1)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        pass
    return time_str