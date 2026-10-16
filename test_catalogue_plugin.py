from decimal import Decimal
from unittest.mock import MagicMock

import pymysql
import pytest

import catalogue_plugin as catalogue


@pytest.fixture
def connexion(monkeypatch):
    connexion = MagicMock()
    monkeypatch.setattr(catalogue, "_connexion", lambda: connexion)
    return connexion


def test_connexion_configuration_et_lecture_seule(monkeypatch):
    connexion = MagicMock()
    connecter = MagicMock(return_value=connexion)
    monkeypatch.setattr(catalogue.pymysql, "connect", connecter)
    for cle, valeur in {
        "DB_HOST": "mysql-test",
        "DB_PORT": "3307",
        "DB_USER": "agent_test",
        "DB_PASSWORD": "mot-de-passe-factice",
        "DB_NAME": "catalogue_test",
    }.items():
        monkeypatch.setenv(cle, valeur)

    assert catalogue._connexion() is connexion
    connecter.assert_called_once_with(
        host="mysql-test",
        port=3307,
        user="agent_test",
        password="mot-de-passe-factice",
        database="catalogue_test",
        charset="utf8mb4",
        cursorclass=catalogue.DictCursor,
    )
    connexion.cursor.return_value.__enter__.return_value.execute.assert_called_once_with(
        "SET SESSION TRANSACTION READ ONLY"
    )


def test_requete_parametree_et_fermeture(connexion):
    curseur = connexion.cursor.return_value.__enter__.return_value
    lignes = [{"id": 1}]
    curseur.fetchall.return_value = lignes

    assert catalogue._requete("SELECT id FROM produits WHERE id = %s", (1,)) == lignes
    curseur.execute.assert_called_once_with(
        "SELECT id FROM produits WHERE id = %s", (1,)
    )
    connexion.close.assert_called_once_with()


def test_refus_ecriture_propage_et_ferme_connexion(connexion):
    curseur = connexion.cursor.return_value.__enter__.return_value
    erreur = pymysql.err.OperationalError(1792, "Read only transaction")
    curseur.execute.side_effect = erreur

    with pytest.raises(pymysql.err.OperationalError) as levee:
        catalogue._requete("DELETE FROM produits")

    assert levee.value is erreur
    curseur.fetchall.assert_not_called()
    connexion.close.assert_called_once_with()


@pytest.mark.parametrize(
    "methode, arguments, parametres, clause",
    [
        (
            "rechercher_produits",
            ("  50%_\\' OR 1=1 --  ",),
            ("%50\\%\\_\\\\' OR 1=1 --%",) * 3 + (catalogue.LIMITE,),
            "WHERE libelle LIKE %s OR categorie LIKE %s OR fournisseur LIKE %s",
        ),
        (
            "produits_par_fournisseur",
            (" NovaTech ",),
            ("%NovaTech%", catalogue.LIMITE),
            "WHERE fournisseur LIKE %s",
        ),
        (
            "produits_stock_faible",
            (3,),
            (3, catalogue.LIMITE),
            "WHERE stock <= %s",
        ),
        (
            "produits_par_fourchette_de_prix",
            (10.0, 50.0),
            (10.0, 50.0, catalogue.LIMITE),
            "WHERE prix BETWEEN %s AND %s",
        ),
    ],
)
def test_outils_catalogue_parametres(
    monkeypatch, methode, arguments, parametres, clause
):
    requete = MagicMock(return_value=[])
    monkeypatch.setattr(catalogue, "_requete", requete)

    resultat = getattr(catalogue.CataloguePlugin(), methode)(*arguments)

    assert resultat == "Aucun produit trouvé."
    requete.assert_called_once()
    sql, params = requete.call_args.args
    assert clause in " ".join(sql.split())
    assert params == parametres
    assert "LIMIT %s" in sql


def test_fourchette_invalide_sans_acces_base(monkeypatch):
    requete = MagicMock()
    monkeypatch.setattr(catalogue, "_requete", requete)

    assert "Fourchette invalide" in (
        catalogue.CataloguePlugin().produits_par_fourchette_de_prix(50, 10)
    )
    requete.assert_not_called()


def test_format_produit_et_statut():
    assert catalogue._formater(
        [
            {
                "id": 4,
                "libelle": "Ecran",
                "categorie": "Informatique",
                "prix": Decimal("349.00"),
                "stock": 0,
                "fournisseur": "NovaTech",
                "statut": "RUPTURE",
            }
        ]
    ) == "- [4] Ecran | Informatique | NovaTech | 349.00 € | stock : 0 [RUPTURE]"


def test_statistiques_agregation(monkeypatch):
    requete = MagicMock(
        return_value=[
            {
                "categorie": "Informatique",
                "nb_produits": 2,
                "unites": Decimal("3"),
                "valeur_stock": Decimal("150.50"),
            },
            {
                "categorie": "Papeterie",
                "nb_produits": 1,
                "unites": Decimal("4"),
                "valeur_stock": Decimal("10.00"),
            },
        ]
    )
    monkeypatch.setattr(catalogue, "_requete", requete)

    resultat = catalogue.CataloguePlugin().statistiques_valeur_stock_par_categorie()

    assert "Informatique : 2 produits, 3 unités, valeur 150.50 € HT" in resultat
    assert "Total : 3 produits, 7 unités, valeur 160.50 € HT" in resultat
    assert "GROUP BY categorie" in requete.call_args.args[0]


def test_statistiques_sans_donnees(monkeypatch):
    monkeypatch.setattr(catalogue, "_requete", lambda sql: [])
    assert (
        catalogue.CataloguePlugin().statistiques_valeur_stock_par_categorie()
        == "Aucune donnée de stock disponible."
    )
