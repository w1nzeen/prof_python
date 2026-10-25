"""Experiment 4: the same behaviour tested with a Mock and with a Fake."""

from unittest.mock import Mock, create_autospec

import pytest
from conftest import FakeRepository

from equipment_manager.domain.exceptions import DeviceNotFoundError
from equipment_manager.domain.models import Computer, InventoryRegistry
from equipment_manager.domain.protocols import Repository
from equipment_manager.domain.value_objects import InventoryNumber


@pytest.fixture
def mock_repository() -> Mock:
    mock: Mock = create_autospec(Repository, instance=True)
    return mock


# ------------------------------------------------------------ with a Fake
def test_fake_state_testing_is_readable(
    fake_repository: FakeRepository, computer: Computer
) -> None:
    registry = InventoryRegistry(fake_repository)

    registry.register(computer)

    assert registry["PC-001"] is computer
    assert len(registry) == 1


def test_fake_survives_refactoring_of_calls(
    fake_repository: FakeRepository, computer: Computer, printer: object
) -> None:
    registry = InventoryRegistry(fake_repository)
    registry.register(computer)

    assert [str(d.inventory_number) for d in registry] == ["PC-001"]
    assert registry.unregister("PC-001") is True
    assert fake_repository.items == {}


def test_fake_is_reusable_for_a_whole_scenario(
    fake_repository: FakeRepository, computer: Computer
) -> None:
    registry = InventoryRegistry(fake_repository)
    registry.register(computer)

    assert registry.total_cost().amount == computer.cost.amount
    assert registry.most_expensive() is computer


# ------------------------------------------------------------ with a Mock
def test_mock_interaction_testing_register(
    mock_repository: Mock, computer: Computer
) -> None:
    registry = InventoryRegistry(mock_repository)

    registry.register(computer)

    mock_repository.add.assert_called_once_with(computer)


def test_mock_find_uses_normalized_key(mock_repository: Mock, computer: Computer) -> None:
    mock_repository.get.return_value = computer
    registry = InventoryRegistry(mock_repository)

    assert registry["pc-001"] is computer

    mock_repository.get.assert_called_once_with(InventoryNumber("PC-001"))


def test_mock_missing_device(mock_repository: Mock) -> None:
    mock_repository.get.return_value = None

    with pytest.raises(DeviceNotFoundError):
        _ = InventoryRegistry(mock_repository)["PC-001"]


def test_mock_test_is_coupled_to_implementation_details(mock_repository: Mock) -> None:
    """len() is implemented through repository.keys(); the test knows it."""
    mock_repository.keys.return_value = [InventoryNumber("PC-001")]

    assert len(InventoryRegistry(mock_repository)) == 1

    mock_repository.keys.assert_called_once_with()
    mock_repository.all.assert_not_called()


def test_fake_satisfies_the_protocol_signature(fake_repository: FakeRepository) -> None:
    repository: Repository[InventoryNumber, object] = fake_repository  # type: ignore[assignment]

    assert repository.all() == []
