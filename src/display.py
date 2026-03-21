from PIL import Image

from src.config import DisplayConfig


class SimulatorDisplay:
    def __init__(self, output_path: str):
        self.output_path = output_path

    def show(self, image: Image.Image):
        image.save(self.output_path)
        print(f"Saved display to {self.output_path}")


class InkyDisplay:
    def __init__(self, saturation: float = 0.5, rotation: int = 0):
        self.saturation = saturation
        self.rotation = rotation
        self._inky = None

    def _get_inky(self):
        if self._inky is None:
            from inky.auto import auto
            self._inky = auto()
        return self._inky

    def show(self, image: Image.Image):
        inky = self._get_inky()
        if self.rotation:
            image = image.rotate(self.rotation, expand=True)
        inky.set_image(image, saturation=self.saturation)
        inky.show()
        print("Display updated")


def create_display(config: DisplayConfig):
    if config.simulate:
        return SimulatorDisplay(config.output_path)
    return InkyDisplay(config.saturation, config.rotation)
