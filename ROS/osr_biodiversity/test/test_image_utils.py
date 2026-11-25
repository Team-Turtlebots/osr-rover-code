import pytest

np = pytest.importorskip('numpy')

from osr_biodiversity.image_utils import ros_image_to_bgr  # noqa: E402


def test_rgb8_is_flipped_to_bgr():
    data = bytes([10, 20, 30, 40, 50, 60])            # 1 row, 2 pixels
    img = ros_image_to_bgr('rgb8', 1, 2, 6, data)
    assert img.shape == (1, 2, 3)
    assert img[0, 0].tolist() == [30, 20, 10]


def test_row_padding_is_ignored():
    data = bytes([1, 2, 3, 0, 0, 4, 5, 6, 0, 0])      # step 5, width 1
    img = ros_image_to_bgr('bgr8', 2, 1, 5, data)
    assert img[:, 0].tolist() == [[1, 2, 3], [4, 5, 6]]


def test_mono8_becomes_three_channels():
    img = ros_image_to_bgr('mono8', 1, 2, 2, bytes([7, 9]))
    assert img[0].tolist() == [[7, 7, 7], [9, 9, 9]]


def test_unsupported_encoding_raises():
    with pytest.raises(ValueError):
        ros_image_to_bgr('bayer_rggb8', 1, 1, 1, bytes([0]))


def test_short_data_raises():
    with pytest.raises(ValueError):
        ros_image_to_bgr('rgb8', 2, 2, 6, bytes(6))
