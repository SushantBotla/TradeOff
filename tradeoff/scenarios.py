"""Public scenario IDs and labels only; no private fixture parameters."""

SCENARIOS = {
    "baseline": "Baseline shortage",
    "primary_loss": "Primary capacity loss",
    "combined_loss": "Combined disruption (unresolved service floors)",
    "no_scarcity": "No scarcity",
    "no_alternate": "No alternative supply",
}
FACTORIES = ("factory_a", "factory_b")

# Public, illustrative shipping choices. These are not confidential factory data
# and are not claimed to be observed chip-procurement shipments in DataCo.
SHIPMENT_CONTEXTS = {
    "factory_a": dict(shipping_mode="First Class", scheduled_days=1, market="USCA"),
    "factory_b": dict(shipping_mode="Standard Class", scheduled_days=4, market="USCA"),
}

