import os
import re
from pathlib import Path
from typing import Annotated

from pypdf import PdfReader
from semantic_kernel import Kernel
from semantic_kernel.functions import kernel_function


def charger_documents(dossier: Path) -> list[tuple[str, int, str]]:
    """Charge une page par morceau, avec fichier source et numero de page."""
    if not dossier.is_dir():
        raise NotADirectoryError(f"Repertoire PDF introuvable : {dossier}")

    morceaux = []
    for chemin in sorted(dossier.rglob("*")):
        if not chemin.is_file() or chemin.suffix.lower() != ".pdf":
            continue
        try:
            lecteur = PdfReader(chemin)
            for numero, page in enumerate(lecteur.pages, start=1):
                texte = (page.extract_text() or "").strip()
                if texte:
                    source = chemin.relative_to(dossier).as_posix()
                    morceaux.append((source, numero, texte))
        except Exception as erreur:
            raise RuntimeError(f"Lecture PDF impossible : {chemin}") from erreur
    return morceaux


def chercher(
    question: str, morceaux: list[tuple[str, int, str]], nombre: int = 3
) -> list[tuple[str, int, str]]:
    """Classe les pages par nombre de mots distincts communs avec la question."""
    mots = {mot for mot in re.findall(r"\w+", question.casefold()) if len(mot) > 3}
    scores = [
        (sum(mot in texte.casefold() for mot in mots), (source, page, texte))
        for source, page, texte in morceaux
    ]
    scores.sort(key=lambda resultat: resultat[0], reverse=True)
    return [morceau for score, morceau in scores if score > 0][: max(1, min(nombre, 10))]


class FichesPlugin:
    """Recherche lexicale dans les pages PDF chargees au demarrage."""

    def __init__(self, repertoire: Path):
        self.repertoire = repertoire
        self.fragments: list[tuple[str, int, str]] = []

    async def indexer(self) -> None:
        self.fragments = charger_documents(self.repertoire)

    @kernel_function(
        name="rechercher_fiches",
        description=(
            "Recherche par mots-cles dans les fiches PDF fournisseurs : conditions, "
            "livraison, garanties, contacts et caracteristiques. Renvoie des extraits "
            "avec fichier source et page, a citer dans la reponse."
        ),
    )
    async def rechercher_fiches(
        self,
        question: Annotated[str, "Question sur les fiches fournisseurs"],
        nombre: Annotated[int, "Nombre de passages souhaites, entre 1 et 10"] = 3,
    ) -> str:
        if not question.strip():
            return "Veuillez preciser la recherche."
        if not self.fragments:
            return "Aucune fiche PDF avec du texte exploitable dans le repertoire configure."
        trouves = chercher(question, self.fragments, nombre)
        if not trouves:
            return "Je ne trouve pas cette information dans les fiches fournisseurs."
        return "\n\n".join(
            f"[Source : {source}, page {page}]\n{texte}"
            for source, page, texte in trouves
        )


async def ajouter_fiches(kernel: Kernel) -> FichesPlugin:
    repertoire = Path(os.environ.get("FICHES_REPERTOIRE", "fiches_fournisseurs"))
    if not repertoire.is_absolute():
        repertoire = Path(__file__).resolve().parent / repertoire
    plugin = FichesPlugin(repertoire)
    await plugin.indexer()
    kernel.add_plugin(plugin, plugin_name="fiches")
    return plugin