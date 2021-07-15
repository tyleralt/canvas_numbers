import time
import traceback
from canvas import CanvasController, CanvasNumberDisplay


def main():
    """
    Run a demo on the local canvas controller displaying numbers 0 - 9
    """
    while True:
        try:
            canvas_controller = CanvasController.start_new_canvas_controller()
            canvas_number_display = CanvasNumberDisplay(canvas_controller)
            while True:
                for number in range(10):
                    print(f"displaying {number}")
                    canvas_number_display.display_number(number)
                    time.sleep(5)

        except Exception as e:
            print(e)
            traceback.print_exc()


if __name__ == "__main__":
    main()
