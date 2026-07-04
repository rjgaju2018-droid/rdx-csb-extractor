from karrio.sdk import Tracking
from .gateways import get_gateway


def track_shipment(tracking_number: str, carrier_name: str):
    """Track a shipment using the configured carrier gateway."""
    if not tracking_number:
        raise ValueError("tracking_number is required")

    gateway = get_gateway(carrier_name)
    request_payload = {
        "tracking_numbers": [tracking_number],
    }

    result = Tracking.fetch(request_payload).from_(gateway).parse()
    return result
