import asyncio
import time
from pathlib import Path
from typing import Any, AsyncIterator
from uuid import UUID

import cv2
import numpy as np
from webai_element_sdk.comms.messages import ColorFormat, Frame
from webai_element_sdk.element import Context, Element
from webai_element_sdk.element.settings import (
    BoolSetting,
    ElementSettings,
    NumberSetting,
    TextSetting,
)
from webai_element_sdk.element.variables import ElementOutputs, Output


class Settings(ElementSettings):
    video_file = TextSetting(
        name="video_file",
        display_name="Video File",
        description="The path to the video file to be loaded.",
        default="",
        hints=["file_path"],
        required=False,
    )
    image_directory = TextSetting(
        name="image_directory",
        display_name="Image Directory",
        description="The path to the image directory to be loaded.",
        default="",
        hints=["folder_path"],
        required=False,
    )
    frame_rate = NumberSetting[int](
        name="frame_rate",
        display_name="Frame Rate",
        description="Number of frames to emit per second. Affects delay between frame outputs.",
        default=0,
        hints=["advanced"],
    )
    stay_alive = BoolSetting(
        name="stay_alive",
        display_name="Stay Alive",
        description="Toggle to keep element running indefinitely after files complete.",
        default=True,
        hints=["advanced"],
    )


class Outputs(ElementOutputs):
    default = Output[Frame]()


element = Element(
    id=UUID("1916c9ba-fca7-4ed3-b773-11f400def123"),
    name="media_loader",
    display_name="Media Loader",
    version="0.4.0",
    description="Imports videos and images into the application so that AI models can use them for inference",
    outputs=Outputs(),
    settings=Settings(),
)


def _load_video_file(video: cv2.VideoCapture, frame_rate: int):
    # total_frames: int = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    counter: int = 0

    while video.isOpened():
        ret, frame = video.read()

        if not ret:
            print("End of file reached.")
            break

        counter += 1
        # print(f"Loading frame {counter}/{total_frames} ({frame_rate}fps)...")

        yield frame

    video.release()


def _load_images_from_directory(filepath: Path):
    supported_extensions = [".jpg", ".png", ".jpeg", ".npy", ".raw"]

    for file in filepath.iterdir():
        if file.is_file() and file.suffix.lower() in supported_extensions:
            try:
                time.sleep(0.5)  # Optional: remove or adjust as needed
                image = cv2.imread(str(file))
                if image is not None:
                    yield image
            except Exception:
                continue


@element.executor  # type: ignore
async def run(ctx: Context[None, Outputs, Settings]) -> AsyncIterator[Any]:
    try:
        frame_rate: int = ctx.settings.frame_rate.value
        stay_alive: bool = ctx.settings.stay_alive.value
        await ctx.logger.log(f"Starting media loader execution")

        # ── resolve user-supplied path ─────────────────────────────────────────────
        media_path = ctx.settings.video_file.value or ctx.settings.image_directory.value
        if not media_path:
            await ctx.logger.log("No media path provided in settings")
            raise ValueError("No media path provided. Quitting…")

        media_path_obj = Path(media_path).resolve()
        await ctx.logger.log(f"Resolved media path: {media_path_obj}")

        if not media_path_obj.exists():
            await ctx.logger.log(f"Media path does not exist: {media_path_obj}")
            raise ValueError(f"Media path does not exist: {media_path_obj}")

        # helper that (re)instantiates the appropriate generator -------------------
        def build_generator():
            if media_path_obj.is_dir():
                return _load_images_from_directory(media_path_obj)
            if media_path_obj.suffix.lower() in {".mp4", ".avi", ".mov"}:
                video = cv2.VideoCapture(str(media_path_obj))
                if not video.isOpened():
                    raise ValueError(f"Failed to open video file: {media_path_obj}")

                nonlocal frame_rate
                if frame_rate == 0:
                    detected_fps = int(video.get(cv2.CAP_PROP_FPS))
                    frame_rate = detected_fps

                return _load_video_file(video, frame_rate)
            raise ValueError(f"{media_path} is not a supported type or format")

        # ── main playback loop ────────────────────────────────────────────────────
        ran_once = False  # remember we finished first pass
        loop_count = 0
        frame_count = 0

        while True:
            loop_count += 1

            if not stay_alive and ran_once:
                # await ctx.logger.log(
                #     "Playback completed and stay_alive is False. Continuing with brief sleep."
                # )
                # If we've run once and stay_alive is False, wait briefly before checking again
                await asyncio.sleep(0.1)
                continue

            try:
                generator = build_generator()
                next_frame_time = time.perf_counter()

                for img in generator:
                    if frame_rate:
                        wait = next_frame_time - time.perf_counter()
                        if wait > 0:
                            time.sleep(wait)
                        next_frame_time += 1 / frame_rate

                    if img is None:
                        await ctx.logger.log("Received None image, skipping frame")
                        continue

                    try:
                        image_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                        frame_count += 1

                        if frame_count % 100 == 0:  # Log every 100 frames
                            await ctx.logger.log(f"Yielding frame {frame_count}")

                        yield ctx.outputs.default(
                            Frame(
                                ndframe=np.asarray(image_rgb),
                                rois=[],
                                color_space=ColorFormat.BGR,
                            )
                        )
                    except Exception as e:
                        await ctx.logger.log(
                            f"Error processing frame {frame_count}: {e}"
                        )
                        continue

                # we have finished one full pass
                ran_once = True
                await ctx.logger.log(
                    f"Completed playback pass {loop_count}. Total frames yielded: {frame_count}"
                )

            except Exception as e:
                await ctx.logger.log(
                    f"Error in playback loop iteration {loop_count}: {e}"
                )
                if not stay_alive:
                    raise
                # If stay_alive is True, continue to next iteration
                await asyncio.sleep(1)  # Brief pause before retrying

    except Exception as e:
        await ctx.logger.log(f"Unhandled error in media loader: {e}")
        print(f"Critical error: {e}")
        raise
