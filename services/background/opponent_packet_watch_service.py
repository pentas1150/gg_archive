"""UDP 패킷 감시 - StarCraft.exe가 받는 패킷에서 상대 ID 추출.

앱 내부에서만 사용. 앱 시작 시 패킷 감시 시작, 추출 완료(None 포함) 시 중단,
LastReplay.rep 변경 시 다시 시작. 포트 미감지 시 5초 간격 리트라이.

실행 시 관리자 권한 필요 (Windows: Npcap 설치 권장)
"""

import socket
import threading

import psutil
from PySide6.QtCore import QObject
from scapy.all import IP, Raw, UDP, sniff

from common.event_bus import EventBus
from common.logger import get_logger


class OpponentPacketWatchService(QObject):
    """앱 내부 패킷 감시 서비스. EventBus.start_packet_monitoring 수신 시 감시 시작."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._logger = get_logger("opponent_packet_watch_service")
        self._event_bus = EventBus.instance()
        self._start_requested = threading.Event()
        self._stop_requested = threading.Event()
        self._worker_thread: threading.Thread | None = None
        # 캡처용 캐시 (감시 시작 시 초기화)
        self._local_ips: set[str] | None = None
        self._port_process_cache: dict[int, str | None] = {}

        self._event_bus.start_packet_monitoring.connect(self._on_start_requested)

    def _clear_port_process_cache(self) -> None:
        """포트-프로세스 캐시 초기화 (감시 시작 시 호출)."""
        self._port_process_cache = {}

    def _get_process_for_udp_port(self, local_port: int) -> str | None:
        """UDP 포트를 사용 중인 프로세스 이름 반환."""
        if local_port in self._port_process_cache:
            return self._port_process_cache[local_port]
        try:
            for conn in psutil.net_connections(kind="udp4"):
                if conn.laddr and conn.laddr.port == local_port and conn.pid:
                    try:
                        proc = psutil.Process(conn.pid)
                        name = proc.name()
                        self._port_process_cache[local_port] = name
                        return name
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
            self._port_process_cache[local_port] = None
        except (psutil.AccessDenied, AttributeError):
            self._port_process_cache[local_port] = None
        return None

    def _get_ports_used_by_starcraft(self) -> list[int]:
        """StarCraft.exe가 사용 중인 UDP 포트 목록 반환."""
        ports: list[int] = []
        try:
            for conn in psutil.net_connections(kind="udp4"):
                if conn.laddr and conn.laddr.port and conn.pid:
                    name = self._get_process_for_udp_port(conn.laddr.port)
                    if name == "StarCraft.exe":
                        ports.append(conn.laddr.port)
        except (psutil.AccessDenied, AttributeError):
            pass
        return ports

    def _extract_payload_data(self, payload: bytes) -> str | None:
        """패킷 payload에서 두 번째 문자열 필드(?? 구분자 이후) 추출."""
        sep = b"\x3f\x3f"  # "??"
        pos = payload.find(sep)
        if pos == -1:
            return None
        start = pos + len(sep)
        while start < len(payload) and payload[start] == 0:
            start += 1
        if start >= len(payload):
            return None
        end = start
        while end < len(payload) and payload[end] != 0:
            end += 1
        try:
            return payload[start:end].decode("utf-8", errors="ignore")
        except Exception:
            return None

    def _get_local_ips(self) -> set[str]:
        """현재 PC의 로컬 IP 주소 목록 조회."""
        if self._local_ips is not None:
            return self._local_ips
        local_ips: set[str] = {"127.0.0.1"}
        try:
            hostname = socket.gethostname()
            local_ips.add(socket.gethostbyname(hostname))
            for ip in socket.gethostbyname_ex(hostname)[2]:
                local_ips.add(ip)
        except socket.gaierror:
            pass
        self._local_ips = local_ips
        return local_ips

    def _on_start_requested(self):
        """패킷 감시 시작 요청 (메인 스레드)."""
        self._logger.debug("Packet monitoring start requested (app start or LastReplay.rep changed)")
        self._start_requested.set()

    def start(self):
        """워커 스레드 시작. 앱 시작 시 호출."""
        if self._worker_thread is not None and self._worker_thread.is_alive():
            return
        self._stop_requested.clear()
        self._worker_thread = threading.Thread(target=self._run_worker, daemon=True)
        self._worker_thread.start()
        self._logger.debug("OpponentPacketWatchService worker thread started")
        # 앱 시작 시 첫 감시 시작
        self._start_requested.set()

    def stop(self):
        """감시 중단 및 워커 스레드 종료."""
        self._logger.debug("OpponentPacketWatchService stop requested")
        self._stop_requested.set()
        self._start_requested.set()  # 워커가 wait 중이면 깨움
        if self._worker_thread is not None and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=10)
            self._worker_thread = None
        self._logger.debug("OpponentPacketWatchService stopped")

    def _run_worker(self):
        """워커: start 대기 → 포트 5초 리트라이 → sniff → 추출 완료 시 중단 → 반복."""
        while True:
            if self._stop_requested.is_set():
                self._logger.debug("Worker exiting (stop requested)")
                break
            # 시작 요청 대기 (이벤트 set 시에만 깨어남)
            self._start_requested.wait()
            if self._stop_requested.is_set():
                break
            self._start_requested.clear()

            self._clear_port_process_cache()
            self._logger.debug("Port process cache cleared")

            # StarCraft 포트 감지될 때까지 5초 간격 리트라이
            while not self._stop_requested.is_set():
                ports = self._get_ports_used_by_starcraft()
                if ports:
                    self._logger.debug("StarCraft UDP port(s) detected: %s", ports)
                    break
                self._logger.debug("StarCraft port not detected, retrying in 5 seconds")
                if self._stop_requested.wait(timeout=5):
                    break
            if self._stop_requested.is_set():
                break

            # 추출 완료 플래그 (packet_handler와 stop_filter에서 공유)
            extraction_done: list[bool] = [False]
            extracted_game_id_list: list[str | None] = [None]

            def packet_handler(pkt):
                if not pkt.haslayer(UDP) or not pkt.haslayer(Raw):
                    return
                if len(pkt) < 480:
                    return
                payload = pkt[Raw].load
                if not pkt.haslayer(IP):
                    return
                dst_ip = pkt[IP].dst
                if dst_ip not in self._get_local_ips():
                    return
                dst_port = pkt[UDP].dport
                if self._get_process_for_udp_port(dst_port) != "StarCraft.exe":
                    return
                extracted_game_id = self._extract_payload_data(payload)
                extracted_game_id_list[0] = extracted_game_id
                extraction_done[0] = True
                if extracted_game_id is not None:
                    self._logger.debug("Opponent extracted from packet: %s", extracted_game_id)
                    self._event_bus.opponent_detected_from_packet.emit(extracted_game_id_list[0])
                else:
                    self._logger.debug("Packet processed, no opponent id extracted (None)")

            def stop_filter(pkt):
                return extraction_done[0] or self._stop_requested.is_set()

            try:
                self._logger.debug("Sniff started (UDP, StarCraft.exe target)")
                sniff(filter="udp", prn=packet_handler, stop_filter=stop_filter, store=False)
                self._logger.debug("Sniff ended (extraction done or stop requested)")
            except Exception as e:
                self._logger.debug("Sniff failed (e.g. permission/Npcap): %s", e)
