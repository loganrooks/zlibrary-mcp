import os
import argparse  # Import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader # To handle PIL images

# Define paths relative to the script location
SCRIPT_DIR = Path(__file__).parent
DEFAULT_FIXTURE_DIR = SCRIPT_DIR.parent / "__tests__" / "python" / "fixtures" / "rag_robustness"
DEFAULT_IMAGE_FILENAME = "blank_image_temp.png"
DEFAULT_IMAGE_PATH = SCRIPT_DIR / DEFAULT_IMAGE_FILENAME

def create_placeholder_image(path, size=(100, 50), color="white"):
    """Creates a simple blank image or an image with text."""
    img = Image.new('RGB', size, color=color)
    # Optional: Add text to distinguish if needed, but for image-only, blank is fine
    # d = ImageDraw.Draw(img)
    # d.text((10,10), "Placeholder", fill=(0,0,0))
    img.save(path)
    print(f"Created placeholder image: {path}")

def create_pdf_from_image(pdf_path, image_path):
    """Creates a PDF containing only the specified image."""
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    width, height = letter
    if not os.path.exists(image_path):
        print(f"Error: Image file not found at {image_path}")
        return False
    try:
        img_reader = ImageReader(image_path)
        img_width, img_height = img_reader.getSize()
        aspect = img_height / float(img_width)
        display_width = 3 * inch
        display_height = display_width * aspect

        c.drawImage(img_reader, inch, height - inch - display_height, width=display_width, height=display_height, mask='auto')
        c.save()
        print(f"Created image-only PDF: {pdf_path}")
        return True
    except Exception as e:
        print(f"Error creating PDF with reportlab: {e}")
        return False
    finally:
        # Clean up the temporary image file immediately after use
        try:
            os.remove(image_path)
            print(f"Removed temporary image: {image_path}")
        except OSError as e:
            print(f"Error removing temporary image {image_path}: {e}")


def create_pdf_from_text(pdf_path, text_content):
    """Creates a PDF containing the specified text content."""
    try:
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        textobject = c.beginText(inch, 10 * inch) # Start near top-left
        textobject.setFont("Helvetica", 10)
        for line in text_content.splitlines():
            textobject.textLine(line)
        c.drawText(textobject)
        c.save()
        print(f"Created text-based PDF: {pdf_path}")
        return True
    except Exception as e:
        print(f"Error creating text PDF with reportlab: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create mock PDF files for testing.")
    parser.add_argument("--type", choices=['image', 'text'], required=True, help="Type of PDF to create ('image' or 'text').")
    parser.add_argument("--output", required=True, help="Output PDF filename (e.g., 'image_only_mock.pdf').")
    parser.add_argument("--input_text_file", help="Path to the input text file (required for type 'text').")

    args = parser.parse_args()

    output_pdf_path = DEFAULT_FIXTURE_DIR / args.output

    # Ensure fixture directory exists
    DEFAULT_FIXTURE_DIR.mkdir(parents=True, exist_ok=True)

    if args.type == 'image':
        # Create a temporary blank image
        create_placeholder_image(DEFAULT_IMAGE_PATH)
        # Create the PDF with the image
        create_pdf_from_image(output_pdf_path, DEFAULT_IMAGE_PATH) # Cleans up image inside

    elif args.type == 'text':
        if not args.input_text_file:
            print("Error: --input_text_file is required for type 'text'.")
            exit(1)

        input_text_path = Path(args.input_text_file)
        if not input_text_path.is_file():
             print(f"Error: Input text file not found: {input_text_path}")
             exit(1)

        try:
            with open(input_text_path, 'r', encoding='utf-8') as f:
                text_content = f.read()
            create_pdf_from_text(output_pdf_path, text_content)
        except Exception as e:
            print(f"Error reading input text file or creating PDF: {e}")
            exit(1)