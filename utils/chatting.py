from collections import deque
from datetime import datetime
from pathlib import Path
from time import time

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "chattings"
if not DB_PATH.exists():
    DB_PATH.mkdir(parents=True)


def read_metadata(file):
    line = file.readline().decode().strip()
    if not line:
        return None, None
    id_, size = line.split(" ")
    return id_, int(size)


class ChatInstance:
    def __init__(self, room_id: str, allow_create: bool = True):
        if not allow_create and not (DB_PATH / f"{room_id}.db").exists():
            raise FileNotFoundError("Chat instance does not exist: " + room_id)
        self.room_id = room_id
        self.db_file = DB_PATH / f"{room_id}.db"

        IS_NEW = not self.db_file.exists()
        self.file = self.db_file.open("a+b")

        self.last_modified = self.db_file.stat().st_mtime

        if IS_NEW:
            self.write("-init-", "room is created at " + str(datetime.now()))

    def find(self, id_: str):
        file = self.file
        fn_seek = file.seek

        fn_seek(0)
        while True:
            cur_id, size = read_metadata(file)
            if cur_id is None or size is None:
                raise IndexError("ID not found: " + id_)
            if cur_id == id_:
                return file.read(size).decode()
            fn_seek(size + 1, 1)

    def findFrom(self, id_: str):
        file = self.file
        fn_seek = file.seek

        fn_seek(0)
        while True:
            cur_id, size = read_metadata(file)
            if cur_id is None or size is None:
                raise IndexError("ID not found: " + id_)
            if cur_id == id_:
                data = file.read(size)
                data_list = [data.decode()]
                while True:
                    fn_seek(1, 1)
                    next_id, next_size = read_metadata(file)
                    if next_id is None or next_size is None:
                        break
                    next_data = file.read(next_size)
                    data_list.append(next_data.decode())
                return data_list
            fn_seek(size + 1, 1)

    @property
    def first_id(self):
        self.file.seek(0)
        id_, _ = read_metadata(self.file)
        return id_

    @property
    def last_id(self):
        file = self.file
        fn_seek = file.seek

        fn_seek(0)
        last_id = None
        while True:
            cur_id, size = read_metadata(file)
            if cur_id is None or size is None:
                break
            last_id = cur_id
            fn_seek(size + 1, 1)
        if last_id is None:
            raise IndexError("No data in chat instance: " + self.room_id)
        return last_id

    def write(self, id_: str, data: str):
        file = self.file

        file.seek(0, 2)
        data_size = len(data)
        file.write(f"{id_} {data_size}\n".encode())
        file.write(data.encode())
        file.write(b"\n")
        file.flush()

        self.last_modified = time()

    def close(self):
        if hasattr(self, "file") and not self.file.closed:
            self.file.close()

    def __del__(self):
        self.close()


queue: deque[ChatInstance] = deque(maxlen=10)
