# agent_catalogue.py
# Agent conversationnel (console) : appels d'outils automatiques et historique multi-tours.
# L'agent est en lecture seule (utilisateur MySQL agent_ia, droit SELECT uniquement).
import asyncio

from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.connectors.ai.open_ai import OpenAIChatPromptExecutionSettings
from semantic_kernel.contents import ChatHistory

from catalogue_plugin import CataloguePlugin
from config import creer_kernel

INSTRUCTIONS_SYSTEME = """Tu es un assistant de consultation du catalogue produits.
Tu réponds uniquement en français.

Outils :
- Utilise systématiquement les outils pour toute question sur les produits, les fournisseurs, les prix, les stocks ou les statistiques.
- Ne réponds jamais de mémoire et n'invente jamais de données, de prix ou de quantités.
- Si un outil ne renvoie aucun résultat, dis-le clairement et propose de reformuler la recherche.

Lecture seule :
- Tu ne peux ni créer, ni modifier, ni supprimer de produit ou de stock.
- Si l'utilisateur demande une modification, explique poliment que tu es en consultation seule.

Présentation :
- Présente les résultats de façon lisible (liste ou tableau).
- Affiche les prix en euros et les quantités en stock telles que renvoyées par les outils.
- Signale clairement les produits en rupture ou en stock faible lorsqu'ils apparaissent.

Historique :
- Tiens compte des échanges précédents : si l'utilisateur fait référence à une réponse antérieure, appuie-toi sur ce contexte.
"""


async def main():
    kernel = creer_kernel()
    kernel.add_plugin(CataloguePlugin(), plugin_name="catalogue")

    service = kernel.get_service(type=ChatCompletionClientBase)
    settings = OpenAIChatPromptExecutionSettings(
        function_choice_behavior=FunctionChoiceBehavior.Auto(),
    )

    historique = ChatHistory()
    historique.add_system_message(INSTRUCTIONS_SYSTEME)

    print("Agent catalogue (lecture seule). Tapez 'quitter' pour sortir.")
    while True:
        question = input("\nVous : ").strip()
        if question.lower() in {"quitter", "exit"}:
            break
        if not question:
            continue

        historique.add_user_message(question)
        reponse = await service.get_chat_message_content(historique, settings, kernel=kernel)
        if reponse is None:
            print("\nAgent : aucune réponse reçue.")
            continue

        # Semantic Kernel n'ajoute pas la réponse finale à l'historique : on l'ajoute explicitement.
        historique.add_message(reponse)
        print(f"\nAgent : {reponse.content}")


if __name__ == "__main__":
    asyncio.run(main())
