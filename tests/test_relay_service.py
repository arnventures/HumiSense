import pytest
import time
from services.relay_service import RelayService

@pytest.fixture(scope="function")
def relay():
    """
    Erstellt eine isolierte Instanz von RelayService für Tests.
    Nach jedem Test wird 'cleanup()' aufgerufen, um GPIO-Ressourcen freizugeben.
    """
    relay_instance = RelayService()
    yield relay_instance
    relay_instance.cleanup()
    time.sleep(0.5)  # Kleine Verzögerung zwischen den Tests

def test_initial_state(relay):
    """Testet, ob das Relais initial ausgeschaltet ist."""
    state_info = relay.get_state()
    print(f"🔍 Initial State: {state_info}")
    assert state_info["state"] is False, "Relais sollte beim Start AUS sein"

def test_turn_on(relay):
    """Testet das Einschalten des Relais ohne Verzögerung."""
    relay.set_mode("Hand")  # Manuell schalten erlauben
    relay.turn_on(delay=0)
    time.sleep(0.5)  # Mehr Zeit geben, um die Schaltung zu prüfen
    state_info = relay.get_state()
    print(f"🔍 Nach turn_on: {state_info}")
    assert state_info["state"] is True, "Relais sollte eingeschaltet sein"

def test_turn_off(relay):
    """Testet das Ausschalten des Relais."""
    relay.set_mode("Hand")
    relay.turn_on(delay=0)
    time.sleep(0.5)
    relay.turn_off(delay=0)
    time.sleep(0.5)
    state_info = relay.get_state()
    print(f"🔍 Nach turn_off: {state_info}")
    assert state_info["state"] is False, "Relais sollte ausgeschaltet sein"

@pytest.mark.parametrize("delay", [1, 2])
def test_turn_on_with_delay(relay, delay):
    """Testet das Einschalten mit verschiedenen Verzögerungen."""
    relay.set_mode("Hand")
    relay.turn_on(delay=delay)
    time.sleep(delay + 0.5)  # Sicherstellen, dass die Verzögerung durchläuft
    state_info = relay.get_state()
    print(f"🔍 Nach turn_on_with_delay({delay}s): {state_info}")
    assert state_info["state"] is True, f"Relais sollte nach {delay}s an sein"

@pytest.mark.parametrize("delay", [1, 2])
def test_turn_off_with_delay(relay, delay):
    """Testet das Ausschalten mit Verzögerung."""
    relay.set_mode("Hand")
    relay.turn_on(delay=0)
    time.sleep(0.5)
    relay.turn_off(delay=delay)
    time.sleep(delay + 0.5)
    state_info = relay.get_state()
    print(f"🔍 Nach turn_off_with_delay({delay}s): {state_info}")
    assert state_info["state"] is False, f"Relais sollte nach {delay}s aus sein"

def test_force_off(relay):
    """Testet die Notfallabschaltung."""
    relay.set_mode("Hand")
    relay.turn_on(delay=0)
    time.sleep(0.5)
    message = relay.force_off()
    time.sleep(0.5)
    state_info = relay.get_state()
    print(f"🔍 Nach force_off: {state_info}, Nachricht: {message}")
    assert state_info["state"] is False, "Relais sollte nach Notabschaltung AUS sein"
    assert "Emergency" in message

    # Nach Notabschaltung lässt sich das Relais nicht mehr einschalten
    result = relay.turn_on(delay=0)
    print(f"🔍 Versuch, nach force_off wieder einzuschalten: {result}")
    assert "Emergency active" in result, "Relais sollte sich bei Brandalarm nicht einschalten lassen"

def test_set_mode_aus(relay):
    """Testet, ob der Modus 'Aus' das Relais sofort abschaltet."""
    # Zunächst auf Hand schalten, damit das Relais ein- und ausgeschaltet werden kann
    relay.set_mode("Hand")
    relay.turn_on(delay=0)
    time.sleep(0.5)
    relay.set_mode("Aus")
    time.sleep(0.5)
    state_info = relay.get_state()
    print(f"🔍 Nach set_mode('Aus'): {state_info}")
    assert state_info["state"] is False, "Relais sollte bei Modus 'Aus' ausgeschaltet sein"
    assert state_info["mode"] == "Aus"

def test_set_mode_hand(relay):
    """Testet, ob der Modus 'Hand' aktiviert wird und man manuell schalten darf."""
    relay.set_mode("Hand")
    time.sleep(0.5)
    state_info = relay.get_state()
    print(f"🔍 Nach set_mode('Hand'): {state_info}")
    assert state_info["mode"] == "Hand", "Modus sollte auf 'Hand' gesetzt sein"
    relay.turn_on(delay=0)
    time.sleep(0.5)
    state_info = relay.get_state()
    print(f"🔍 Nach turn_on in Hand-Modus: {state_info}")
    assert state_info["state"] is True, "Relais sollte im Hand-Modus schaltbar sein"

def test_set_mode_auto(relay):
    """Testet das Umschalten auf 'Auto'-Modus."""
    relay.set_mode("Auto")
    time.sleep(0.5)
    state_info = relay.get_state()
    print(f"🔍 Nach set_mode('Auto'): {state_info}")
    assert state_info["mode"] == "Auto", "Modus sollte auf 'Auto' gesetzt sein"
