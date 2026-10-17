"""SYNTHETIC PRIVATE FIXTURES: imported only by administrative bootstrap.

Fixtures are published for reproducibility. Real-world secrets must instead be
provisioned by their participant. The coordinator never imports this module.
"""


def factory_profiles(name):
    if name == "factory_a":
        base = dict(demand=600, stock=40, stock_unit_cost=45, mild_threshold=100,
                    mild_unit_cost=90, severe_unit_cost=220, priority_signal=165,
                    deadline="day_5", contract_ids=["SYNTHETIC_MEDICAL_001"])
    else:
        base = dict(demand=500, stock=50, stock_unit_cost=30, mild_threshold=150,
                    mild_unit_cost=40, severe_unit_cost=110, priority_signal=75,
                    deadline="day_5", contract_ids=["SYNTHETIC_RETAIL_001"])
    return {name: dict(base) for name in ("baseline", "primary_loss", "combined_loss", "no_scarcity", "no_alternate")}


def supplier_profiles():
    capacities = dict(baseline=(800, 300), primary_loss=(480, 300), combined_loss=(480, 150),
                      no_scarcity=(1100, 300), no_alternate=(800, 0))
    return {name: dict(primary_capacity=c[0], alternate_capacity=c[1], alternate_unit_cost=95,
                       manufacturing_unit_cost=18, wafer_inventory=9000,
                       client_book=["SYNTHETIC_PRIVATE_CLIENT_001"])
            for name, c in capacities.items()}

