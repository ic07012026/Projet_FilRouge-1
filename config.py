# config.py
# Crée le "Kernel" de Semantic Kernel, connecté à notre déploiement Azure OpenAI.
# Tous les scripts du projet l'importent : from config import creer_kernel
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

load_dotenv(Path(__file__).resolve().parent / ".env")


def creer_kernel():
    # Le même client que dans les projets précédents (API v1 d'Azure OpenAI),
    # mais en version "Async" car Semantic Kernel travaille en asynchrone.
    client = AsyncOpenAI(
        base_url=os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/") + "/openai/v1/",
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
    )

    # Le "service" = le LLM que le Kernel va utiliser
    service = OpenAIChatCompletion(
        ai_model_id=os.environ["CHAT_DEPLOYMENT"],  # le NOM DU DÉPLOIEMENT
        async_client=client,
    )

    # Le Kernel = le chef d'orchestre : il connaît le LLM et les plugins
    kernel = Kernel()
    kernel.add_service(service)
    return kernel
