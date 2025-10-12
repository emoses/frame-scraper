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
        async with self._get_tv() as tv:
            image_name = await tv.upload(img, matte="none", portrait_matte="none")
            LOGGER.info(f"Uploaded {image_name}")
            await tv.select_image(image_name)
        return  image_name

    async def select(self, name: str) -> None:
        async with self._get_tv() as tv:
            await tv.select_image(name)

    async def delete(self, names: List[str]) -> None:
        LOGGER.debug("Deleting %s", names)
        async with self._get_tv() as tv:
            await tv.delete_list(names)

    async def list(self):
        async with self._get_tv() as tv:
            return await tv.available()
