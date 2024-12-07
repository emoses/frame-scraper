import logging
from samsungtvws import SamsungTVWS
from typing import List


LOGGER = logging.getLogger(__name__)

class Tv:
    def __init__(self, ip: str):
        self.ip = ip

    def _get_tv(self) -> SamsungTVWS:
        return SamsungTVWS(self.ip, timeout=30)

    def upload(self, img: bytes) -> str:
        tv = self._get_tv()
        image_name = tv.art().upload(img, matte="none", portrait_matte="none")
        LOGGER.info(f"Uploaded {image_name}")
        tv.art().select_image(image_name)
        return  image_name

    def select(self, name: str) -> None:
        tv = self._get_tv()
        tv.art().select_image(name)

    def delete(self, names: List[str]) -> None:
        LOGGER.debug("Deleting %s", names)
        self._get_tv().art().delete_list(names)

    def list(self):
        return self._get_tv().art().available()
