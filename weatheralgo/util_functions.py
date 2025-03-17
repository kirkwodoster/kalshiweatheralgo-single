import csv
import logging
from datetime import datetime
import logging
import shelve



from weatheralgo.clients import client

   
def trade_to_csv(order_id : str, ticker: str):
    try:
        trade_data = client.get_fills(order_id = order_id)['fills'][0]
        #Formatting Time
        raw_date = trade_data['created_time']
        raw_date = datetime.strptime(raw_date, '%Y-%m-%dT%H:%M:%S.%fZ')  
        year = raw_date.strftime('%Y-%m-%d')
        time = raw_date.strftime('%H:%M:%S')
        #Ticker
        ticker = trade_data['ticker']
        #Side
        side = trade_data['side']
        #fees
        take_fees = client.get_orders(ticker=ticker)['orders'][0]['taker_fees']
        taker_fill_cost = client.get_orders(ticker=ticker)['orders'][0]['taker_fill_cost']
        fees = take_fees + taker_fill_cost
        #Price
        if side == 'yes':
            price = trade_data['yes_price']
        else:
            price = trade_data['no_price']
        #Portfolio Total
        portfolio_total = client.get_balance()['balance']

        data_to_csv = {
            'year': year,
            'time': time,
            'order_id': order_id,
            'ticker': ticker,
            'side': side,
            'price': price,
            'fees': fees,
            'revenue': None,
            'portfolio_total': portfolio_total
                        }
        
        column_names = data_to_csv.keys()

        with open('util/data/trade_data.csv', 'a', newline='') as file:
            writer = csv.DictWriter(file, column_names)
            writer.writerow(data_to_csv)
            
        return None
    except Exception as e:
        logging.error(f"Error in CSV Write: {e}")


def weather_config(market, timezone): 
    try:
        today = datetime.now(timezone)
        todays_date = today.strftime('%y%b%d').upper()
        event_ticker = f'{market}-{todays_date}'
            
        event_list = []
        events = client.get_event(event_ticker)  # Ensure getEvent is defined or imported
        for i in range(len(events['markets'])):
            event_list.append(events['markets'][i]['ticker'])

        #temp_adj = []
        temp_adj = []

        event_list = [i.split('-', 2)[-1] for i in event_list]
        counter = 0
        for i in event_list:
            if "T" in i:
                counter += 1
                remove_t = i.strip('T')
                if counter == 1:
                    temp_adj.append(int(remove_t)-2)
                elif counter == 2:
                    temp_adj.append(int(remove_t)+1) # adjust for rounding error
                    
            elif "B" in i:
                remove_b = i.strip('B')
                temp_minus_5 = float(remove_b) - .5
                #temp_add_5 = float(remove_b) + .5
                #degree_range = [int(temp_minus_5) , int(temp_add_5)]
                temp_adj.append(int(temp_minus_5))

        degree_dictionary = {k: v for k, v in zip(event_list, temp_adj)}
       
        return degree_dictionary
    
    except Exception as e:
        logging.info(f'weather_config: {e}')
    

def order_pipeline(highest_temp: int, market: str, timezone):
    
    try:
        today = datetime.now(timezone)
        todaysDate = today.strftime('%y%b%d').upper()
        event = f'{market}-{todaysDate}'

    # tempMarket = None
        listofMarkets = weather_config(market=market, timezone=timezone)
        minMarketTemp = list(listofMarkets.values())[0]
        maxMarketTemp = list(listofMarkets.values())[-1]
        listofMarketsAdj = dict(list(listofMarkets.items())[1:-1])

        if highest_temp <= minMarketTemp:
            tempMarket = list(listofMarkets)[0]
        elif highest_temp >= maxMarketTemp:
            tempMarket = list(listofMarkets)[-1]
        else:
            for key, value in listofMarketsAdj.items():
                if highest_temp == value:
                    tempMarket = key

        if tempMarket:        
            return f'{event}-{tempMarket}'
        else:
            return False
            
    except Exception as e:
         if "tempMarket" not in  str(e):
            logging.info(f"order_pipeline {e}")
    except:
        None

def order_filled(market, timezone):
    try:
        market_ticker = weather_config(market=market, timezone=timezone)
        orders = client.get_orders(ticker=market_ticker)['orders']
        
        if orders:  # Check if there are any orders
            order = orders[0]
            filled = order['status']
            
            if filled == 'executed':
                order_id = order['order_id']
                logging.info(f'Order Executed {market_ticker}')
                trade_to_csv(order_id=order_id, ticker=market_ticker)
                logging.info(f'Trade {market_ticker} saved')
            else:
                # Do nothing if the order status is not 'executed'
                pass
        
    except Exception as e:
        logging.error(f"Order Filled error: {e}")
            
filepath = 'util/data/database/market_dict'      

def market_dict_update(market_dict):
    with shelve.open(filepath) as db:
        db['market_dict'] = market_dict
        
def retrieve_market_dict():
    with shelve.open(filepath) as db:
        return dict(db)['market_dict']
        
    
    
            
            
def logging_settings():
    return logging.basicConfig(
    level=logging.INFO,  # Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format="%(asctime)s - %(levelname)s - %(message)s",  # Define the log format
    handlers=[logging.StreamHandler()]  # Output logs to the terminal
)
