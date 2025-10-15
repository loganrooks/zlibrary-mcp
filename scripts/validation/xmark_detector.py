#!/usr/bin/env python3
"""
X-Mark Detection V2 - Focused on Diagonal Line Pairs
Key insight: X-marks are TWO diagonal lines crossing, not horizontal strikethroughs
"""

import cv2
import numpy as np
import fitz  # PyMuPDF
import json
from pathlib import Path
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass, asdict
import math


@dataclass
class DetectedLine:
    """Detected line with metadata"""
    x1: float
    y1: float
    x2: float
    y2: float
    angle: float
    length: float

    @property
    def x_center(self):
        return (self.x1 + self.x2) / 2

    @property
    def y_center(self):
        return (self.y1 + self.y2) / 2


@dataclass
class XMarkCandidate:
    """Potential X-mark from crossing diagonal lines"""
    line1: DetectedLine
    line2: DetectedLine
    center_x: float
    center_y: float
    confidence: float
    bbox: Tuple[float, float, float, float]


class XMarkDetectorV2:
    """Detect X-marks by finding crossing diagonal line pairs"""

    def __init__(self, output_dir: str = "test_output/xmark_v2"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Ground truth from previous analysis
        self.ground_truth = {
            'heidegger_p2': (91.68, 138.93, 379.99, 150.0),  # Being
            'heidegger_p1': (94.32, 141.88, 377.76, 154.06),  # Sein
            'derrida_p2': (312.21, 172.998, 326.38, 186.87),  # is
            'margins_p1': (36.0, 256.02, 238.63, 269.22),  # is
        }

    def render_page(self, pdf_path: str, page_idx: int, dpi: int = 300) -> np.ndarray:
        """Render PDF page to image"""
        doc = fitz.open(pdf_path)
        page = doc[page_idx]
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        doc.close()
        return img

    def detect_all_lines_lsd(self, img: np.ndarray) -> List[DetectedLine]:
        """Detect ALL lines using LSD (most accurate)"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
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
                    angle=angle, length=length
                ))

        return detected

    def filter_diagonal_lines(self, lines: List[DetectedLine],
                              angle_tolerance: float = 20) -> Tuple[List[DetectedLine], List[DetectedLine]]:
        """
        Separate diagonal lines into two groups:
        - Positive slope (45° ± tolerance): /
        - Negative slope (-45° ± tolerance): \
        """
        positive_diagonal = []  # / lines (around 45°)
        negative_diagonal = []  # \ lines (around -45° or 135°)

        for line in lines:
            # Normalize angle to -180 to 180
            angle = line.angle % 360
            if angle > 180:
                angle -= 360

            # Positive diagonal: 30° to 60° (45° ± 15°)
            if 30 <= angle <= 60:
                positive_diagonal.append(line)
            # Negative diagonal: -60° to -30° OR 120° to 150°
            elif (-60 <= angle <= -30) or (120 <= angle <= 150):
                negative_diagonal.append(line)

        return positive_diagonal, negative_diagonal

    def find_crossing_pairs(self, pos_lines: List[DetectedLine],
                           neg_lines: List[DetectedLine],
                           max_distance: float = 20) -> List[XMarkCandidate]:
        """
        Find pairs of diagonal lines that cross to form X-marks
        """
        candidates = []

        for pos in pos_lines:
            for neg in neg_lines:
                # Check if lines are close enough to be crossing
                center_dist = math.sqrt(
                    (pos.x_center - neg.x_center)**2 +
                    (pos.y_center - neg.y_center)**2
                )

                if center_dist < max_distance:
                    # Calculate crossing point
                    cross_x = (pos.x_center + neg.x_center) / 2
                    cross_y = (pos.y_center + neg.y_center) / 2

                    # Bounding box around the X
                    min_x = min(pos.x1, pos.x2, neg.x1, neg.x2)
                    max_x = max(pos.x1, pos.x2, neg.x1, neg.x2)
                    min_y = min(pos.y1, pos.y2, neg.y1, neg.y2)
                    max_y = max(pos.y1, pos.y2, neg.y1, neg.y2)

                    # Confidence based on:
                    # 1. How close the centers are (closer = better)
                    # 2. How similar the lengths are (more similar = better)
                    # 3. How perpendicular the angles are (closer to 90° = better)
                    center_score = 1 - (center_dist / max_distance)
                    length_ratio = min(pos.length, neg.length) / max(pos.length, neg.length)
                    angle_diff = abs(abs(pos.angle - neg.angle) - 90)
                    angle_score = 1 - (angle_diff / 45)  # Ideal is 90°, worst is 45° off

                    confidence = (center_score + length_ratio + angle_score) / 3

                    candidates.append(XMarkCandidate(
                        line1=pos,
                        line2=neg,
                        center_x=cross_x,
                        center_y=cross_y,
                        confidence=confidence,
                        bbox=(min_x, min_y, max_x, max_y)
                    ))

        # Sort by confidence
        candidates.sort(key=lambda x: x.confidence, reverse=True)
        return candidates

    def validate_against_ground_truth(self, candidates: List[XMarkCandidate],
                                     ground_truth_bbox: Tuple[float, float, float, float],
                                     dpi: int = 300) -> Tuple[bool, float]:
        """
        Check if any candidate overlaps with ground truth bbox
        Returns: (found, best_overlap_score)
        """
        # Scale ground truth bbox from 72 DPI to render DPI
        scale = dpi / 72
        gt_x0, gt_y0, gt_x1, gt_y1 = ground_truth_bbox
        gt_x0 *= scale
        gt_y0 *= scale
        gt_x1 *= scale
        gt_y1 *= scale

        best_overlap = 0
        found = False

        for candidate in candidates:
            cx, cy = candidate.center_x, candidate.center_y

            # Check if center is within ground truth bbox (with tolerance)
            tolerance = 30
            if (gt_x0 - tolerance <= cx <= gt_x1 + tolerance and
                gt_y0 - tolerance <= cy <= gt_y1 + tolerance):
                # Calculate overlap score
                x_overlap = min(candidate.bbox[2], gt_x1) - max(candidate.bbox[0], gt_x0)
                y_overlap = min(candidate.bbox[3], gt_y1) - max(candidate.bbox[1], gt_y0)

                if x_overlap > 0 and y_overlap > 0:
                    overlap_area = x_overlap * y_overlap
                    gt_area = (gt_x1 - gt_x0) * (gt_y1 - gt_y0)
                    overlap_score = overlap_area / gt_area

                    best_overlap = max(best_overlap, overlap_score)
                    found = True

        return found, best_overlap

    def visualize_detections(self, img: np.ndarray,
                            all_lines: List[DetectedLine],
                            pos_lines: List[DetectedLine],
                            neg_lines: List[DetectedLine],
                            candidates: List[XMarkCandidate],
                            ground_truth_bbox: Tuple[float, float, float, float],
                            output_prefix: str,
                            dpi: int = 300):
        """Save visualizations of detection steps"""

        # 1. All detected lines
        vis_all = img.copy()
        for line in all_lines:
            cv2.line(vis_all, (int(line.x1), int(line.y1)),
                    (int(line.x2), int(line.y2)), (128, 128, 128), 1)
        cv2.imwrite(str(self.output_dir / f"{output_prefix}_1_all_lines.png"), vis_all)

        # 2. Diagonal lines only
        vis_diag = img.copy()
        for line in pos_lines:
            cv2.line(vis_diag, (int(line.x1), int(line.y1)),
                    (int(line.x2), int(line.y2)), (0, 255, 0), 2)  # Green for /
        for line in neg_lines:
            cv2.line(vis_diag, (int(line.x1), int(line.y1)),
                    (int(line.x2), int(line.y2)), (0, 0, 255), 2)  # Red for \
        cv2.imwrite(str(self.output_dir / f"{output_prefix}_2_diagonal_lines.png"), vis_diag)

        # 3. X-mark candidates
        vis_candidates = img.copy()

        # Draw ground truth
        scale = dpi / 72
        gt_x0, gt_y0, gt_x1, gt_y1 = ground_truth_bbox
        cv2.rectangle(vis_candidates,
                     (int(gt_x0 * scale), int(gt_y0 * scale)),
                     (int(gt_x1 * scale), int(gt_y1 * scale)),
                     (255, 255, 0), 3)  # Yellow for ground truth

        # Draw top candidates
        for i, candidate in enumerate(candidates[:10]):  # Top 10
            # Draw both lines
            cv2.line(vis_candidates,
                    (int(candidate.line1.x1), int(candidate.line1.y1)),
                    (int(candidate.line1.x2), int(candidate.line1.y2)),
                    (0, 255, 0), 2)
            cv2.line(vis_candidates,
                    (int(candidate.line2.x1), int(candidate.line2.y1)),
                    (int(candidate.line2.x2), int(candidate.line2.y2)),
                    (0, 0, 255), 2)

            # Draw center point
            cv2.circle(vis_candidates,
                      (int(candidate.center_x), int(candidate.center_y)),
                      5, (255, 0, 255), -1)

            # Draw confidence score
            text = f"#{i+1}: {candidate.confidence:.2f}"
            cv2.putText(vis_candidates, text,
                       (int(candidate.center_x) + 10, int(candidate.center_y) - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

        cv2.imwrite(str(self.output_dir / f"{output_prefix}_3_xmark_candidates.png"), vis_candidates)

    def test_page(self, pdf_path: str, page_idx: int, gt_name: str):
        """Test X-mark detection on a single page"""
        print(f"\n{'='*80}")
        print(f"Testing: {pdf_path} - Page {page_idx + 1} ({gt_name})")
        print(f"{'='*80}")

        # Render page
        img = self.render_page(pdf_path, page_idx, dpi=300)
        print(f"Rendered: {img.shape[1]}x{img.shape[0]} @ 300 DPI")

        # Detect all lines
        all_lines = self.detect_all_lines_lsd(img)
        print(f"Detected {len(all_lines)} total lines (LSD)")

        # Filter diagonal lines
        pos_lines, neg_lines = self.filter_diagonal_lines(all_lines)
        print(f"Diagonal lines: {len(pos_lines)} positive (/), {len(neg_lines)} negative (\\)")

        # Find crossing pairs
        candidates = self.find_crossing_pairs(pos_lines, neg_lines, max_distance=30)
        print(f"Found {len(candidates)} X-mark candidates")

        if candidates:
            print(f"\nTop 5 candidates by confidence:")
            for i, c in enumerate(candidates[:5]):
                print(f"  #{i+1}: confidence={c.confidence:.3f}, "
                      f"center=({c.center_x:.0f}, {c.center_y:.0f})")

        # Validate against ground truth
        gt_bbox = self.ground_truth[gt_name]
        found, overlap = self.validate_against_ground_truth(candidates, gt_bbox, dpi=300)

        print(f"\n{'='*40}")
        if found:
            print(f"✅ DETECTED! Overlap score: {overlap:.3f}")
        else:
            print(f"❌ NOT DETECTED")
        print(f"{'='*40}")

        # Visualize
        output_prefix = f"{Path(pdf_path).stem}_p{page_idx + 1}_{gt_name}"
        self.visualize_detections(img, all_lines, pos_lines, neg_lines,
                                 candidates, gt_bbox, output_prefix, dpi=300)

        return found, overlap, len(candidates)

    def run_all_tests(self):
        """Run tests on all ground truth instances"""
        print("\n" + "="*80)
        print("X-MARK DETECTION V2 - DIAGONAL LINE PAIR DETECTION")
        print("="*80)

        test_cases = [
            ("test_files/heidegger_pages_79-88.pdf", 1, "heidegger_p2"),
            ("test_files/heidegger_pages_79-88.pdf", 0, "heidegger_p1"),
            ("test_files/derrida_pages_110_135.pdf", 1, "derrida_p2"),
            ("test_files/margins_test_pages.pdf", 0, "margins_p1"),
        ]

        results = []
        for pdf_path, page_idx, gt_name in test_cases:
            found, overlap, num_candidates = self.test_page(pdf_path, page_idx, gt_name)
            results.append({
                'pdf': pdf_path,
                'page': page_idx + 1,
                'gt_name': gt_name,
                'detected': found,
                'overlap_score': overlap,
                'num_candidates': num_candidates
            })

        # Summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)

        total = len(results)
        detected = sum(1 for r in results if r['detected'])
        recall = detected / total if total > 0 else 0

        print(f"\nDetection Rate: {detected}/{total} = {recall:.1%}")
        print(f"\nDetailed Results:")
        for r in results:
            status = "✅ DETECTED" if r['detected'] else "❌ MISSED"
            print(f"  {r['gt_name']:20s} {status:15s} "
                  f"overlap={r['overlap_score']:.3f}, "
                  f"candidates={r['num_candidates']}")

        # Save results
        results_file = self.output_dir / "detection_results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Results saved to: {results_file}")

        return results


def main():
    detector = XMarkDetectorV2()
    results = detector.run_all_tests()

    print("\n✅ X-mark detection tests complete!")
    print(f"📁 Output: {detector.output_dir}")


if __name__ == "__main__":
    main()
