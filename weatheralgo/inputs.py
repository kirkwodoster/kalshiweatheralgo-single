
import pytz
from datetime import datetime
from weatheralgo import scrape_functions
import logging

lr_length = 5
hour = 7
scraping_hours = [45,30]
yes_price = 85
count = 1


all_markets = {
            "DENVER": {
                "SERIES": "KXHIGHDEN",
                "TIMEZONE":"America/Denver",
                "URL": f"https://www.weather.gov/wrh/timeseries?site=KDEN&hours={hour}",
                "XML_URL": "https://forecast.weather.gov/MapClick.php?lat=39.8589&lon=-104.6733&FcstType=digitalDWML",
            },
            "CHICAGO": {
                "SERIES": "KXHIGHCHI",
                "TIMEZONE":"America/Chicago",
                "URL": f"https://www.weather.gov/wrh/timeseries?site=KMDW&hours={hour}",
                "XML_URL": "https://forecast.weather.gov/MapClick.php?lat=41.7842&lon=-87.7553&FcstType=digitalDWML",
            },
            "MIAMI": {
                "SERIES": "KXHIGHMIA",
                "TIMEZONE":"US/Eastern",
                "URL": f"https://www.weather.gov/wrh/timeseries?site=KMIA&hours={hour}",
                "XML_URL": "https://forecast.weather.gov/MapClick.php?lat=25.7934&lon=-80.2901&FcstType=digitalDWML",
            },
            "AUSTIN": {
                "SERIES": "KXHIGHAUS",
                "TIMEZONE":"US/Central",
                "URL": f"https://www.weather.gov/wrh/timeseries?site=KAUS&hours={hour}",
                "XML_URL": "https://forecast.weather.gov/MapClick.php?lat=30.1945&lon=-97.6699&FcstType=digitalDWML",
            },
            "PHILADELPHIA": {
                "SERIES": "KXHIGHPHIL",
                "TIMEZONE":"US/Eastern",
                "URL": f"https://www.weather.gov/wrh/timeseries?site=KPHL&hours={hour}",
                "XML_URL": "https://forecast.weather.gov/MapClick.php?lat=39.8721&lon=-75.2407&FcstType=digitalDWML",
            },
            "LOS ANGELES": {
                "SERIES":"KXHIGHLAX",
                "TIMEZONE":"America/Los_Angeles",
                "URL": f"https://www.weather.gov/wrh/timeseries?site=KLAX&hours={hour}",
                "XML_URL": "https://forecast.weather.gov/MapClick.php?lat=33.9425&lon=-118.409&FcstType=digitalDWML",
            }
        }


    
market_dict = {
        "KXHIGHDEN": {
            'current_timezone':None,
            'forecasted_high':None,
            'trade_executed':None
            },
        "KXHIGHCHI": {
            'current_timezone':None,
            'forecasted_high':None,
            'trade_executed':None
            },
        "KXHIGHMIA": {
            'current_timezone':None,
            'forecasted_high':None,
            'trade_executed':None
            },
        "KXHIGHAUS": {
            'current_timezone':None,
            'forecasted_high':None,
            'trade_executed':None
            },
        "KXHIGHPHIL": {
            'current_timezone':None,
            'forecasted_high':None,
            'trade_executed':None
            },
        "KXHIGHLAX": {
            'current_timezone':None,
            'forecasted_high':None,
            'trade_executed':None
            },
                }


locations = all_markets.keys()
market_inputs = list(all_markets['DENVER'].keys())

scrape_inputs = {
    'lr_length': lr_length,
    'count': count,
    'scraping_hours': scraping_hours,
    'yes_price': yes_price,
    'locations': locations      
                }


def model_input(markets):
    try:
        market = all_markets[markets]['SERIES']
        timezone =  pytz.timezone(all_markets[markets]['TIMEZONE'])
        url = all_markets[markets]['URL']
        xml_url = all_markets[markets]['XML_URL']
        return market, timezone, url, xml_url
    
    except Exception as e:
        logging.error(f"model_input: {e}")



def forecasted_high_gate(market_dict, market, xml_url, timezone):
    
    try:
        current_timezone = datetime.now(timezone)

        if market_dict[market]['current_timezone'] != current_timezone.date():
            
            current_timezone = datetime.now(timezone)
            expected_high_date = scrape_functions.xml_scrape(xml_url, timezone)[0]

            return current_timezone, expected_high_date
        else:
            return False
    except Exception as e:
        logging.error(f"forecasted_high_gate: {e}")
    



    

