import pytest
from src.models import Apartment, Bill, Parameters, ApartmentSettlement, Tenant
from src.manager import Manager


def test_apartment_costs_with_optional_parameters():
    manager = Manager(Parameters())
    manager.bills.append(Bill(
        apartment='apart-polanka',
        date_due='2025-03-15',
        settlement_year=2025,
        settlement_month=2,
        amount_pln=1250.0,
        type='rent'
    ))

    manager.bills.append(Bill(
        apartment='apart-polanka',
        date_due='2024-03-15',
        settlement_year=2024,
        settlement_month=2,
        amount_pln=1150.0,
        type='rent'
    ))

    manager.bills.append(Bill(
        apartment='apart-polanka',
        date_due='2024-02-02',
        settlement_year=2024,
        settlement_month=1,
        amount_pln=222.0,
        type='electricity'
    ))

    costs = manager.get_apartment_costs('apartment-1', 2024, 1)
    assert costs is None

    costs = manager.get_apartment_costs('apart-polanka', 2024, 3)
    assert costs == 0.0

    costs = manager.get_apartment_costs('apart-polanka', 2024, 1)
    assert costs == 222.0

    costs = manager.get_apartment_costs('apart-polanka', 2025, 1)
    assert costs == 910.0
    
    costs = manager.get_apartment_costs('apart-polanka', 2024)
    assert costs == 1372.0

    costs = manager.get_apartment_costs('apart-polanka')
    assert costs == 3532.0


def test_get_apartment_costs():
    manager = Manager.__new__(Manager)
    manager.apartments = {
        "A1": Apartment(key="A1", name="Test", location="Wawa", area_m2=30.0, rooms={})
    }
    manager.bills = [
        Bill(amount_pln=300.0, date_due="2024-03-10", apartment="A1", settlement_year=2024, settlement_month=3, type="prąd"),
        Bill(amount_pln=150.0, date_due="2024-03-15", apartment="A1", settlement_year=2024, settlement_month=3, type="woda"),
        Bill(amount_pln=200.0, date_due="2024-04-10", apartment="A1", settlement_year=2024, settlement_month=4, type="prąd"),
    ]

    assert manager.get_apartment_costs("A1", 2024, 3) == 450.0  # są rachunki
    assert manager.get_apartment_costs("A1", 2024, 5) == 0.0    # brak rachunków w miesiącu
    assert manager.get_apartment_costs("X99", 2024, 3) is None  # mieszkanie nie istnieje

    # Niepoprawne miesiące
    with pytest.raises(ValueError):
        manager.get_apartment_costs("A1", 2024, 13)
    with pytest.raises(ValueError):
        manager.get_apartment_costs("A1", 2024, 0)


def test_create_apartment_settlement():
    manager = Manager.__new__(Manager)
    manager.apartments = {
        "A1": Apartment(key="A1", name="Kawalerka", location="Poznań", area_m2=30.0, rooms={})
    }
    manager.tenants = {}
    manager.transfers = []
    manager.bills = [
        Bill(amount_pln=300.0, date_due="2024-03-10", apartment="A1", settlement_year=2024, settlement_month=3, type="electricity"),
        Bill(amount_pln=150.0, date_due="2024-03-15", apartment="A1", settlement_year=2024, settlement_month=3, type="water"),
        Bill(amount_pln=200.0, date_due="2024-04-10", apartment="A1", settlement_year=2024, settlement_month=4, type="electricity"),
    ]

    # Mieszkanie ma rachunki w danym miesiącu (marzec 2024 - suma 450.0)
    settlement_march = manager.create_apartment_settlement("A1", 2024, 3)

    assert settlement_march is not None
    assert isinstance(settlement_march, ApartmentSettlement)
    assert settlement_march.apartment == "A1"
    assert settlement_march.year == 2024
    assert settlement_march.month == 3
    assert settlement_march.total_rent_pln == 0.0
    assert settlement_march.total_bills_pln == 450.0
    assert settlement_march.total_due_pln == -450.0

    # Mieszkanie nie ma rachunków w danym miesiącu (maj 2024 - suma 0.0)
    settlement_may = manager.create_apartment_settlement("A1", 2024, 5)

    assert settlement_may is not None
    assert settlement_may.total_bills_pln == 0.0
    assert settlement_may.total_due_pln == 0.0

    # Nieistniejące mieszkanie
    assert manager.create_apartment_settlement("X99", 2024, 3) is None


def test_create_tenant_settlements():
    manager = Manager.__new__(Manager)
    t_base = dict(rent_pln=1000.0, deposit_pln=1000.0, date_agreement_from="2024-01-01", date_agreement_to="2024-12-31")
    s_base = dict(month=3, year=2024, total_rent_pln=0.0, total_bills_pln=500.0, total_due_pln=-500.0)

    # Dwóch najemców (500.0 / 2 = 250.0)
    manager.tenants = {
        "T1": Tenant(name="Jan", apartment="A1", room="R1", **t_base),
        "T2": Tenant(name="Anna", apartment="A1", room="R2", **t_base),
    }
    res2 = manager.create_tenant_settlements(ApartmentSettlement(apartment="A1", **s_base))
    assert len(res2) == 2
    assert res2[0].tenant == "T1"
    assert res2[0].bills_pln == 250.0
    assert res2[0].balance_pln == -250.0
    assert res2[1].tenant == "T2"
    assert res2[1].bills_pln == 250.0

    # Jeden najemca (500.0 / 1 = 500.0)
    manager.tenants = {"T3": Tenant(name="Piotr", apartment="A2", room="R1", **t_base)}
    res1 = manager.create_tenant_settlements(ApartmentSettlement(apartment="A2", **s_base))
    assert len(res1) == 1
    assert res1[0].bills_pln == 500.0
    assert res1[0].balance_pln == -500.0

    # Brak najemców -> pusta lista
    assert manager.create_tenant_settlements(ApartmentSettlement(apartment="A3", **s_base)) == []