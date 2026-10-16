import asyncio

import streamlit as st
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.connectors.ai.open_ai import OpenAIChatPromptExecutionSettings
from semantic_kernel.contents import ChatHistory, FunctionCallContent

from agent_catalogue import INSTRUCTIONS_SYSTEME
from catalogue_plugin import CataloguePlugin
from config import creer_kernel
from fiches_plugin import ajouter_fiches


async def _initialiser_kernel():
    kernel = creer_kernel()
    kernel.add_plugin(CataloguePlugin(), plugin_name="catalogue")
    await ajouter_fiches(kernel)
    return kernel


async def _obtenir_reponse(kernel, historique):
    service = kernel.get_service(type=ChatCompletionClientBase)
    settings = OpenAIChatPromptExecutionSettings(
        function_choice_behavior=FunctionChoiceBehavior.Auto(),
    )
    return await service.get_chat_message_content(historique, settings, kernel=kernel)


def _nouvel_historique():
    historique = ChatHistory()
    historique.add_system_message(INSTRUCTIONS_SYSTEME)
    return historique


def _extraire_outils(messages):
    outils = []
    for message in messages:
        for item in message.items or []:
            if isinstance(item, FunctionCallContent):
                nom = item.function_name or item.name or "outil"
                outils.append(f"{item.plugin_name}.{nom}" if item.plugin_name else nom)
    return outils


st.set_page_config(page_title="Assistant catalogue")
st.title("Assistant catalogue")

if "runner" not in st.session_state:
    st.session_state.runner = asyncio.Runner()
    st.session_state.kernel = st.session_state.runner.run(_initialiser_kernel())
    st.session_state.historique = _nouvel_historique()
    st.session_state.conversation = []

_, bouton = st.columns([3, 2])
if bouton.button("Nouvelle conversation", use_container_width=True):
    st.session_state.historique = _nouvel_historique()
    st.session_state.conversation = []

for message in st.session_state.conversation:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("outils"):
            with st.expander("Outils appeles"):
                for outil in message["outils"]:
                    st.code(outil, language=None)

question = st.chat_input("Posez une question sur le catalogue ou les fournisseurs")
if question:
    st.session_state.conversation.append({"role": "user", "content": question})
    st.session_state.historique.add_user_message(question)
    nombre_messages = len(st.session_state.historique.messages)

    try:
        with st.spinner("Recherche en cours..."):
            reponse = st.session_state.runner.run(
                _obtenir_reponse(st.session_state.kernel, st.session_state.historique)
            )
        if reponse is None:
            contenu = "Aucune reponse recue."
            outils = []
        else:
            st.session_state.historique.add_message(reponse)
            contenu = reponse.content or "Aucune reponse recue."
            outils = _extraire_outils(
                st.session_state.historique.messages[nombre_messages:]
            )
        st.session_state.conversation.append(
            {"role": "assistant", "content": contenu, "outils": outils}
        )
    except Exception as erreur:
        st.session_state.conversation.append(
            {"role": "assistant", "content": f"Erreur : {erreur}"}
        )

    st.rerun()