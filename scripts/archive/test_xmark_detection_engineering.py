#!/usr/bin/env python3
"""
X-Mark and Strikethrough Detection Engineering
Systematic testing of OpenCV methods for philosophy PDF annotation detection
"""

import cv2
import numpy as np
import fitz  # PyMuPDF
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, asdict
import math


@dataclass
class GroundTruthInstance:
    """Ground truth for known X-marks and strikethroughs"""
    pdf_file: str
    page_index: int  # 0-indexed
    text: str
    corruption: str
    bbox: Tuple[float, float, float, float] = None  # (x0, y0, x1, y1)
    type: str = "unknown"  # "xmark", "strikethrough", or "underline"


@dataclass
class DetectedLine:
    """Detected line with metadata"""
    x1: float
    y1: float
    x2: float
    y2: float
    angle: float
    length: float
    method: str
    confidence: float = 1.0

    @property
    def x_center(self):
        return (self.x1 + self.x2) / 2

    @property
    def y_center(self):
        return (self.y1 + self.y2) / 2


@dataclass
class DetectionResult:
    """Results from a detection method"""
    method_name: str
    preprocessing: str
    parameters: Dict[str, Any]
    detected_lines: List[DetectedLine]
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float
    processing_time: float


class XMarkDetectionEngineer:
    """Systematic engineering of X-mark detection"""

    def __init__(self, output_dir: str = "test_output/xmark_engineering"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results = []

        # Ground truth instances
        self.ground_truth = self._define_ground_truth()

    def _define_ground_truth(self) -> List[GroundTruthInstance]:
        """Define known X-marks and strikethroughs for validation"""
        return [
            # Heidegger
            GroundTruthInstance(
                pdf_file="test_files/heidegger_pages_79-88.pdf",
                page_index=1,  # Original p.80
                text="Being",
                corruption="^B©»^",
                type="xmark"
            ),
            GroundTruthInstance(
                pdf_file="test_files/heidegger_pages_79-88.pdf",
                page_index=0,  # Original p.79
                text="Sein",
                corruption="Sfcfös",
                type="xmark"
            ),
            # Derrida
            GroundTruthInstance(
                pdf_file="test_files/derrida_pages_110_135.pdf",
                page_index=1,  # Original p.135
                text="is",
                corruption=")(",
                type="strikethrough"
            ),
            # Margins
            GroundTruthInstance(
                pdf_file="test_files/margins_test_pages.pdf",
                page_index=0,  # Original p.19
                text="is",
                corruption=")",  # Part of strikethrough
                type="strikethrough"
            ),
            GroundTruthInstance(
                pdf_file="test_files/margins_test_pages.pdf",
                page_index=1,  # Original p.33
                text="underlines",
                corruption="",  # Should NOT detect
                type="underline"
            )
        ]

    def find_ground_truth_bboxes(self):
        """Locate ground truth instances in PDFs using OCR corruption patterns"""
        print("=" * 80)
        print("LOCATING GROUND TRUTH INSTANCES")
        print("=" * 80)

        for gt in self.ground_truth:
            print(f"\n📍 Searching: {gt.pdf_file} page {gt.page_index + 1}")
            print(f"   Text: '{gt.text}' | Corruption: '{gt.corruption}'")

            try:
                doc = fitz.open(gt.pdf_file)
                page = doc[gt.page_index]

                # Get all text with bboxes
                blocks = page.get_text("dict")["blocks"]

                found = False
                for block in blocks:
                    if "lines" not in block:
                        continue
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"]
                            bbox = span["bbox"]

                            # Look for corruption pattern or original text
                            if gt.corruption and gt.corruption in text:
                                gt.bbox = tuple(bbox)
                                print(f"   ✅ Found corruption '{gt.corruption}' at bbox: {bbox}")
                                found = True
                                break
                            elif gt.text in text and not gt.corruption:
                                # For underlines (no corruption)
                                gt.bbox = tuple(bbox)
                                print(f"   ✅ Found text '{gt.text}' at bbox: {bbox}")
                                found = True
                                break
                        if found:
                            break
                    if found:
                        break

                if not found:
                    print(f"   ⚠️  Could not locate ground truth instance")
                    # Search entire page text for debugging
                    full_text = page.get_text()
                    if gt.corruption in full_text:
                        print(f"   ℹ️  Corruption '{gt.corruption}' exists in page text")
                    else:
                        print(f"   ℹ️  Corruption not found in page text")

                doc.close()

            except Exception as e:
                print(f"   ❌ Error: {e}")

    def render_page_to_image(self, pdf_path: str, page_index: int, dpi: int = 300) -> np.ndarray:
        """Render PDF page to OpenCV image"""
        doc = fitz.open(pdf_path)
        page = doc[page_index]

        # Render at specified DPI
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)

        # Convert to numpy array
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)

        # Convert RGBA to BGR if needed
        if pix.n == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        elif pix.n == 1:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        doc.close()
        return img

    # =========================================================================
    # PREPROCESSING METHODS
    # =========================================================================

    def preprocess_method_a_clahe(self, img: np.ndarray) -> np.ndarray:
        """Method A: Adaptive thresholding + CLAHE"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        binary = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, blockSize=11, C=2
        )
        return binary

    def preprocess_method_b_bilateral(self, img: np.ndarray) -> np.ndarray:
        """Method B: Bilateral filter + Otsu"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        bilateral = cv2.bilateralFilter(gray, 9, 75, 75)
        _, binary = cv2.threshold(bilateral, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        return binary

    def preprocess_method_c_morphological(self, img: np.ndarray) -> np.ndarray:
        """Method C: Morphological gradient"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        morph_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        gradient = cv2.morphologyEx(gray, cv2.MORPH_GRADIENT, morph_kernel)
        _, binary = cv2.threshold(gradient, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary

    def save_preprocessing_comparison(self, img: np.ndarray, pdf_name: str, page_idx: int):
        """Save comparison of preprocessing methods"""
        methods = {
            "A_CLAHE": self.preprocess_method_a_clahe,
            "B_Bilateral": self.preprocess_method_b_bilateral,
            "C_Morphological": self.preprocess_method_c_morphological
        }

        for name, method in methods.items():
            processed = method(img)
            output_path = self.output_dir / f"{pdf_name}_p{page_idx + 1}_{name}.png"
            cv2.imwrite(str(output_path), processed)
            print(f"   💾 Saved: {output_path.name}")

    # =========================================================================
    # DETECTION METHODS
    # =========================================================================

    def detect_hough_standard(self, binary: np.ndarray, threshold: int = 100) -> List[DetectedLine]:
        """Standard Hough Transform"""
        edges = cv2.Canny(binary, 50, 150, apertureSize=3)
        lines = cv2.HoughLines(edges, rho=1, theta=np.pi/180, threshold=threshold)

        detected = []
        if lines is not None:
            for line in lines:
                rho, theta = line[0]
                a = np.cos(theta)
                b = np.sin(theta)
                x0 = a * rho
                y0 = b * rho
                x1 = int(x0 + 1000 * (-b))
                y1 = int(y0 + 1000 * (a))
                x2 = int(x0 - 1000 * (-b))
                y2 = int(y0 - 1000 * (a))

                angle = math.degrees(theta)
                length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

                detected.append(DetectedLine(
                    x1=x1, y1=y1, x2=x2, y2=y2,
                    angle=angle, length=length,
                    method="hough_standard"
                ))

        return detected

    def detect_hough_probabilistic(self, binary: np.ndarray, threshold: int = 50,
                                   min_line_length: int = 30, max_line_gap: int = 5) -> List[DetectedLine]:
        """Probabilistic Hough Transform"""
        edges = cv2.Canny(binary, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, rho=1, theta=np.pi/180,
                                threshold=threshold,
                                minLineLength=min_line_length,
                                maxLineGap=max_line_gap)

        detected = []
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]

                angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
                length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

                detected.append(DetectedLine(
                    x1=x1, y1=y1, x2=x2, y2=y2,
                    angle=angle, length=length,
                    method="hough_probabilistic"
                ))

        return detected

    def detect_lsd(self, gray: np.ndarray) -> List[DetectedLine]:
        """Line Segment Detector"""
        lsd = cv2.createLineSegmentDetector(0)
        lines = lsd.detect(gray)[0]

        detected = []
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]

                angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
                length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

                detected.append(DetectedLine(
                    x1=x1, y1=y1, x2=x2, y2=y2,
                    angle=angle, length=length,
                    method="lsd"
                ))

        return detected

    def detect_morphological_lines(self, binary: np.ndarray, kernel_width: int = 40) -> List[DetectedLine]:
        """Morphological line detection"""
        # Horizontal lines
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_width, 1))
        h_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel)

        # Find contours in horizontal lines
        contours, _ = cv2.findContours(h_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        detected = []
        for contour in contours:
            # Get bounding rect
            x, y, w, h = cv2.boundingRect(contour)

            if w > 10:  # Minimum width
                x1, y1 = x, y + h//2
                x2, y2 = x + w, y + h//2

                detected.append(DetectedLine(
                    x1=x1, y1=y1, x2=x2, y2=y2,
                    angle=0, length=w,
                    method="morphological"
                ))

        return detected

    # =========================================================================
    # FILTERING STRATEGIES
    # =========================================================================

    def filter_by_angle(self, lines: List[DetectedLine],
                       min_angle: float = -10, max_angle: float = 10) -> List[DetectedLine]:
        """Filter lines by angle (for horizontal strikethroughs)"""
        filtered = []
        for line in lines:
            # Normalize angle to -180 to 180
            angle = line.angle % 360
            if angle > 180:
                angle -= 360

            # Check if horizontal (near 0°) or near 180°
            if (min_angle <= angle <= max_angle) or (180 + min_angle <= angle <= 180 + max_angle):
                filtered.append(line)

        return filtered

    def filter_by_position(self, lines: List[DetectedLine],
                          text_bboxes: List[Tuple[float, float, float, float]],
                          tolerance_factor: float = 0.2) -> List[DetectedLine]:
        """Filter lines that go through text (not above/below)"""
        filtered = []

        for line in lines:
            line_y = line.y_center

            for bbox in text_bboxes:
                x0, y0, x1, y1 = bbox
                text_middle = (y0 + y1) / 2
                text_height = y1 - y0
                tolerance = text_height * tolerance_factor

                # Check if line is near text middle
                if abs(line_y - text_middle) < tolerance:
                    # Also check horizontal overlap
                    if not (line.x2 < x0 or line.x1 > x1):
                        filtered.append(line)
                        break

        return filtered

    def filter_page_borders(self, lines: List[DetectedLine],
                           page_width: int, page_height: int,
                           border_margin: int = 20) -> List[DetectedLine]:
        """Remove lines at page borders"""
        filtered = []

        for line in lines:
            # Check if line is near any edge
            if (line.x1 < border_margin or line.x2 < border_margin or
                line.x1 > page_width - border_margin or line.x2 > page_width - border_margin or
                line.y1 < border_margin or line.y2 < border_margin or
                line.y1 > page_height - border_margin or line.y2 > page_height - border_margin):
                continue

            filtered.append(line)

        return filtered

    def detect_table_regions(self, lines: List[DetectedLine],
                           parallel_threshold: int = 3) -> List[Tuple[float, float, float, float]]:
        """Detect table regions (many parallel horizontal lines)"""
        # Group lines by Y coordinate (within tolerance)
        y_groups = {}
        tolerance = 5

        for line in lines:
            y = round(line.y_center / tolerance) * tolerance
            if y not in y_groups:
                y_groups[y] = []
            y_groups[y].append(line)

        # Find regions with many parallel lines
        table_regions = []
        for y, group in y_groups.items():
            if len(group) >= parallel_threshold:
                # Get bounding box of this table region
                xs = [l.x1 for l in group] + [l.x2 for l in group]
                ys = [l.y1 for l in group] + [l.y2 for l in group]
                table_regions.append((min(xs), min(ys), max(xs), max(ys)))

        return table_regions

    def filter_table_lines(self, lines: List[DetectedLine],
                          table_regions: List[Tuple[float, float, float, float]]) -> List[DetectedLine]:
        """Remove lines inside table regions"""
        filtered = []

        for line in lines:
            in_table = False
            for x0, y0, x1, y1 in table_regions:
                if (x0 <= line.x_center <= x1 and y0 <= line.y_center <= y1):
                    in_table = True
                    break

            if not in_table:
                filtered.append(line)

        return filtered

    # =========================================================================
    # VALIDATION
    # =========================================================================

    def lines_overlap(self, line: DetectedLine, bbox: Tuple[float, float, float, float],
                     tolerance: float = 20) -> bool:
        """Check if detected line overlaps with ground truth bbox"""
        x0, y0, x1, y1 = bbox

        # Check if line center is near bbox
        if (x0 - tolerance <= line.x_center <= x1 + tolerance and
            y0 - tolerance <= line.y_center <= y1 + tolerance):
            return True

        return False

    def validate_against_ground_truth(self, detected_lines: List[DetectedLine],
                                     pdf_file: str, page_index: int) -> Tuple[int, int, int]:
        """
        Validate detected lines against ground truth
        Returns: (true_positives, false_positives, false_negatives)
        """
        # Get ground truth for this page
        gt_instances = [gt for gt in self.ground_truth
                       if gt.pdf_file == pdf_file and gt.page_index == page_index]

        # Skip underlines (should NOT detect)
        gt_instances = [gt for gt in gt_instances if gt.type != "underline"]

        if not gt_instances:
            return 0, len(detected_lines), 0

        # Find matches
        matched_gt = set()
        true_positives = 0

        for line in detected_lines:
            for i, gt in enumerate(gt_instances):
                if gt.bbox and i not in matched_gt:
                    if self.lines_overlap(line, gt.bbox):
                        true_positives += 1
                        matched_gt.add(i)
                        break

        false_positives = len(detected_lines) - true_positives
        false_negatives = len(gt_instances) - len(matched_gt)

        return true_positives, false_positives, false_negatives

    def visualize_detections(self, img: np.ndarray, lines: List[DetectedLine],
                            ground_truth_bboxes: List[Tuple[float, float, float, float]],
                            output_path: str):
        """Save visualization of detected lines vs ground truth"""
        vis = img.copy()

        # Draw ground truth in green
        for bbox in ground_truth_bboxes:
            x0, y0, x1, y1 = [int(c) for c in bbox]
            cv2.rectangle(vis, (x0, y0), (x1, y1), (0, 255, 0), 2)

        # Draw detected lines in red
        for line in lines:
            cv2.line(vis, (int(line.x1), int(line.y1)),
                    (int(line.x2), int(line.y2)), (0, 0, 255), 2)

        cv2.imwrite(output_path, vis)

    # =========================================================================
    # SYSTEMATIC TESTING
    # =========================================================================

    def run_comprehensive_tests(self):
        """Run all tests systematically"""
        import time

        print("\n" + "=" * 80)
        print("COMPREHENSIVE X-MARK DETECTION ENGINEERING")
        print("=" * 80)

        # Step 1: Find ground truth locations
        self.find_ground_truth_bboxes()

        # Step 2: Test preprocessing methods
        print("\n" + "=" * 80)
        print("PREPROCESSING COMPARISON")
        print("=" * 80)

        for gt in self.ground_truth:
            pdf_name = Path(gt.pdf_file).stem
            print(f"\n📄 {pdf_name} - Page {gt.page_index + 1}")

            img = self.render_page_to_image(gt.pdf_file, gt.page_index, dpi=300)
            self.save_preprocessing_comparison(img, pdf_name, gt.page_index)

        # Step 3: Parameter tuning for each method
        print("\n" + "=" * 80)
        print("DETECTION METHOD COMPARISON WITH PARAMETER TUNING")
        print("=" * 80)

        # Test configurations
        test_configs = []

        # Hough Probabilistic - grid search
        for threshold in [30, 50, 100, 150]:
            for min_len in [20, 30, 40, 50]:
                for max_gap in [2, 5, 10]:
                    test_configs.append({
                        'method': 'hough_probabilistic',
                        'preprocessing': 'clahe',
                        'params': {
                            'threshold': threshold,
                            'min_line_length': min_len,
                            'max_line_gap': max_gap
                        }
                    })

        # LSD - different preprocessing
        for prep in ['clahe', 'bilateral', 'morphological']:
            test_configs.append({
                'method': 'lsd',
                'preprocessing': prep,
                'params': {}
            })

        # Morphological - different kernel widths
        for kernel_width in [20, 30, 40, 50, 60]:
            test_configs.append({
                'method': 'morphological',
                'preprocessing': 'clahe',
                'params': {'kernel_width': kernel_width}
            })

        print(f"Testing {len(test_configs)} configurations...")

        best_results = []

        for config in test_configs[:20]:  # Limit to first 20 for now
            method_name = config['method']
            prep_name = config['preprocessing']
            params = config['params']

            print(f"\n🔧 Testing: {method_name} + {prep_name} {params}")

            all_tp, all_fp, all_fn = 0, 0, 0
            total_time = 0

            for gt in self.ground_truth[:3]:  # Test on first 3 ground truth instances
                img = self.render_page_to_image(gt.pdf_file, gt.page_index, dpi=300)

                # Preprocess
                if prep_name == 'clahe':
                    processed = self.preprocess_method_a_clahe(img)
                elif prep_name == 'bilateral':
                    processed = self.preprocess_method_b_bilateral(img)
                else:
                    processed = self.preprocess_method_c_morphological(img)

                # Detect
                start_time = time.time()

                if method_name == 'hough_probabilistic':
                    lines = self.detect_hough_probabilistic(processed, **params)
                elif method_name == 'lsd':
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    lines = self.detect_lsd(gray)
                elif method_name == 'morphological':
                    lines = self.detect_morphological_lines(processed, **params)
                else:
                    lines = []

                elapsed = time.time() - start_time
                total_time += elapsed

                # Filter
                lines = self.filter_by_angle(lines)
                lines = self.filter_page_borders(lines, img.shape[1], img.shape[0])

                # Validate
                tp, fp, fn = self.validate_against_ground_truth(lines, gt.pdf_file, gt.page_index)
                all_tp += tp
                all_fp += fp
                all_fn += fn

            # Calculate metrics
            precision = all_tp / (all_tp + all_fp) if (all_tp + all_fp) > 0 else 0
            recall = all_tp / (all_tp + all_fn) if (all_tp + all_fn) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

            result = {
                'method': method_name,
                'preprocessing': prep_name,
                'params': params,
                'tp': all_tp,
                'fp': all_fp,
                'fn': all_fn,
                'precision': precision,
                'recall': recall,
                'f1': f1,
                'time': total_time
            }

            best_results.append(result)

            print(f"   TP: {all_tp}, FP: {all_fp}, FN: {all_fn}")
            print(f"   Precision: {precision:.2f}, Recall: {recall:.2f}, F1: {f1:.2f}")
            print(f"   Time: {total_time:.3f}s")

        # Save results
        results_file = self.output_dir / "engineering_results.json"
        with open(results_file, 'w') as f:
            json.dump(best_results, f, indent=2)

        print(f"\n💾 Results saved to: {results_file}")

        # Find best configuration
        if best_results:
            best = max(best_results, key=lambda x: x['f1'])
            print("\n" + "=" * 80)
            print("BEST CONFIGURATION")
            print("=" * 80)
            print(f"Method: {best['method']}")
            print(f"Preprocessing: {best['preprocessing']}")
            print(f"Parameters: {best['params']}")
            print(f"F1 Score: {best['f1']:.2f}")
            print(f"Precision: {best['precision']:.2f}")
            print(f"Recall: {best['recall']:.2f}")

        return best_results


def main():
    engineer = XMarkDetectionEngineer()
    results = engineer.run_comprehensive_tests()

    print("\n✅ Engineering tests complete!")
    print(f"📊 Tested {len(results)} configurations")
    print(f"📁 Output directory: {engineer.output_dir}")


if __name__ == "__main__":
    main()
