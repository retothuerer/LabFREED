import asyncio
import logging
import sys
from datetime import datetime, timezone
from typing import Awaitable, Callable, Iterable, Dict

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from labfreed.pac_id.pac_id import PAC_ID
from labfreed_experimental.pac_disco.ble_uuid import PAC_Characteristics, ServiceUUID


TEST = True
TEST_SERVICE_UUID = "c7660001-f42b-4f69-950a-2c973260386d"

RSSI_THRESHOLD = -80

PacIdCallback = Callable[[BLEDevice, str], Awaitable[None]]


class BlePacCentral:
    """
    BLE central that scans for devices, connects, reads PAC_ID characteristics,
    tracks seen PAC IDs (with timestamps), and calls an injected async callback
    for each *new* PAC ID.
    """

    def __init__(
        self,
        *,
        service_uuids: Iterable[str],
        pac_characteristics: Iterable[PAC_Characteristics],
        on_pac_id: PacIdCallback,
        debug_log: logging.Logger, status_log: logging.Logger
    ) -> None:
        self._service_uuids = list(service_uuids)
        self._pac_characteristics = list(pac_characteristics)
        self._on_pac_id = on_pac_id
        self._log = debug_log
        self._status = status_log

        # pac_id_url -> first_seen_timestamp (UTC)
        self._seen_pac_ids: Dict[str, datetime] = {}

        # per-device lock to avoid overlapping connects/reads for same address
        self._per_device_lock: Dict[str, asyncio.Lock] = {}

        self._scanner: BleakScanner | None = None

    # ------- public API -------

    async def run(self) -> None:
        """Run scanner until Ctrl+C."""
        self._scanner = BleakScanner(
            detection_callback=self._detection_callback,
            service_uuids=self._service_uuids,
            scanning_mode="active",
        )

        await self._scanner.start()
        self._log.info("Scanning for BLE advertisements... Ctrl+C to stop.")
        try:
            while True:
                await asyncio.sleep(1.0)
        except KeyboardInterrupt:
            self._log.info("Stopping scanner...")
        finally:
            await self._scanner.stop()

    def get_seen_pac_ids(self) -> list[tuple[str, datetime]]:
        """
        Synchronous snapshot of all seen PAC IDs.

        Returns list of (pac_id_url, first_seen_utc) tuples.
        """
        return list(self._seen_pac_ids.items())

    # ------- internal helpers -------

    def _get_lock_for(self, address: str) -> asyncio.Lock:
        lock = self._per_device_lock.get(address)
        if lock is None:
            lock = asyncio.Lock()
            self._per_device_lock[address] = lock
        return lock

    def _detection_callback(self, device: BLEDevice, adv: AdvertisementData) -> None:
        msg = f"Detected ({device.address}) aka ({device.name}). Services:{adv.service_uuids}, RSSI:{adv.rssi} "
        self._log.info(msg)
        
        # ignore weak signals (far away)
        if adv.rssi is not None and adv.rssi < RSSI_THRESHOLD:
            return

        # only try connectable devices if info is present
        if hasattr(adv, "is_connectable") and not adv.is_connectable:
            return

        # schedule handling; per-device lock will serialize connects per address
        asyncio.create_task(self._handle_device(device))

    async def _handle_device(self, device: BLEDevice) -> None:
        lock = self._get_lock_for(device.address)
        async with lock:
            pac_id_url = await self._read_pac_id_url(device)
            if not pac_id_url:
                return

            # de-duplicate by PAC ID (not by device)
            if pac_id_url in self._seen_pac_ids:
                self._log.info(f"PAC-ID {pac_id_url} was already known")
                return

            # record first seen timestamp
            self._seen_pac_ids[pac_id_url] = datetime.now(timezone.utc)

            # fire user callback
            await self._on_pac_id(device, pac_id_url)

    async def _read_pac_id_url(self, device: BLEDevice) -> str:
        self._log.info(f"Connecting to {device.address} ({device.name})...")
        pac_id_url = ""

        try:
            # services_cache=False helps on Windows to avoid stale service info
            async with BleakClient(device) as client:
                for characteristic in self._pac_characteristics:
                    try:
                        raw = await client.read_gatt_char(characteristic.value)
                        if raw:
                            pac_id_url += raw.decode("utf-8")
                    except Exception as e:
                        self._log.warning(
                            f"{device.address} cannot read {characteristic.name}: {e!r}"
                        )

            if pac_id_url:
                self._log.info(f"PAC_ID {pac_id_url} was published")

        except Exception as e:
            self._log.error(f"Failed to connect to {device.address}: {e!r}")

        return pac_id_url
