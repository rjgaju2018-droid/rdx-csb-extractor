import os
import sys
from dotenv import load_dotenv
from karrio.sdk import gateway

if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

env_path = os.path.join(base_path, ".env")
load_dotenv(env_path)

CARRIER_ENV_MAP = {
    "fedex": {
        "client_id": "FEDEX_CLIENT_ID",
        "client_secret": "FEDEX_CLIENT_SECRET",
        "account_number": "FEDEX_ACCOUNT_NUMBER",
    },
    "ups": {
        "client_id": "UPS_CLIENT_ID",
        "client_secret": "UPS_CLIENT_SECRET",
        "account_number": "UPS_ACCOUNT_NUMBER",
    },
    "dhl": {
        "site_id": "DHL_SITE_ID",
        "password": "DHL_PASSWORD",
        "account_number": "DHL_ACCOUNT_NUMBER",
    },
    "aramex": {
        "username": "ARAMEX_USERNAME",
        "password": "ARAMEX_PASSWORD",
        "account_number": "ARAMEX_ACCOUNT_NUMBER",
        "account_pin": "ARAMEX_ACCOUNT_PIN",
        "account_entity": "ARAMEX_ACCOUNT_ENTITY",
    },
}

def _load_settings_for_carrier(carrier_name: str) -> dict:
    carrier_name = carrier_name.lower()
    if carrier_name not in CARRIER_ENV_MAP:
        raise ValueError(f"Unsupported carrier: {carrier_name}")
    env_map = CARRIER_ENV_MAP[carrier_name]
    settings = {key: os.getenv(env_var) for key, env_var in env_map.items()}
    missing = [env_var for env_var, value in settings.items() if value is None]
    if missing:
        raise EnvironmentError(
            f"Missing required settings for {carrier_name}: {', '.join(missing)}"
        )
    return settings

def get_gateway(carrier_name: str):
    carrier_name = carrier_name.lower()
    if carrier_name not in CARRIER_ENV_MAP:
        raise ValueError(
            f"Unsupported carrier '{carrier_name}'. Supported carriers: {', '.join(CARRIER_ENV_MAP)}"
        )
    settings = _load_settings_for_carrier(carrier_name)
    return gateway[carrier_name].create(settings)
