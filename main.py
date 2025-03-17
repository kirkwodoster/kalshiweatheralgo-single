#from cryptography.hazmat.primitives import serialization
#import asyncio
# from weatheralgo.clients import  KalshiWebSocketClient
import logging
import pytz

from weatheralgo.model import weather_model
from weatheralgo import util_functions
from weatheralgo import scrape_functions
from weatheralgo import trade_functions
from weatheralgo.clients import client
from datetime import datetime, timedelta
import pytz
import time
import numpy as np
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from dateutil import tz

from weatheralgo import inputs

# from weatheralgo.clients import client



# Initialize the WebSocket client
# ws_client = KalshiWebSocketClient(
#     key_id=client.key_id,
#     private_key=client.private_key,
#     environment=client.environment
# )

# Connect via WebSocket
# asyncio.run(ws_client.connect())

if __name__ == "__main__":
        
    driver =  weather_model.initialize_driver()

    scraping_inputs = inputs.scrape_inputs
    
    util_functions.logging_settings()
    
    try:
       weather_model.scrape_dynamic_table(driver, **scraping_inputs)
        # scrape_functions.scrape_temperature(driver=driver,url=url)
    except KeyboardInterrupt:
        logging.info("Script interrupted by user.")
    finally:
        driver.quit()
        logging.info("WebDriver closed.")
        time.sleep(15)
        weather_model.scrape_dynamic_table(driver, **scraping_inputs)

