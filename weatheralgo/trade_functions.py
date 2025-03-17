import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from selenium.webdriver.common.by import By

import xml.etree.ElementTree as ET
import logging
import uuid

from weatheralgo.clients import client
from weatheralgo import util_functions



def trade_execution(market: str, temperatures: list, yes_price: int, count: int, timezone):
    try:
        highest_temp = np.array(temperatures).max()
        highest_temp = int(highest_temp)
        market_ticker = util_functions.order_pipeline(highest_temp=highest_temp, market=market, timezone=timezone)
        
        balance_min = count * yes_price
        balance = client.get_balance()['balance'] > balance_min
        
        if balance:          
            logging.info('order_pipeline worked')
            order_id = str(uuid.uuid4())
            client.create_order(ticker=market_ticker, client_order_id=order_id,  yes_price=yes_price, count=count)
            logging.info(f'Order Submitted {market_ticker}')
          
            return True
        else:
            return False
    
    except Exception as e:
        logging.info(f'trade_execution : {e}')
    
def if_temp_reaches_max(current_temp: int, market: str, yes_price: int, count: int, temperatures: list, timezone):
    try:
        market_temp_max = list(util_functions.weather_config(market=market, timezone=timezone).items())[-1][1]
        
        balance_min = count * yes_price
        balance = client.get_balance()['balance'] > balance_min
        
        if current_temp >= market_temp_max and balance:
            trade_execution(market=market, temperatures=temperatures, yes_price=yes_price, count=count, timezone=timezone)
            logging.info(f"Max temp reached and order created {current_temp}")
         
            return True
        else:
            return False
    except Exception as e:
        logging.info(f'if_temp_reaches_max : {e}')
    
    
def trade_criteria_met(temperatures: list, lr_length: int, 
                       market: str, yes_price: int, count: int, timezone):
    try:
        highest_temp = int(np.array(temperatures).max())
        order_pipeline_check = util_functions.order_pipeline(highest_temp=highest_temp, market=market, timezone=timezone)
        
        length = len(temperatures) >= lr_length

        if order_pipeline_check and length:
            x = np.arange(0, lr_length).reshape(-1,1)
            temp_length = temperatures[-lr_length:]
            regressor = LinearRegression().fit(x, temp_length)
            slope = regressor.coef_
            if slope < 0:
                logging.info(f"Slope: {slope}")
                logging.info(f"X: {temp_length}")
                logging.info(f"Max Temp: {highest_temp}")
                trade_execution(market=market, temperatures=temperatures, yes_price=yes_price, count=count, timezone=timezone)
                #consider making it True if trade_execution is trade_execution is True or False
                return True
            else:
                return False
        else:
            False
    except Exception as e:
        logging.error(f"Error in trade_criteria_met: {e}")
        
    
    
def max_or_trade_criteria_met(current_temp: int, market: str, yes_price: int, count: int, temperatures: list, timezone, lr_length: int):
    
    try:
    
        current_temp_is_max = if_temp_reaches_max(
                                                current_temp=current_temp, 
                                                market = market, 
                                                yes_price=yes_price,
                                                count=count,
                                                temperatures=temperatures,
                                                timezone=timezone
                                                )
        trade_criteria = trade_criteria_met(
                                            temperatures=temperatures, 
                                            lr_length=lr_length,
                                            market=market,
                                            yes_price=yes_price,
                                            count=count,
                                            timezone=timezone,
                                            )
                        
        if current_temp_is_max:
            logging.info(f'Max Temperature Reached {market}')
            trade_executed = True
            return trade_executed

            

        elif trade_criteria:
            logging.info(f'Trade Criteria Met {market}')
            trade_executed = True
            return trade_executed
        
        else:
            return None
    
    
            
    except Exception as e:
        logging.info(f'max_or_trade_criteria_met: {e}')
        return None
    
   
    
