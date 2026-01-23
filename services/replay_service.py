import os
import re
import json
import subprocess
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Optional

from dto.replay import ReplayAnalysisDTO
from config.app_config import AppConfig


# 게임 속도별 FPS (Fastest가 일반적이지만 방어적으로 전체 포함)
FPS_BY_SPEED: dict[str, float] = {
    "SLOWEST": 8.0,
    "SLOWER": 10.0,
    "SLOW": 12.0,
    "NORMAL": 15.0,
    "FAST": 17.86,
    "FASTER": 20.83,
    "FASTEST": 23.81,
}


class ReplayService:
    def __init__(self):
        self.app_config = AppConfig.get_instance()

    def _safe_decode(self, b: bytes) -> str:
        '''
        screp 표준출력을 안전하게 문자열로 변환:
        - 우선 utf-8 시도, 실패 시 utf-8-sig, 마지막으로 'replace'
        - 앞뒤에 쓰레기 문자열이 붙는 경우를 대비해 JSON 시작/끝을 재탐색
        '''
        if not isinstance(b, (bytes, bytearray)):
            return str(b or "")
        try:
            s = b.decode("utf-8")
        except UnicodeDecodeError:
            try:
                s = b.decode("utf-8-sig")
            except UnicodeDecodeError:
                s = b.decode("utf-8", errors="replace")

        # 혹시 ANSI 로그가 앞에 붙어 있으면 첫 '{'부터 끝 '}'까지 잘라내기
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end != -1 and end > start:
            return s[start:end+1]
        return s

    def run_screp(self, rep_path: Path) -> dict[str, Any]:
        """screp CLI를 실행해 JSON을 반환(윈도우 UTF-8 안전 처리)"""
        env = os.environ.copy()
        env.setdefault("PYTHONIOENCODING", "utf-8")
        env.setdefault("LC_ALL", "C.UTF-8")
        env.setdefault("LANG", "C.UTF-8")

        print(f"[ReplayService] Running screp: {self.app_config.screp_path} {str(rep_path)}")

        proc = subprocess.run(
            [self.app_config.screp_path, str(rep_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            env=env,
        )

        out = self._safe_decode(proc.stdout)
        if not out.strip():
            err = self._safe_decode(proc.stderr)
            raise RuntimeError(f"screp 출력이 비어 있습니다. stderr={err!r}")

        try:
            return json.loads(out)
        except json.JSONDecodeError as e:
            err = self._safe_decode(proc.stderr)
            sample = out[:800]
            raise RuntimeError(f"JSON 파싱 실패: {e}. stdout 샘플={sample!r}, stderr={err!r}")

    def players_from_header(self, header: dict[str, Any]) -> list[dict[str, Any]]:
        """헤더에서 플레이어 배열 추출 (관전자 제외, pid 확보)"""
        raw_players = header.get("Players") or header.get("players") or []
        players: list[dict[str, Any]] = []
        for idx, p in enumerate(raw_players):
            name = (
                p.get("Name")
                or p.get("name")
                or p.get("PlayerName")
                or p.get("playerName")
                or "Unknown"
            )
            is_observer = (
                p.get("IsObserver") or p.get("isObserver") or p.get("Type") == "Observer"
            )
            if is_observer:
                continue
            pid = (
                p.get("ID")
                or p.get("Id")
                or p.get("PlayerID")
                or idx
            )
            players.append({
                "name": str(name),
                "pid": int(pid),
                "raw": p,
            })
        return players

    def map_from_header(self, header: dict[str, Any]) -> str:
        map_name: str = header['Map']
        cleaned_name = re.sub(r'[\x00-\x1F\x7F]', '', map_name)
        split_name = cleaned_name.split(' ')[:-1]

        return ' '.join(split_name)

    def opponent_race_from_players(self, players: list[dict[str, Any]], my_name: str) -> str:
        return [p["raw"]["Race"]["Name"] for p in players if p["name"] != my_name][0]

    def frames_and_speed(self, root: dict[str, Any]) -> tuple[Optional[int], Optional[str]]:
        """프레임 수와 게임 속도 문자열 추출"""
        header = root.get("Header") or root.get("header") or {}
        frames = (
            header.get("Frames")
            or root.get("Frames")
            or header.get("frames")
            or root.get("frames")
        )
        speed = (
            header.get("GameSpeed")
            or header.get("gameSpeed")
            or root.get("GameSpeed")
            or root.get("gameSpeed")
        )
        if isinstance(speed, str):
            speed = speed.upper()
        return (int(frames) if isinstance(frames, (int, float)) else None, speed)

    def frames_to_seconds(self, frames: int, speed: Optional[str]) -> float:
        fps = FPS_BY_SPEED.get(speed or "FASTEST", 23.81)
        return frames / fps

    def is_player_win(self, root: dict, players: list[dict], my_name: str) -> bool:
        if not root['Computed']['LeaveGameCmds']:
            return False

        lose_player_id: int | None = None
        for cmd in root['Computed']['LeaveGameCmds']:
            reason_type = cmd['Reason']['Name']
            if reason_type == 'Quit':
                lose_player_id = cmd['Reason']['ID']
                break
        else:
            raise Exception('No find losing player')

        for p in players:
            if p['raw']['ID'] == lose_player_id and p['name'] == my_name:
                return False
        return True

    def analyze_replay(self, rep_path: str, my_name: str) -> ReplayAnalysisDTO | None:
        data = self.run_screp(Path(rep_path))
        header = data.get("Header") or data.get("header") or {}
        players = self.players_from_header(header)
        map_name = self.map_from_header(header)
        race = self.opponent_race_from_players(players, my_name)

        if len(players) != 2:
            raise Exception(f"{rep_path} is not 1vs1 replay")

        frames, speed = self.frames_and_speed(data)
        seconds = self.frames_to_seconds(frames, speed) if frames is not None else None
        if not seconds or seconds < self.app_config.playtime_threshold:  # threshold 안에 들어가지 않으면 skip
            return None

        is_win = self.is_player_win(data, players, my_name)
        played_at = datetime.fromisoformat(header["StartTime"]).replace(tzinfo=UTC)

        return ReplayAnalysisDTO(
            opponent_id=[p["name"] for p in players if p["name"] != my_name][0],
            race=race,
            map_name=map_name,
            is_win=is_win,
            playtime=int(seconds),
            played_at=played_at
        )
