"""Native LSD coordinate compatibility on an existing PDF, not X-mark ground truth."""

import math
from pathlib import Path

import pytest

from conftest import require_real_fixture


@pytest.mark.slow
def test_native_lsd_preserves_real_pdf_lines():
    cv2 = pytest.importorskip("cv2", exc_type=ModuleNotFoundError)
    np = pytest.importorskip("numpy", exc_type=ModuleNotFoundError)
    pytest.importorskip("fitz", exc_type=ModuleNotFoundError)
    from lib.strikethrough_detection import _detect_lines_lsd, _render_page_to_image

    pdf = Path(__file__).resolve().parents[2] / "test_files/heidegger_pages_79-88.pdf"
    require_real_fixture(pdf)
    # One page only; same page and DPI as the parent's OpenCV shape receipt.
    image = _render_page_to_image(pdf, 0, dpi=300)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    native = cv2.createLineSegmentDetector(0).detect(gray)[0]
    assert native is not None
    assert len(native) > 1
    assert native.shape[1:] in ((4,), (1, 4))
    coordinates = native if native.ndim == 2 else native[:, 0, :]

    lines = _detect_lines_lsd(image)
    assert len(lines) == len(native)
    np.testing.assert_allclose(
        [(line.x1, line.y1, line.x2, line.y2) for line in lines], coordinates,
        rtol=0, atol=1e-5,
    )
    for line in lines:
        assert all(math.isfinite(value) for value in (
            line.x1, line.y1, line.x2, line.y2, line.length, line.angle,
            line.x_center, line.y_center,
        ))
        assert line.length > 0
        assert line.length == pytest.approx(math.hypot(line.x2 - line.x1, line.y2 - line.y1))
        assert -180 <= line.angle <= 180
        assert line.angle == pytest.approx(
            math.degrees(math.atan2(line.y2 - line.y1, line.x2 - line.x1))
        )
