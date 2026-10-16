import os

import pymysql
import pytest

from catalogue_plugin import CataloguePlugin, _connexion, _requete

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("RUN_MYSQL_TESTS") != "1",
        reason="Definir RUN_MYSQL_TESTS=1 avec une base MySQL de test initialisee.",
    ),
]


def test_scripts_sql_et_session_lecture_seule():
    assert _requete("SELECT COUNT(*) AS nombre FROM produits") == [{"nombre": 38}]
    assert _requete("SELECT @@session.transaction_read_only AS lecture_seule") == [
        {"lecture_seule": 1}
    ]


def test_outils_sur_donnees_projet():
    plugin = CataloguePlugin()
    assert "ProBook 14" in plugin.rechercher_produits("ProBook")
    assert "NovaTech Distribution" in plugin.produits_par_fournisseur("NovaTech")
    assert "[RUPTURE]" in plugin.produits_stock_faible(0)
    assert "Souris sans fil" in plugin.produits_par_fourchette_de_prix(29.90, 29.90)
    assert "Total : 38 produits" in plugin.statistiques_valeur_stock_par_categorie()


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO produits VALUES (999, 'Test', 'Test', 1, 1, 'Test')",
        "UPDATE produits SET stock = 0 WHERE id = 1",
        "DELETE FROM produits WHERE id = 1",
        "CREATE TABLE ecriture_interdite (id INTEGER)",
    ],
)
def test_mysql_refuse_ecriture(sql):
    with pytest.raises(pymysql.err.OperationalError) as levee:
        _requete(sql)
    assert levee.value.args[0] in (1142, 1792)


def test_droits_select_seuls_meme_sans_garde_fou_session():
    connexion = _connexion()
    try:
        with connexion.cursor() as curseur:
            curseur.execute("SET SESSION TRANSACTION READ WRITE")
            with pytest.raises(pymysql.err.OperationalError) as levee:
                curseur.execute("UPDATE produits SET stock = 0 WHERE id = 1")
            assert levee.value.args[0] == 1142
    finally:
        connexion.close()
