import asyncio
from datetime import datetime, timezone
import sys
from bleak.backends.device import BLEDevice

from labfreed.pac_id.pac_id import PAC_ID
from labfreed.trex.pythonic import pyTREX
from labfreed.trex.trex import TREX
from labfreed.labfreed_experimental.pac_disco.ble_uuid import PAC_Characteristics, ServiceUUID


from labfreed.labfreed_experimental.pac_disco.ble_central import BlePacCentral


import logging
from pathlib import Path

TEST = False

TEST_SERVICE_UUID = "c7660001-f42b-4f69-950a-2c973260386d"

# Log file path
LOG_PATH = Path("pac_central.log")
if TEST:
    STATUS_LOG_LVL = logging.DEBUG
else:
    STATUS_LOG_LVL = logging.INFO


def setup_logging() -> tuple[logging.Logger, logging.Logger]:
    """
    Returns:
        debug_log  - very verbose logger (writes to file)
        status_log - minimal logger (writes to console only)
    """
    # root logger: no handlers, no output by default
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    # ---- file handler: everything goes here ----
    file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )
    )
    root.addHandler(file_handler)

    # ---- console handler: only for "status" logger ----
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        logging.Formatter("%(message)s")  # simple console output
    )

    # verbose logger (goes to file via root)
    debug_log = logging.getLogger("pac.debug")
    debug_log.setLevel(logging.DEBUG)

    # minimal status logger (goes to file + console)
    status_log = logging.getLogger("pac.status")
    status_log.setLevel(STATUS_LOG_LVL)
    status_log.addHandler(console_handler)
    # avoid double-adding handlers if setup_logging() is called twice
    status_log.propagate = True  # still goes to file via root

    # mute third-party libraries on console (file still gets them)
    for noisy in ("bleak",):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    return debug_log, status_log





SAVED_PAC_ID_FILE= Path('saved_pac_id.txt')

async def handle_pac_id(device: BLEDevice, pac_id_url: str) -> None:
    
    loop = asyncio.get_running_loop()
    
    try:
        # a nasty hack to account for BUCHI R-300 sending an experimental pac-id, which is no longer valid
        pac_id_url = pac_id_url.replace('RNR', '21') 
        pac_id = PAC_ID.from_url(pac_id_url)
        summary = pyTREX.from_trex(pac_id.get_extension("SUM").trex)
            
        sum_lines = '\n  '.join([f"{k}:  {v}" for k,v in summary.items()])  
        prompt = (
            f"\n---\nDetected PAC-ID from {device.name} ({device.address}):\n"
            f"{pac_id_url} \nSummary:\n  {sum_lines}\n\n"
            "Save this PAC-ID? [give a description if you want to save. type 'N' if you want to discard] "
        )
        answer = await loop.run_in_executor(None, input, prompt)

        if not answer.upper() == "N":
            ts = datetime.now(timezone.utc).isoformat()
            with open(SAVED_PAC_ID_FILE, "a", encoding="utf-8") as f:
                f.write(f"{pac_id_url}\t{ts}\t{answer}\n")
            print("PAC-ID saved.")
        else:
            print("PAC-ID discarded.")
            
    except Exception as e:
        pass


    


async def run_scanner() -> None:
    if TEST:
        service_uuids = None#[TEST_SERVICE_UUID]
    else:
        service_uuids = ServiceUUID.all_uuid()
        
    
    debug_log, status_log = setup_logging()

    central = BlePacCentral(
        service_uuids=service_uuids,
        pac_characteristics=PAC_Characteristics,
        on_pac_id=handle_pac_id,
        status_log=status_log,
        debug_log=debug_log
    )

    await central.run()

    # example: after run() returns (Ctrl+C) you can inspect:
    for pac_url, ts in central.get_seen_pac_ids():
        print(ts.isoformat(), pac_url)


def main() -> None:
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_scanner())


if __name__ == "__main__":
    main()