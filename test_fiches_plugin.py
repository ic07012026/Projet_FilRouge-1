import asyncio
from unittest.mock import Mock, patch

import pytest
from pypdf import PdfWriter

from fiches_plugin import FichesPlugin, ajouter_fiches, chercher


def test_configuration_chat_seul(monkeypatch):
    from config import creer_kernel
    from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase

    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test")
    monkeypatch.setenv("CHAT_DEPLOYMENT", "chat-test")
    kernel = creer_kernel()
    assert len(kernel.services) == 1
    assert kernel.get_service(type=ChatCompletionClientBase).ai_model_id == "chat-test"


def test_chercher_classement_et_ponctuation():
    morceaux = [
        ("livraison.pdf", 1, "Livraison sous trois jours."),
        ("novatech.pdf", 2, "NovaTech : garantie de deux ans et livraison."),
        ("autre.pdf", 1, "Contacts commerciaux."),
    ]
    trouves = chercher("GARANTIE, livraison ? garantie", morceaux)
    assert trouves == [morceaux[1], morceaux[0]]
    assert chercher("inconnu", morceaux) == []
    assert chercher("le de et", morceaux) == []


@pytest.mark.parametrize("nombre, attendu", [(0, 1), (2, 2), (20, 10)])
def test_chercher_limite(nombre, attendu):
    morceaux = [("fiche.pdf", numero, "Garantie.") for numero in range(1, 13)]
    assert len(chercher("garantie", morceaux, nombre)) == attendu


def test_enregistrement_sans_service_embeddings(tmp_path, monkeypatch):
    from semantic_kernel import Kernel

    async def verifier():
        monkeypatch.setenv("FICHES_REPERTOIRE", str(tmp_path))
        kernel = Kernel()
        plugin = await ajouter_fiches(kernel)
        assert plugin.fragments == []
        assert kernel.get_function("fiches", "rechercher_fiches") is not None

    asyncio.run(verifier())


def test_recherche_classement_et_citation(tmp_path):
    async def verifier():
        plugin = FichesPlugin(tmp_path)
        plugin.fragments = [
            ("autre.pdf", 1, "Livraison."),
            ("sous-dossier/garantie.pdf", 3, "Garantie de deux ans."),
        ]
        resultat = await plugin.rechercher_fiches("garantie", nombre=1)
        assert resultat == (
            "[Source : sous-dossier/garantie.pdf, page 3]\nGarantie de deux ans."
        )
        assert "Je ne trouve pas cette information" in await plugin.rechercher_fiches("inconnu")

    asyncio.run(verifier())


def test_indexation_pdf_et_decoupage(tmp_path):
    async def verifier():
        dossier = tmp_path / "fournisseur"
        dossier.mkdir()
        chemin = dossier / "fiche.PDF"
        chemin.touch()
        (tmp_path / "ignore.txt").write_text("ignore", encoding="utf-8")
        page_vide = Mock()
        page_vide.extract_text = lambda: ""
        page = Mock()
        page.extract_text = lambda: "Conditions de garantie et livraison. " * 600
        plugin = FichesPlugin(tmp_path)
        with patch("fiches_plugin.PdfReader") as lecteur:
            lecteur.return_value.pages = [page_vide, page]
            await plugin.indexer()
            lecteur.assert_called_once_with(chemin)
        assert plugin.fragments == [
            ("fournisseur/fiche.PDF", 2, page.extract_text().strip())
        ]

    asyncio.run(verifier())


def test_repertoire_vide_et_question_vide(tmp_path):
    async def verifier():
        plugin = FichesPlugin(tmp_path)
        await plugin.indexer()
        assert "Aucune fiche" in await plugin.rechercher_fiches("garantie")
        assert "preciser" in await plugin.rechercher_fiches("  ")

    asyncio.run(verifier())


def test_pdf_sans_texte(tmp_path):
    async def verifier():
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        writer.write(tmp_path / "scan.pdf")
        plugin = FichesPlugin(tmp_path)
        await plugin.indexer()
        assert plugin.fragments == []

    asyncio.run(verifier())


def test_erreurs_explicites(tmp_path):
    async def verifier():
        with pytest.raises(NotADirectoryError):
            await FichesPlugin(tmp_path / "absent").indexer()
        (tmp_path / "corrompu.pdf").write_bytes(b"pas un pdf")
        with pytest.raises(RuntimeError, match="corrompu.pdf"):
            await FichesPlugin(tmp_path).indexer()

    asyncio.run(verifier())