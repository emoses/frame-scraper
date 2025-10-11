import logging
from samsungtvws.async_art import SamsungTVAsyncArt
from typing import List


LOGGER = logging.getLogger(__name__)

class Tv:
    def __init__(self, ip: str):
        self.ip = ip

    def _get_tv(self) -> SamsungTVAsyncArt:
        return SamsungTVAsyncArt(self.ip, timeout=30)

    async def upload(self, img: bytes) -> str:
        tv = self._get_tv()
        image_name = await tv.upload(img, matte="none", portrait_matte="none")
        LOGGER.info(f"Uploaded {image_name}")
        await tv.select_image(image_name)
        return  image_name

    async def select(self, name: str) -> None:
        tv = self._get_tv()
        await tv.select_image(name)

    async def delete(self, names: List[str]) -> None:
        LOGGER.debug("Deleting %s", names)
        await self._get_tv().delete_list(names)

    async def list(self):
        return await self._get_tv().available()
