"""Normalize artwork image fields when applying catalog or external URLs."""


def normalize_artwork_image_update(data: dict) -> dict:
    if "image_url" not in data:
        return data

    new_url = data["image_url"]
    if new_url is None:
        data.setdefault("image_thumbnail_url", None)
        data["image_width"] = None
        data["image_height"] = None
        data["image_mime_type"] = None
        data["image_file_size"] = None
        return data

    if "image_thumbnail_url" not in data and new_url.startswith("http"):
        data["image_thumbnail_url"] = new_url
        data["image_width"] = None
        data["image_height"] = None
        data["image_mime_type"] = None
        data["image_file_size"] = None

    return data
