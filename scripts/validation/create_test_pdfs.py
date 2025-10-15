#!/usr/bin/env python3
"""
Create comprehensive test PDFs with known ground truth for formatting validation.

Generates:
1. test_digital_formatting.pdf - Born-digital with native PDF formatting
2. test_xmarks_and_strikethrough.pdf - Simulated X-marks and strikethrough
3. test_mixed_formatting.pdf - Complex combinations
4. test_formatting_ground_truth.json - Complete ground truth data
"""

import json
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

OUTPUT_DIR = Path("test_files")
OUTPUT_DIR.mkdir(exist_ok=True)


def create_digital_formatting_pdf():
    """Test PDF 1: Born-Digital with native PDF formatting."""
    output_path = OUTPUT_DIR / "test_digital_formatting.pdf"
    c = canvas.Canvas(str(output_path), pagesize=letter)
    width, height = letter

    y_position = height - 100
    line_height = 30

    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, y_position, "Test PDF 1: Digital Formatting")
    y_position -= line_height * 1.5

    # 1. Bold text
    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, y_position, "This is bold")
    y_position -= line_height

    # 2. Italic text
    c.setFont("Helvetica-Oblique", 12)
    c.drawString(100, y_position, "This is italic")
    y_position -= line_height

    # 3. Bold + Italic
    c.setFont("Helvetica-BoldOblique", 12)
    c.drawString(100, y_position, "This is both")
    y_position -= line_height

    # 4. Underline (draw line under text)
    c.setFont("Helvetica", 12)
    text = "This is underlined"
    c.drawString(100, y_position, text)
    text_width = c.stringWidth(text, "Helvetica", 12)
    c.line(100, y_position - 2, 100 + text_width, y_position - 2)
    y_position -= line_height

    # 5. Horizontal strikethrough (line through middle)
    c.setFont("Helvetica", 12)
    text = "This is deleted"
    c.drawString(100, y_position, text)
    text_width = c.stringWidth(text, "Helvetica", 12)
    # Draw line through middle of text (at baseline + half x-height)
    c.line(100, y_position + 4, 100 + text_width, y_position + 4)
    y_position -= line_height

    # 6. Superscript
    c.setFont("Helvetica", 12)
    c.drawString(100, y_position, "Footnote")
    c.setFont("Helvetica", 8)
    c.drawString(100 + c.stringWidth("Footnote", "Helvetica", 12), y_position + 4, "1")
    y_position -= line_height

    # 7. Subscript
    c.setFont("Helvetica", 12)
    c.drawString(100, y_position, "H")
    c.setFont("Helvetica", 8)
    x_h = 100 + c.stringWidth("H", "Helvetica", 12)
    c.drawString(x_h, y_position - 3, "2")
    c.setFont("Helvetica", 12)
    c.drawString(x_h + c.stringWidth("2", "Helvetica", 8), y_position, "O")
    y_position -= line_height

    # 8. Monospace (simulate with Courier)
    c.setFont("Courier", 12)
    c.drawString(100, y_position, "code text")
    y_position -= line_height

    c.save()
    print(f"✓ Created: {output_path}")

    return {
        "test_digital_formatting.pdf": {
            "page_1": [
                {"text": "This is bold", "formatting": ["bold"], "y_approx": height - 145},
                {"text": "This is italic", "formatting": ["italic"], "y_approx": height - 175},
                {"text": "This is both", "formatting": ["bold", "italic"], "y_approx": height - 205},
                {"text": "This is underlined", "formatting": ["underline"], "y_approx": height - 235},
                {"text": "This is deleted", "formatting": ["strikethrough"], "y_approx": height - 265},
                {"text": "Footnote", "formatting": [], "y_approx": height - 295},
                {"text": "1", "formatting": ["superscript"], "y_approx": height - 291},
                {"text": "H", "formatting": [], "y_approx": height - 325},
                {"text": "2", "formatting": ["subscript"], "y_approx": height - 328},
                {"text": "O", "formatting": [], "y_approx": height - 325},
                {"text": "code text", "formatting": ["monospaced"], "y_approx": height - 355},
            ]
        }
    }


def create_xmarks_and_strikethrough_pdf():
    """Test PDF 2: Simulated X-marks (sous-erasure) and strikethrough."""
    output_path = OUTPUT_DIR / "test_xmarks_and_strikethrough.pdf"
    c = canvas.Canvas(str(output_path), pagesize=letter)
    width, height = letter

    y_position = height - 100
    line_height = 40

    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, y_position, "Test PDF 2: X-Marks and Strikethrough")
    y_position -= line_height * 1.5

    ground_truth = []

    # 1. X-marked word (sous-erasure style)
    c.setFont("Helvetica", 12)
    text1 = "Being"
    x1, y1 = 100, y_position
    c.drawString(x1, y1, text1)
    text_width = c.stringWidth(text1, "Helvetica", 12)
    # Draw X over it (diagonal lines crossing)
    c.setStrokeColor(colors.black)
    c.setLineWidth(1.5)
    # Diagonal / (bottom-left to top-right)
    c.line(x1 - 2, y1 - 3, x1 + text_width + 2, y1 + 12)
    # Diagonal \ (top-left to bottom-right)
    c.line(x1 - 2, y1 + 12, x1 + text_width + 2, y1 - 3)
    ground_truth.append({"text": text1, "formatting": ["sous-erasure"], "y_approx": y1})
    y_position -= line_height

    # 2. Regular text (no formatting)
    c.setFont("Helvetica", 12)
    text2 = "Normal text without formatting"
    c.drawString(100, y_position, text2)
    ground_truth.append({"text": text2, "formatting": [], "y_approx": y_position})
    y_position -= line_height

    # 3. Horizontal strikethrough
    c.setFont("Helvetica", 12)
    text3 = "Deleted text"
    x3, y3 = 100, y_position
    c.drawString(x3, y3, text3)
    text_width = c.stringWidth(text3, "Helvetica", 12)
    c.line(x3, y3 + 4, x3 + text_width, y3 + 4)
    ground_truth.append({"text": text3, "formatting": ["strikethrough"], "y_approx": y3})
    y_position -= line_height

    # 4. Another X-marked word
    c.setFont("Helvetica", 12)
    text4 = "presence"
    x4, y4 = 100, y_position
    c.drawString(x4, y4, text4)
    text_width = c.stringWidth(text4, "Helvetica", 12)
    c.line(x4 - 2, y4 - 3, x4 + text_width + 2, y4 + 12)
    c.line(x4 - 2, y4 + 12, x4 + text_width + 2, y4 - 3)
    ground_truth.append({"text": text4, "formatting": ["sous-erasure"], "y_approx": y4})
    y_position -= line_height

    # 5. Underline (to verify we DON'T detect as strikethrough)
    c.setFont("Helvetica", 12)
    text5 = "Emphasized text"
    x5, y5 = 100, y_position
    c.drawString(x5, y5, text5)
    text_width = c.stringWidth(text5, "Helvetica", 12)
    c.line(x5, y5 - 2, x5 + text_width, y5 - 2)
    ground_truth.append({"text": text5, "formatting": ["underline"], "y_approx": y5})
    y_position -= line_height

    # 6. Third X-marked word
    c.setFont("Helvetica", 12)
    text6 = "trace"
    x6, y6 = 100, y_position
    c.drawString(x6, y6, text6)
    text_width = c.stringWidth(text6, "Helvetica", 12)
    c.line(x6 - 2, y6 - 3, x6 + text_width + 2, y6 + 12)
    c.line(x6 - 2, y6 + 12, x6 + text_width + 2, y6 - 3)
    ground_truth.append({"text": text6, "formatting": ["sous-erasure"], "y_approx": y6})
    y_position -= line_height

    # 7. Another horizontal strikethrough
    c.setFont("Helvetica", 12)
    text7 = "Removed word"
    x7, y7 = 100, y_position
    c.drawString(x7, y7, text7)
    text_width = c.stringWidth(text7, "Helvetica", 12)
    c.line(x7, y7 + 4, x7 + text_width, y7 + 4)
    ground_truth.append({"text": text7, "formatting": ["strikethrough"], "y_approx": y7})

    c.save()
    print(f"✓ Created: {output_path}")

    return {
        "test_xmarks_and_strikethrough.pdf": {
            "page_1": ground_truth
        }
    }


def create_mixed_formatting_pdf():
    """Test PDF 3: Mixed and complex formatting combinations."""
    output_path = OUTPUT_DIR / "test_mixed_formatting.pdf"
    c = canvas.Canvas(str(output_path), pagesize=letter)
    width, height = letter

    y_position = height - 100
    line_height = 40

    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, y_position, "Test PDF 3: Mixed Formatting")
    y_position -= line_height * 1.5

    ground_truth = []

    # 1. Bold + horizontal strikethrough
    c.setFont("Helvetica-Bold", 12)
    text1 = "deleted bold"
    x1, y1 = 100, y_position
    c.drawString(x1, y1, text1)
    text_width = c.stringWidth(text1, "Helvetica-Bold", 12)
    c.line(x1, y1 + 4, x1 + text_width, y1 + 4)
    ground_truth.append({"text": text1, "formatting": ["bold", "strikethrough"], "y_approx": y1})
    y_position -= line_height

    # 2. Italic + underline
    c.setFont("Helvetica-Oblique", 12)
    text2 = "underlined emphasis"
    x2, y2 = 100, y_position
    c.drawString(x2, y2, text2)
    text_width = c.stringWidth(text2, "Helvetica-Oblique", 12)
    c.line(x2, y2 - 2, x2 + text_width, y2 - 2)
    ground_truth.append({"text": text2, "formatting": ["italic", "underline"], "y_approx": y2})
    y_position -= line_height

    # 3. Bold + Italic + X-marks (sous-erasure)
    c.setFont("Helvetica-BoldOblique", 12)
    text3 = "complex"
    x3, y3 = 100, y_position
    c.drawString(x3, y3, text3)
    text_width = c.stringWidth(text3, "Helvetica-BoldOblique", 12)
    c.line(x3 - 2, y3 - 3, x3 + text_width + 2, y3 + 12)
    c.line(x3 - 2, y3 + 12, x3 + text_width + 2, y3 - 3)
    ground_truth.append({"text": text3, "formatting": ["bold", "italic", "sous-erasure"], "y_approx": y3})
    y_position -= line_height

    # 4. Paragraph with mixed formatting
    c.setFont("Helvetica", 12)
    x_start = 100
    y_para = y_position

    # "Some "
    text_part1 = "Some "
    c.drawString(x_start, y_para, text_part1)
    x_offset = c.stringWidth(text_part1, "Helvetica", 12)
    ground_truth.append({"text": text_part1.strip(), "formatting": [], "y_approx": y_para})

    # "deleted " (with strikethrough)
    text_part2 = "deleted "
    x2_start = x_start + x_offset
    c.drawString(x2_start, y_para, text_part2)
    text2_width = c.stringWidth(text_part2, "Helvetica", 12)
    c.line(x2_start, y_para + 4, x2_start + text2_width, y_para + 4)
    x_offset += text2_width
    ground_truth.append({"text": text_part2.strip(), "formatting": ["strikethrough"], "y_approx": y_para})

    # "text with "
    text_part3 = "text with "
    x3_start = x_start + x_offset
    c.drawString(x3_start, y_para, text_part3)
    x_offset += c.stringWidth(text_part3, "Helvetica", 12)
    ground_truth.append({"text": text_part3.strip(), "formatting": [], "y_approx": y_para})

    # "bold " (bold)
    c.setFont("Helvetica-Bold", 12)
    text_part4 = "bold "
    x4_start = x_start + x_offset
    c.drawString(x4_start, y_para, text_part4)
    x_offset += c.stringWidth(text_part4, "Helvetica-Bold", 12)
    ground_truth.append({"text": text_part4.strip(), "formatting": ["bold"], "y_approx": y_para})

    # "and "
    c.setFont("Helvetica", 12)
    text_part5 = "and "
    x5_start = x_start + x_offset
    c.drawString(x5_start, y_para, text_part5)
    x_offset += c.stringWidth(text_part5, "Helvetica", 12)
    ground_truth.append({"text": text_part5.strip(), "formatting": [], "y_approx": y_para})

    # "italic" (italic)
    c.setFont("Helvetica-Oblique", 12)
    text_part6 = "italic"
    x6_start = x_start + x_offset
    c.drawString(x6_start, y_para, text_part6)
    ground_truth.append({"text": text_part6, "formatting": ["italic"], "y_approx": y_para})

    c.save()
    print(f"✓ Created: {output_path}")

    return {
        "test_mixed_formatting.pdf": {
            "page_1": ground_truth
        }
    }


def main():
    """Create all test PDFs and ground truth."""
    print("Creating comprehensive test PDFs with ground truth...")
    print()

    # Generate all test PDFs
    ground_truth_data = {}

    print("1. Creating digital formatting test PDF...")
    ground_truth_data.update(create_digital_formatting_pdf())

    print("\n2. Creating X-marks and strikethrough test PDF...")
    ground_truth_data.update(create_xmarks_and_strikethrough_pdf())

    print("\n3. Creating mixed formatting test PDF...")
    ground_truth_data.update(create_mixed_formatting_pdf())

    # Save ground truth JSON
    ground_truth_path = OUTPUT_DIR / "test_formatting_ground_truth.json"
    with open(ground_truth_path, 'w', encoding='utf-8') as f:
        json.dump(ground_truth_data, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Ground truth saved to: {ground_truth_path}")
    print("\n✅ All test PDFs created successfully!")
    print("\nNext steps:")
    print("1. Run: python test_formatting_extraction.py")
    print("2. Review the extraction accuracy report")
    print("3. Identify gaps and prioritize fixes")


if __name__ == "__main__":
    main()
