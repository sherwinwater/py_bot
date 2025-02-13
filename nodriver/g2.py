from typing import List
import nodriver as uc
import asyncio


async def main():
    browser = await uc.start()
    page = await browser.get("https://www.g2.com/products/g2/reviews")
    await asyncio.sleep(10)


if __name__ == "__main__":
    uc.loop().run_until_complete(main())