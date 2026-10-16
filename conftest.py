import socket

import pytest


@pytest.fixture(autouse=True)
def interdire_reseau_unitaire(request, monkeypatch):
    """Les tests unitaires ne doivent appeler aucun service distant."""
    if request.node.get_closest_marker("integration"):
        return

    def refuser(*args, **kwargs):
        raise AssertionError("Appel reseau interdit dans un test unitaire.")

    monkeypatch.setattr(socket.socket, "connect", refuser)
    monkeypatch.setattr(socket, "create_connection", refuser)
