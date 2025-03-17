import requests
import base64
import time
from typing import Any, Dict, Optional, Required
from datetime import datetime, timedelta
from enum import Enum
import json
from requests.exceptions import HTTPError
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.exceptions import InvalidSignature
from dotenv import load_dotenv
import websockets



load_dotenv()
class KalshiClient:
    def __init__(self):
        self.env = Environment.PROD
        self.key_id = '114141f5-a709-4521-8361-28229ff4248b'
        self.key_file_path = 'util/api/KalshiKey.txt'
        self.client = self._initialize_client()

    def _initialize_client(self):
        try:
            with open(self.key_file_path, "rb") as key_file:
                private_key = serialization.load_pem_private_key(
                    key_file.read(),
                    password=None  # Provide the password if your key is encrypted
                )
        except FileNotFoundError:
            raise FileNotFoundError(f"Private key file not found at {self.key_file_path}")
        except Exception as e:
            raise Exception(f"Error loading private key: {str(e)}")

        # Initialize and return the HTTP client
        return KalshiHttpClient(
            key_id=self.key_id,
            private_key=private_key,
            environment=self.env
        )

    def get_client(self):
        return self.client


class Environment(Enum):
    DEMO = "demo"
    PROD = "prod"

class KalshiBaseClient:
    """Base client class for interacting with the Kalshi API."""
    def __init__(
        self,
        key_id: str,
        private_key: rsa.RSAPrivateKey,
        environment: Environment = Environment.PROD,
    ):
        """Initializes the client with the provided API key and private key.

        Args:
            key_id (str): Your Kalshi API key ID.
            private_key (rsa.RSAPrivateKey): Your RSA private key.
            environment (Environment): The API environment to use (DEMO or PROD).
        """
        self.key_id = key_id
        self.private_key = private_key
        self.environment = environment
        self.last_api_call = datetime.now()

        if self.environment == Environment.DEMO:
            self.HTTP_BASE_URL = "https://demo-api.kalshi.co"
            self.WS_BASE_URL = "wss://demo-api.kalshi.co"
        elif self.environment == Environment.PROD:
            self.HTTP_BASE_URL = "https://api.elections.kalshi.com"
            self.WS_BASE_URL = "wss://api.elections.kalshi.com"
        else:
            raise ValueError("Invalid environment")

    def request_headers(self, method: str, path: str) -> Dict[str, Any]:
        """Generates the required authentication headers for API requests."""
        current_time_milliseconds = int(time.time() * 1000)
        timestamp_str = str(current_time_milliseconds)

        # Remove query params from path
        path_parts = path.split('?')

        msg_string = timestamp_str + method + path_parts[0]
        signature = self.sign_pss_text(msg_string)

        headers = {
            "Content-Type": "application/json",
            "KALSHI-ACCESS-KEY": self.key_id,
            "KALSHI-ACCESS-SIGNATURE": signature,
            "KALSHI-ACCESS-TIMESTAMP": timestamp_str,
        }
        return headers

    def sign_pss_text(self, text: str) -> str:
        """Signs the text using RSA-PSS and returns the base64 encoded signature."""
        message = text.encode('utf-8')
        try:
            signature = self.private_key.sign(
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.DIGEST_LENGTH
                ),
                hashes.SHA256()
            )
            return base64.b64encode(signature).decode('utf-8')
        except InvalidSignature as e:
            raise ValueError("RSA sign PSS failed") from e

class KalshiHttpClient(KalshiBaseClient):
    """Client for handling HTTP connections to the Kalshi API."""
    def __init__(
        self,
        key_id: str,
        private_key: rsa.RSAPrivateKey,
        environment: Environment = Environment.PROD,
    ):
        super().__init__(key_id, private_key, environment)
        self.host = self.HTTP_BASE_URL
        self.exchange_url = "/trade-api/v2/exchange"
        self.markets_url = "/trade-api/v2/markets"
        self.portfolio_url = "/trade-api/v2/portfolio"
        self.events_url = "/trade-api/v2/events"

    def rate_limit(self) -> None:
        """Built-in rate limiter to prevent exceeding API rate limits."""
        THRESHOLD_IN_MILLISECONDS = 100
        now = datetime.now()
        threshold_in_microseconds = 1000 * THRESHOLD_IN_MILLISECONDS
        threshold_in_seconds = THRESHOLD_IN_MILLISECONDS / 1000
        if now - self.last_api_call < timedelta(microseconds=threshold_in_microseconds):
            time.sleep(threshold_in_seconds)
        self.last_api_call = datetime.now()

    def raise_if_bad_response(self, response: requests.Response) -> None:
        """Raises an HTTPError if the response status code indicates an error."""
        if response.status_code not in range(200, 299):
            response.raise_for_status()

    def post(self, path: str, body: dict) -> Any:
        """Performs an authenticated POST request to the Kalshi API."""
        self.rate_limit()
        response = requests.post(
            self.host + path,
            json=body,
            headers=self.request_headers("POST", path)
        )
        self.raise_if_bad_response(response)
        return response.json()

    def get(self, path: str, params: Dict[str, Any] = {}) -> Any:
        """Performs an authenticated GET request to the Kalshi API."""
        self.rate_limit()
        response = requests.get(
            self.host + path,
            headers=self.request_headers("GET", path),
            params=params
        )
        self.raise_if_bad_response(response)
        return response.json()

    def delete(self, path: str, params: Dict[str, Any] = {}) -> Any:
        """Performs an authenticated DELETE request to the Kalshi API."""
        self.rate_limit()
        response = requests.delete(
            self.host + path,
            headers=self.request_headers("DELETE", path),
            params=params
        )
        self.raise_if_bad_response(response)
        return response.json()

    def get_balance(self) -> Dict[str, Any]:
        """Retrieves the account balance."""
        return self.get(self.portfolio_url + '/balance')

    def get_exchange_status(self) -> Dict[str, Any]:
        """Retrieves the exchange status."""
        return self.get(self.exchange_url + "/status")
    
    def get_portfolio_settlements(self) -> Dict[str, Any]:
        """Retrieves the member's historical settlements"""
        return self.get(self.portfolio_url + '/settlements')
    
    def get_order(self,order_id: str)-> Dict[str, Any]:
        """Retrieves the member's order based on order ID"""
        return self.get(self.portfolio_url + "/orders/" + order_id)
    
    
    def get_event(
        self,
        event_ticker: str = Required,
        with_nested_markets: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Retrieves an event based on the provided event ticker."""
        # Construct the URL path with the event ticker
        url = f"{self.events_url}/{event_ticker}"
        
        # Define the query parameters
        params = {
            'with_nested_markets': with_nested_markets,
        }
        
        # Remove None values from the params dictionary
        params = {k: v for k, v in params.items() if v is not None}
        
        # Perform the GET request
        return self.get(url, params=params)


    def get_trades(
        self,
        ticker: Optional[str] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        max_ts: Optional[int] = None,
        min_ts: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Retrieves trades based on provided filters."""
        params = {
            'ticker': ticker,
            'limit': limit,
            'cursor': cursor,
            'max_ts': max_ts,
            'min_ts': min_ts,
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        return self.get(self.markets_url + '/trades', params=params)
    
    def get_fills(
        self,
        ticker: Optional[str] = None,
        order_id: Optional[str] = None,
        max_ts: Optional[str] = None,
        limit: Optional[int] = None,
        cursor: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Retrieves trades based on provided filters."""
        params = {
            'ticker': ticker,
            'order_id': order_id,
            'max_ts': max_ts,
            'limit': limit,
            'cursor': cursor,
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        return self.get(self.portfolio_url + '/fills', params=params)
        
    def get_orders(
        self,
        ticker: Optional[str] = None,
        event_ticker: Optional[str] = None,
        min_ts: Optional[int] = None,
        status: Optional[str] = None,
        cursor: Optional[int] = None,
        limit: Optional[int] = None,
        
    ) -> Dict[str, Any]:
        """Retrieves trades based on provided filters."""
        params = {
            'ticker': ticker,
            'event_ticker': event_ticker,
            'min_ts': min_ts,
            'status': status,
            'cursor': cursor,
            'limit': limit,
            
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        return self.get(self.portfolio_url + '/orders', params=params)
    
    def get_positions(
        self,
        cursor: Optional[str] = None,
        limit: Optional[str] = None,
        count_filter: Optional[int] = None,
        settlement_status: Optional[str] = None,
        ticker: Optional[int] = None,
        event_ticker: Optional[int] = None,
        
    ) -> Dict[str, Any]:
        """Retrieves trades based on provided filters."""
        params = {
            'cursor': cursor,
            'limit': limit,
            'count_filter': count_filter,
            'settlement_status': settlement_status,
            'ticker': ticker,
            'event_ticker': event_ticker
            
        }
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        return self.get(self.portfolio_url + '/orders', params=params)

    def create_order(
        self,
        action: str = 'buy',
        buy_max_cost: Optional[int] = None,
        client_order_id: str = Required,
        count: int = 1,
        expiration_ts: Optional[int] = None,
        no_price: Optional[int] = None,
        post_only: Optional[bool] = None,
        sell_position_floor: Optional[int] = None,
        side: str = 'yes',
        ticker: str = Required,
        type: str = 'limit',
        yes_price: Optional[int] = 85,
        
        
    ) -> Dict[str, Any]:
        """Retrieves trades based on provided filters."""
        body = {
            'action': action,
            'buy_max_cost': buy_max_cost,
            'client_order_id': client_order_id,
            'count': count,
            'expiration_ts': expiration_ts,
            'no_price': no_price,
            'post_only': post_only,
            'sell_position_floor': sell_position_floor,
            'side': side,
            'ticker': ticker,
            'type': type,
            'yes_price': yes_price
        }
        # Remove None values
        body = {k: v for k, v in body.items() if v is not None}
        return self.post(self.portfolio_url + '/orders', body=body)
    
   

class KalshiWebSocketClient(KalshiBaseClient):
    """Client for handling WebSocket connections to the Kalshi API."""
    def __init__(
        self,
        key_id: str,
        private_key: rsa.RSAPrivateKey,
        environment: Environment = Environment.PROD,
    ):
        super().__init__(key_id, private_key, environment)
        self.ws = None
        self.url_suffix = "/trade-api/ws/v2"
        self.message_id = 1  # Add counter for message IDs

    async def connect(self):
        """Establishes a WebSocket connection using authentication."""
        host = self.WS_BASE_URL + self.url_suffix
        auth_headers = self.request_headers("GET", self.url_suffix)
        async with websockets.connect(host, additional_headers=auth_headers) as websocket:
            self.ws = websocket
            await self.on_open()
            await self.handler()

    async def on_open(self):
        """Callback when WebSocket connection is opened."""
        print("WebSocket connection opened.")
        await self.subscribe_to_tickers()

    async def subscribe_to_tickers(self):
        """Subscribe to ticker updates for all markets."""
        subscription_message = {
            "id": self.message_id,
            "cmd": "subscribe",
            "params": {
                "channels": ["ticker"]
            }
        }
        await self.ws.send(json.dumps(subscription_message))
        self.message_id += 1

    async def handler(self):
        """Handle incoming messages."""
        try:
            async for message in self.ws:
                await self.on_message(message)
        except websockets.ConnectionClosed as e:
            await self.on_close(e.code, e.reason)
        except Exception as e:
            await self.on_error(e)

    async def on_message(self, message):
        """Callback for handling incoming messages."""
        print("Received message:", message)

    async def on_error(self, error):
        """Callback for handling errors."""
        print("WebSocket error:", error)

    async def on_close(self, close_status_code, close_msg):
        """Callback when WebSocket connection is closed."""
        print("WebSocket connection closed with code:", close_status_code, "and message:", close_msg)


kalshi_client = KalshiClient()
client = kalshi_client.get_client()
