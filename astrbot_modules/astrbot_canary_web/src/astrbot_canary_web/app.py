from robyn import Robyn
from astrbot_canary_api.types import BROKER_TYPE
from logging import getLogger , Logger
logger: Logger = getLogger("astrbot_canary.module.web.app")

web_app = Robyn(__file__)

@web_app.startup_handler  # type: ignore[reportUnknownMemberType]
async def startup_handler() -> None:
    logger.info("Web app startup handler called")
    broker: BROKER_TYPE = web_app.dependencies.get_global_dependencies()["BROKER"]
    await broker.startup()



@web_app.get("/", const=True)
async def index() -> str:
    return "Hello Astrbot Canary Web!"




if __name__ == "__main__":
    # create a configured "Session" class
    web_app.start(host="0.0.0.0", port=8080)
