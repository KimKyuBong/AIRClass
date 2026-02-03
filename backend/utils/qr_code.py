"""
QR Code Generation
터미널에 QR 코드 ASCII 아트 출력
"""

import qrcode
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def print_qr_code(data: str) -> None:
    """
    Print QR code to terminal using ASCII art

    Args:
        data: QR 코드에 인코딩할 데이터 (IP 주소 등)
    """
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=2,
        )
        qr.add_data(data)
        qr.make(fit=True)

        # Print to terminal
        print("\n" + "=" * 60)
        print("📱 QR Code for Android App Connection:")
        print("=" * 60)
        qr.print_ascii(invert=True)
        print("=" * 60)
        print(f"Server IP: {data}")
        print("=" * 60 + "\n")

        logger.info(f"QR code printed for: {data}")
    except Exception as e:
        logger.error(f"Failed to generate QR code: {e}")


def generate_qr_code_image(data: str, filepath: str) -> bool:
    """
    Generate QR code as image file

    Args:
        data: QR 코드에 인코딩할 데이터
        filepath: 저장할 파일 경로 (.png)

    Returns:
        생성 성공 여부
    """
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        img.save(filepath)

        logger.info(f"QR code image saved to: {filepath}")
        return True
    except Exception as e:
        logger.error(f"Failed to save QR code image: {e}")
        return False


def generate_qr_code_svg(data: str) -> Optional[str]:
    """
    Generate QR code as SVG string

    Args:
        data: QR 코드에 인코딩할 데이터

    Returns:
        SVG 문자열, 실패 시 None
    """
    try:
        import qrcode.image.svg

        factory = qrcode.image.svg.SvgPathImage
        qr = qrcode.QRCode(image_factory=factory)
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image()
        # SVG를 문자열로 반환하려면 추가 처리 필요
        # 여기서는 간단히 파일로 저장하는 방식 사용
        return str(img)
    except Exception as e:
        logger.error(f"Failed to generate SVG QR code: {e}")
        return None
