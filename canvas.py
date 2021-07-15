import time
import socket
import re
import json
import traceback

import requests

# This should be updated to the static ip you assigned your canvas
SERVER_IP = "192.168.86.33"
# This should be updated to auth token of your canvas
AUTH_TOKEN = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

SERVER_PORT = 16021
SERVER_ADDRESS = f"http://{SERVER_IP}:{SERVER_PORT}"
API_PREFIX = "api/v1"


class CanvasController:
    """Used to control individual panels on a canvas"""

    def __init__(self, socket_address):
        self._socket_address = socket_address

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.settimeout(1)

    @classmethod
    def start_new_canvas_controller(cls):
        cls.wait_for_connection()
        resp = requests.put(
            f"{SERVER_ADDRESS}/api/v1/{AUTH_TOKEN}/effects",
            json={
                "write": {
                    "command": "display",
                    "animType": "extControl",
                    "extControlVersion": "v2",
                }
            },
        )
        resp.raise_for_status()

        socket_address = (SERVER_IP, 60222)

        return cls(socket_address=socket_address)

    @classmethod
    def wait_for_connection(cls):
        while True:
            try:
                resp = requests.get(f"{SERVER_ADDRESS}/{API_PREFIX}/{AUTH_TOKEN}", timeout=5)
                if resp.ok:
                    return
            except requests.RequestException as e:
                traceback.print_exc()
                time.sleep(2)

    def _send_to_socket(self, message_bytes):
        self._sock.sendto(message_bytes, self._socket_address)

    def set_color(self, panel_id, rgb, transition_time):
        r, g, b = rgb
        message_bytes = (
            (1).to_bytes(2, byteorder="big")
            + (panel_id).to_bytes(2, byteorder="big")
            + (r).to_bytes(1, byteorder="big")
            + (g).to_bytes(1, byteorder="big")
            + (b).to_bytes(1, byteorder="big")
            + (0).to_bytes(1, byteorder="big")
            + (transition_time).to_bytes(2, byteorder="big")
        )
        self._send_to_socket(message_bytes)

    def iter_touch_events(self):
        """
        yields an iterator with a tuple containing the panel id, and the gesture type

        possible gesture values and their meaning:
        0 Single Tap
        1 Double Tap
        2 Swipe Up
        3 Swipe Down
        4 Swipe Left
        5 Swipe Right
        """
        # touch events are associated with id = 4
        TOUCH_EVENTS_PORT = 58930
        while True:
            try:
                with requests.get(
                    f"{SERVER_ADDRESS}/{API_PREFIX}/{AUTH_TOKEN}/events?id=4",
                    stream=True,
                    headers={"TouchEventsPort": str(TOUCH_EVENTS_PORT)},
                ) as r:
                    print("started connection")
                    accumulator = ""
                    DELIM = "\n\n"
                    for content in r.iter_content(chunk_size=1, decode_unicode=True):
                        accumulator += content
                        if DELIM in accumulator:
                            touch_event, accumulator = accumulator.split("\n\n", 1)
                            _, data_line = touch_event.split("\n")
                            data = json.loads(re.match(r"data:(.*)", data_line).group(1))
                            for event in data["events"]:
                                yield event["panelId"], event["gesture"]

            # raises this when the connection cannot be established
            except requests.exceptions.ConnectTimeout as e:
                print("caught bad error no longer connected")
                traceback.print_exc()
                raise e

            except (
                requests.exceptions.Timeout,
                requests.exceptions.ConnectionError,
            ) as e:
                print("Didn't recieve an event in a long time in time")
                print(e)
                traceback.print_exc()
                continue

    @classmethod
    def get_panel_ids(cls):
        return sorted(
            [
                leaf["panelId"]
                for leaf in requests.get(
                    f"{SERVER_ADDRESS}/{API_PREFIX}/{AUTH_TOKEN}/panelLayout/layout"
                ).json()["positionData"]
            ]
        )

    def set_orienation(self, orientation):
        resp = requests.put(
            f"{SERVER_ADDRESS}/{API_PREFIX}/{AUTH_TOKEN}/panelLayout/globalOrientation",
            json={"globalOrientation": {"value": orientation}},
        )
        resp.raise_for_status()

    @classmethod
    def get_current_state(cls):
        """get the current state of the canvas. This includes all of the locations of the tiles in
        x and y coordinates.

        eg output:
        {
             "numPanels": 6,
             "positionData": [
                 {"o": 0, "panelId": 64509, "shapeType": 3, "x": 100, "y": 0},
                 {"o": 180, "panelId": 34304, "shapeType": 2, "x": 200, "y": 50},
                 {"o": 180, "panelId": 59567, "shapeType": 2, "x": 300, "y": 50},
                 {"o": 180, "panelId": 30126, "shapeType": 2, "x": 400, "y": 50},
                 {"o": 180, "panelId": 41205, "shapeType": 2, "x": 500, "y": 50},
                 {"o": 450, "panelId": 51253, "shapeType": 2, "x": 600, "y": 50},
             ],
             "sideLength": 100,
         }
        """
        try:
            resp = requests.get(f"{SERVER_ADDRESS}/{API_PREFIX}/{AUTH_TOKEN}/panelLayout/layout")

        except requests.RequestException as err:
            traceback.print_exc()
            raise err

        return resp.json()


class CanvasNumberDisplay:
    """uses a 4x7 grid of canvas tiles to display the numbers 1 through 9"""

    NUMBER_TO_DISPLAY_TILES = [
        [
            [False, True, True, False],
            [True, False, False, True],
            [True, False, False, True],
            [True, False, False, True],
            [True, False, False, True],
            [True, False, False, True],
            [False, True, True, False],
        ],
        [
            [False, False, True, False],
            [False, True, True, False],
            [True, False, True, False],
            [False, False, True, False],
            [False, False, True, False],
            [False, False, True, False],
            [False, True, True, True],
        ],
        [
            [False, True, True, False],
            [True, False, False, True],
            [False, False, False, True],
            [False, False, True, False],
            [False, True, False, False],
            [True, False, False, False],
            [True, True, True, True],
        ],
        [
            [False, True, True, False],
            [True, False, False, True],
            [False, False, False, True],
            [False, True, True, False],
            [False, False, False, True],
            [True, False, False, True],
            [False, True, True, False],
        ],
        [
            [True, False, False, True],
            [True, False, False, True],
            [True, False, False, True],
            [False, True, True, True],
            [False, False, False, True],
            [False, False, False, True],
            [False, False, False, True],
        ],
        [
            [True, True, True, True],
            [True, False, False, False],
            [True, True, True, False],
            [False, False, False, True],
            [False, False, False, True],
            [True, False, False, True],
            [False, True, True, False],
        ],
        [
            [False, True, True, False],
            [True, False, False, True],
            [True, False, False, False],
            [True, True, True, False],
            [True, False, False, True],
            [True, False, False, True],
            [False, True, True, False],
        ],
        [
            [True, True, True, True],
            [False, False, False, True],
            [False, False, False, True],
            [False, False, True, False],
            [False, False, True, False],
            [False, True, False, False],
            [False, True, False, False],
        ],
        [
            [False, True, True, False],
            [True, False, False, True],
            [True, False, False, True],
            [False, True, True, False],
            [True, False, False, True],
            [True, False, False, True],
            [False, True, True, False],
        ],
        [
            [False, True, True, False],
            [True, False, False, True],
            [True, False, False, True],
            [False, True, True, True],
            [False, False, False, True],
            [True, False, False, True],
            [False, True, True, False],
        ],
    ]

    ON_COLOR = (0, 0, 250)
    OFF_COLOR = (0, 0, 0)

    def _intialize_display_grid_pannel_ids(self):
        """find which panel ids should be associated with each index of the display grid and set
        them in self._display_grid_pannel_ids"""

        self._display_grid_pannel_ids = [
            [None, None, None, None],
            [None, None, None, None],
            [None, None, None, None],
            [None, None, None, None],
            [None, None, None, None],
            [None, None, None, None],
            [None, None, None, None],
        ]

        state = self._canvas_controller.get_current_state()
        position_data = state["positionData"]

        # for values are off by 1 sometimes
        def round_to_closest_50(num):
            return round(num / 50) * 50

        for pd in position_data:
            pd["x"] = round_to_closest_50(pd["x"])
            pd["y"] = round_to_closest_50(pd["y"])

        min_x = min(pd["x"] for pd in position_data)
        min_y = min(pd["y"] for pd in position_data)

        for pd in position_data:
            x_index = round((pd["x"] - min_x) / 100)
            y_index = round((pd["y"] - min_y) / 100)
            if 0 <= x_index <= 3 and 0 <= y_index <= 6:
                self._display_grid_pannel_ids[y_index][x_index] = pd["panelId"]

    def __init__(self, canvas_controller):
        self._canvas_controller = canvas_controller
        self._display_grid_pannel_ids = None

        self._intialize_display_grid_pannel_ids()

    def display_number(self, number):
        display_tiles = self.NUMBER_TO_DISPLAY_TILES[number]
        for y, row in enumerate(display_tiles):
            for x, is_tile_on in enumerate(row):
                color = self.ON_COLOR if is_tile_on else self.OFF_COLOR
                pannel_id = self._display_grid_pannel_ids[-y - 1][x]

                if pannel_id is None:
                    print(f"there was no panel for {x}, {y}")
                    continue
                self._canvas_controller.set_color(pannel_id, color, 2)

    def _initialize_grid(self):
        self._canvas_controller
