import pytest
import time
# On importe les fonctions et les variables depuis le fichier collector.py
import collector


@pytest.fixture(autouse=True)
def reset_compteur_alerte():
    """Cette fonction s'exécute automatiquement avant CHAQUE test pour remettre le compteur à zéro."""
    collector.COMPTEUR_ATTAQUES = 0
    collector.DERNIER_RESET_TEMPS = time.time()


def test_enrichir_geoip_local():
    """Test 1 : Vérifie que les adresses IP locales ne déclenchent pas d'appel API"""
    res_local = collector.enrichir_geoip("127.0.0.1")
    assert res_local["pays"] == "Local network"
    assert res_local["latitude"] == 0.0


def test_enrichir_geoip_publique():
    """Test 2 : Vérifie qu'une vraie IP publique est bien géolocalisée (ex: Google DNS)"""
    res_public = collector.enrichir_geoip("8.8.8.8")

    # On teste que l'API a bien répondu avec un pays (ici United States)
    assert res_public["pays"] == "United States"
    assert "latitude" in res_public
    assert "ville" in res_public


def test_verifier_alerte_seuil_en_dessous():
    """Test 3 : Vérifie que l'alerte reste False si on est en dessous du seuil"""
    # On simule 5 attaques (le seuil est à 100)
    for _ in range(5):
        alerte_declenchee = collector.verifier_alerte_seuil()

    assert alerte_declenchee is False


def test_verifier_alerte_seuil_au_dessus():
    """Test 4 : Vérifie que l'alerte passe à True si on dépasse le seuil de 100"""
    # On modifie temporairement le seuil à 3 pour que le test soit super rapide à s'exécuter
    collector.SEUIL_ALERTE = 3

    # 3 premières attaques -> en dessous ou égal au seuil, pas d'alerte
    collector.verifier_alerte_seuil()
    collector.verifier_alerte_seuil()
    assert collector.verifier_alerte_seuil() is False

    # 4ème attaque -> on dépasse le seuil de 3 !
    assert collector.verifier_alerte_seuil() is True