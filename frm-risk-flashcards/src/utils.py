from pathlib import Path
from datetime import datetime
import shutil


def save_uploaded_image(
    uploaded_image,
    chapter,
    topic
):
    """
    Saves an uploaded image inside assets/uploads
    and returns its relative path.

    Returns
    -------
    str | None
        Relative path to the saved image.
    """

    if uploaded_image is None:
        return None

    uploads_dir = Path("assets") / "uploads"

    uploads_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    safe_chapter = (
        chapter.lower()
        .replace(" ", "_")
    )

    safe_topic = (
        topic.lower()
        .replace(" ", "_")
    )

    extension = Path(
        uploaded_image.name
    ).suffix

    filename = (
        f"{safe_chapter}_{safe_topic}_{timestamp}{extension}"
    )

    destination = uploads_dir / filename

    with open(destination, "wb") as f:
        shutil.copyfileobj(
            uploaded_image,
            f
        )

    return str(destination)