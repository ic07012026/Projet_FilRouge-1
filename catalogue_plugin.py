# catalogue_plugin.py
# Plugin Semantic Kernel d'interrogation de la base "catalogue" (lecture seule).
# Variables d'environnement : DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME.
import os
from pathlib import Path
from typing import Annotated

import pymysql
from dotenv import load_dotenv
from pymysql.cursors import DictCursor
from semantic_kernel.functions import kernel_function

load_dotenv(Path(__file__).resolve().parent / ".env")

LIMITE = 50


def _connexion():
    conn = pymysql.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=int(os.environ.get("DB_PORT", "3306")),
        user=os.environ.get("DB_USER", "agent_ia"),
        password=os.environ["DB_PASSWORD"],
        database=os.environ.get("DB_NAME", "catalogue"),
        charset="utf8mb4",
        cursorclass=DictCursor,
    )
    # Garde-fou : la session refuse toute écriture côté serveur.
    with conn.cursor() as cur:
        cur.execute("SET SESSION TRANSACTION READ ONLY")
    return conn


def _requete(sql: str, params: tuple = ()) -> list[dict]:
    conn = _connexion()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()


def _echapper_like(texte: str) -> str:
    return texte.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _formater(lignes: list[dict]) -> str:
    if not lignes:
        return "Aucun produit trouvé."
    return "\n".join(
        f"- [{l['id']}] {l['libelle']} | {l['categorie']} | {l['fournisseur']} | "
        f"{float(l['prix']):.2f} € | stock : {l['stock']}"
        + (f" [{l['statut']}]" if "statut" in l else "")
        for l in lignes
    )


class CataloguePlugin:
    """Outils d'interrogation du catalogue produits."""

    @kernel_function(
        name="rechercher_produits",
        description="Recherche des produits par mot-clé dans le libellé, la catégorie ou le fournisseur.",
    )
    def rechercher_produits(
        self,
        mot_cle: Annotated[str, "Mot ou fragment à rechercher, par exemple 'café' ou 'écran'"],
    ) -> str:
        motif = f"%{_echapper_like(mot_cle.strip())}%"
        sql = """
            SELECT id, libelle, categorie, prix, stock, fournisseur
            FROM produits
            WHERE libelle LIKE %s OR categorie LIKE %s OR fournisseur LIKE %s
            ORDER BY libelle
            LIMIT %s
        """
        return _formater(_requete(sql, (motif, motif, motif, LIMITE)))

    @kernel_function(
        name="produits_par_fournisseur",
        description="Liste les produits d'un fournisseur donné (raison sociale, correspondance partielle acceptée).",
    )
    def produits_par_fournisseur(
        self,
        fournisseur: Annotated[str, "Nom du fournisseur, par exemple 'NovaTech' ou 'CaféoPro'"],
    ) -> str:
        motif = f"%{_echapper_like(fournisseur.strip())}%"
        sql = """
            SELECT id, libelle, categorie, prix, stock, fournisseur
            FROM produits
            WHERE fournisseur LIKE %s
            ORDER BY libelle
            LIMIT %s
        """
        return _formater(_requete(sql, (motif, LIMITE)))

    @kernel_function(
        name="produits_stock_faible",
        description="Liste les produits en rupture (stock à 0) ou à stock faible (stock inférieur ou égal au seuil).",
    )
    def produits_stock_faible(
        self,
        seuil: Annotated[int, "Quantité en dessous de laquelle le stock est considéré faible"] = 5,
    ) -> str:
        sql = """
            SELECT id, libelle, categorie, prix, stock, fournisseur,
                   CASE WHEN stock = 0 THEN 'RUPTURE' ELSE 'stock faible' END AS statut
            FROM produits
            WHERE stock <= %s
            ORDER BY stock, libelle
            LIMIT %s
        """
        return _formater(_requete(sql, (seuil, LIMITE)))

    @kernel_function(
        name="produits_par_fourchette_de_prix",
        description="Liste les produits dont le prix unitaire HT est compris dans une fourchette (bornes incluses).",
    )
    def produits_par_fourchette_de_prix(
        self,
        prix_min: Annotated[float, "Prix minimum en euros HT"],
        prix_max: Annotated[float, "Prix maximum en euros HT"],
    ) -> str:
        if prix_min > prix_max:
            return "Fourchette invalide : le prix minimum est supérieur au prix maximum."
        sql = """
            SELECT id, libelle, categorie, prix, stock, fournisseur
            FROM produits
            WHERE prix BETWEEN %s AND %s
            ORDER BY prix
            LIMIT %s
        """
        return _formater(_requete(sql, (prix_min, prix_max, LIMITE)))

    @kernel_function(
        name="statistiques_valeur_stock_par_categorie",
        description="Calcule, pour chaque catégorie, le nombre de produits, les unités en stock et la valeur du stock HT, ainsi que le total général.",
    )
    def statistiques_valeur_stock_par_categorie(self) -> str:
        sql = """
            SELECT categorie,
                   COUNT(*) AS nb_produits,
                   SUM(stock) AS unites,
                   SUM(prix * stock) AS valeur_stock
            FROM produits
            GROUP BY categorie
            ORDER BY valeur_stock DESC
        """
        lignes = _requete(sql)
        if not lignes:
            return "Aucune donnée de stock disponible."
        total_valeur = sum(float(l["valeur_stock"]) for l in lignes)
        total_unites = sum(int(l["unites"]) for l in lignes)
        total_produits = sum(int(l["nb_produits"]) for l in lignes)
        detail = "\n".join(
            f"- {l['categorie']} : {l['nb_produits']} produits, {int(l['unites'])} unités, "
            f"valeur {float(l['valeur_stock']):.2f} € HT"
            for l in lignes
        )
        return (
            f"{detail}\n"
            f"Total : {total_produits} produits, {total_unites} unités, "
            f"valeur {total_valeur:.2f} € HT"
        )
