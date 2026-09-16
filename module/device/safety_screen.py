"""Recognize the recorded violation dialog before any task clicks through it."""
from functools import lru_cache
from pathlib import Path
import cv2


@lru_cache(maxsize=8)
def template(name):
    path = Path(__file__).with_name('safety_assets') / (name + '.png')
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise RuntimeError('Missing safety template: ' + str(path))
    return image


def matches(image, name, roi, threshold=0.88):
    if image is None or image.shape[:2] != (720, 1280):
        return False
    x, y, w, h = roi
    crop = image[y:y+h, x:x+w]
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    return cv2.minMaxLoc(cv2.matchTemplate(gray, template(name), cv2.TM_CCOEFF_NORMED))[1] >= threshold


def violation_visible(image):
    # Match title plus either the body or both action labels. The latter also
    # detects the notice behind the recorded disconnected-server overlay.
    if (matches(image, 'violation_title_covered', (540, 210, 210, 75)) and
            matches(image, 'disconnected_text', (428, 300, 430, 60))):
        return True
    if not matches(image, 'violation_title', (540, 210, 210, 75)):
        return False
    return (matches(image, 'violation_body', (440, 287, 395, 120)) or
            matches(image, 'disconnected_text', (428, 300, 430, 60)) or
            (matches(image, 'violation_immediate', (449, 415, 137, 85)) and
             matches(image, 'violation_automatic', (690, 415, 139, 85))))
