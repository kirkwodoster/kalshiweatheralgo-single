import logging
import pandas as pd
from selenium.webdriver.common.by import By
from datetime import datetime, timedelta
from dateutil import tz
import pytz
import requests
import xml.etree.ElementTree as ET

from weatheralgo.clients import client
from weatheralgo import scrape_functions
from weatheralgo import trade_functions
from weatheralgo import util_functions

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

    
def scrape_temperature(driver, url, timezone) -> list[str, float]:
    
    try:
        driver.get(url)
        WebDriverWait(driver, 1).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'path[fill="#2caffe"]'))
        )
        path_elements = driver.find_elements(By.CSS_SELECTOR, 'path[fill="#2caffe"]')

        datetemp_list = [path.get_attribute("aria-label") for path in path_elements]
       
        date = [', '.join(i.split(', ')[0:3]) for i in datetemp_list]
        temp = [float(i.split(', ')[-1].split(' ')[0][:-1]) for i in datetemp_list]
        
        day = datetime.now(timezone).day
        
        date = [i for i,j in zip(date, temp) if datetime.strptime(i, '%A, %b %d, %I:%M %p').day == day]
        temp = [j for i,j in zip(date, temp) if datetime.strptime(i, '%A, %b %d, %I:%M %p').day == day]
    
        return [date, temp]  # Return date and temperature
        
    except Exception as e:
        logging.error(f"Error scrape_temperature: {e}")
        return None
    
def xml_scrape(xml_url, timezone):

    try:
        response = requests.get(xml_url)
        root = ET.fromstring(response.content)

        start_times = root.findall('.//start-valid-time')
        dates = [time.text for time in start_times]

        temperature_element = root.find('.//temperature[@type="hourly"]')
        value_elements = temperature_element.findall('.//value')
        temp = [int(value.text) for value in value_elements if isinstance(value.text, str)]
        temp_length = len(temp)
 
        forecasted = pd.DataFrame({'DateTime': dates[:temp_length], 'Temperature': temp})
        forecasted['DateTime'] = pd.to_datetime(forecasted['DateTime'])
        forecasted = forecasted.sort_values(by='DateTime')

        denver_today = datetime.now(timezone).day

        next_day_high = forecasted[forecasted['DateTime'].dt.day == denver_today]['Temperature'].idxmax() #[::-1]
        date = forecasted['DateTime'].iloc[next_day_high]
        hour_of_high = forecasted['DateTime'].iloc[next_day_high].hour
        temp_high = forecasted['Temperature'].iloc[next_day_high]

        return [date, hour_of_high, temp_high]

    except Exception as e:
      print(e)


def iso_to_local_time(iso_string, timezone):
    
    utc_time = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
    local_tz = tz.gettz(timezone)
    local_time = utc_time.astimezone(local_tz).date()
    
    return local_time.isoformat()

def trade_today(market, timezone):

    try:
        today = datetime.now(timezone)
        todays_date = today.strftime('%y%b%d').upper()
        event = f'{market}-{todays_date}'
        orders = client.get_orders(event_ticker=event)['orders']
    
        if len(orders) >= 1:
            order_list = [iso_to_local_time(iso_string = i['created_time'], timezone=str(timezone)) for i in orders]
            if str(today.date()) in order_list:
             
                return True
            else:
                return False
        else:
            return False

    except Exception as e:
        logging.error(f"Error Trade Today: {e}")

def begin_scrape(scraping_hours, forecasted_high_date, timezone):
    
    try:
        today = datetime.now(timezone)

        start_scrape = today >= forecasted_high_date - timedelta(minutes=scraping_hours[0])
        end_scrape = today <= forecasted_high_date + timedelta(minutes=scraping_hours[1])
        
        # time_limit_lower = today.hour >= 3
        # time_limit_upper = today.hour <= 23

        if all([start_scrape, end_scrape]):
            return True
        else:
            return False
    except Exception as e:
        logging.error(f"Error in begin_scrape: {e}")

def permission_to_scrape(market, timezone, scraping_hours, forecasted_high_date, market_dict):
       
    trade_today_check = trade_today(market, timezone)
    begin_scrape_check = begin_scrape(scraping_hours, forecasted_high_date, timezone)
    market_dict_check = market_dict[market]['trade_executed'] == None

    
    if all([not trade_today_check, begin_scrape_check, market_dict_check]): #timezone_lower_bound, timezone_upper_bound,
        print('True')
    
        return True
    else:
        return False
    
    

def scrape_trade(market, timezone, scraping_hours, market_dict, driver, url,
                 lr_length, yes_price, count, forecasted_high_date):
    
    permission_scrape = scrape_functions.permission_to_scrape(
                                                            market=market, 
                                                            timezone=timezone, 
                                                            scraping_hours=scraping_hours, 
                                                            forecasted_high_date=forecasted_high_date,
                                                            market_dict=market_dict
                                                            )
    
    is_order_filled = util_functions.order_filled(market=market, timezone=timezone)
    
    if permission_scrape:
        scrape = scrape_functions.scrape_temperature(driver=driver, url=url, timezone=timezone)
        current_temp = scrape[1][-1]
        temperatures = scrape[1]
        
        print(f'Market: {market}')
        print(f'Current Temp: {current_temp}')
        print(f'Temperature: {temperatures}')
        print(f'expected high date {forecasted_high_date}')
        print(market_dict[market]['trade_executed'])
        
        trade_execution = trade_functions.max_or_trade_criteria_met(
                                                            current_temp=current_temp,
                                                            market = market, 
                                                            yes_price=yes_price,
                                                            count=count,
                                                            temperatures=temperatures,
                                                            timezone=timezone,
                                                            lr_length=lr_length,
                                                            )
        
        if trade_execution:
            # market_dict[market]['trade_executed'] = trade_execution
            return trade_execution
                        
        if is_order_filled:
            logging.info(f'Order filled and saved: {market}')
            
        
        
        
    
        

    