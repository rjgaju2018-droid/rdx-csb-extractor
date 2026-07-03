import os
import pytest

from carriers import gateways, tracking


def test_load_settings_missing_env(monkeypatch):
    # Ensure required env vars are not present
    monkeypatch.delenv("FEDEX_CLIENT_ID", raising=False)
    monkeypatch.delenv("FEDEX_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("FEDEX_ACCOUNT_NUMBER", raising=False)

    with pytest.raises(EnvironmentError):
        gateways._load_settings_for_carrier("fedex")


def test_track_shipment_no_number():
    with pytest.raises(ValueError):
        tracking.track_shipment("", "fedex")


def test_track_shipment_uses_gateway_and_tracking(monkeypatch):
    # Fake Tracking.fetch to return an object with from_().parse() chain
    expected = {"ok": True}

    class FakeParse:
        def parse(self):
            return expected

    class FakeFrom:
        def __init__(self, payload):
            self.payload = payload

        def from_(self, gateway):
            # ensure gateway passed is the same object returned by get_gateway
            assert gateway is fake_gateway
            return FakeParse()

    # Replace Tracking in the tracking module
    monkeypatch.setattr(tracking, "Tracking", type("T", (), {"fetch": staticmethod(lambda payload: FakeFrom(payload))}))

    # Replace get_gateway to return a dummy gateway instance
    fake_gateway = object()

    def fake_get_gateway(name):
        assert name == "fedex"
        return fake_gateway

    monkeypatch.setattr("carriers.tracking.get_gateway", fake_get_gateway)

    res = tracking.track_shipment("TRACK12345", "fedex")
    assert res == expected
