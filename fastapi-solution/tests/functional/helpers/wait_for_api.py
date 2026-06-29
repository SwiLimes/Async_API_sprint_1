import aiohttp
import asyncio
import sys
from functional.settings import test_settings


async def wait_for_api():
    url = test_settings.service_url + "/health"

    for _ in range(30):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return

        await asyncio.sleep(1)

    sys.exit(1)


if __name__ == "__main__":
    asyncio.run(wait_for_api())
