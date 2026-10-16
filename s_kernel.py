# semantic_kernel.py

import asyncio

from semantic_kernel.functions import KernelArguments

from catalogue_plugin import CataloguePlugin
from config import creer_kernel


async def main():
    kernel = creer_kernel()
    kernel.add_plugin(CataloguePlugin(), plugin_name="catalogue")


asyncio.run(main())
