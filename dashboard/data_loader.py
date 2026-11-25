import csv
import os
import random

_SPEED_COLS = {"speed", "速度", "tốc_độ", "toc_do", "kph", "kmh", "km/h", "vel"}

def speed_to_risk(speed: int) -> int:
    if speed <= 0:
        base = 5
    elif speed <= 60:
        base = int(speed * 0.3)
    elif speed <= 100:
        base = 18 + int((speed - 60) * 0.8)
    else:
        base = 50 + int((speed - 100) * 1.5)
    return max(5, min(95, base + random.randint(-4, 4)))


class DataLoader:
    def __init__(self):
        self.rows: list = []
        self.index: int = 0
        self.loaded: bool = False
        self.file_name: str = ""
        self.looped: bool = False

    def load_csv(self, path: str) -> tuple:
        try:
            rows = []
            with open(path, newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                if reader.fieldnames is None:
                    return False, "ヘッダー行が見つかりません"

                speed_col = None
                for col in reader.fieldnames:
                    if col.strip().lower() in _SPEED_COLS:
                        speed_col = col
                        break

                if speed_col is None:
                    cols = reader.fieldnames
                    if len(cols) >= 2:
                        speed_col = cols[1]
                    else:
                        return False, f"Speed列が見つかりません: {list(reader.fieldnames)}"

                for row in reader:
                    raw = row.get(speed_col, "").strip()
                    if raw:
                        try:
                            rows.append(int(float(raw)))
                        except ValueError:
                            pass

            if not rows:
                return False, "有効なデータ行がありません"

            self.rows = rows
            self.index = 0
            self.loaded = True
            self.looped = False
            self.file_name = os.path.basename(path)
            return True, f"{len(rows)} 行読み込み完了"
        except Exception as e:
            return False, f"読み込みエラー: {e}"

    def next_speed(self) -> int:
        if not self.loaded or not self.rows:
            return random.randint(40, 140)
        speed = self.rows[self.index]
        self.index += 1
        if self.index >= len(self.rows):
            self.index = 0
            self.looped = True
        return speed

    @property
    def progress(self) -> tuple:
        return (self.index, len(self.rows))
