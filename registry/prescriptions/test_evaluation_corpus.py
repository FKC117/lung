from types import SimpleNamespace
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

from prescriptions.evaluation.corpus import cases
from prescriptions.services.processing import extract_pages


class SyntheticCorpusTests(SimpleTestCase):
    def test_annotations_have_unique_ids_quotes_and_synthetic_sources(self):
        corpus = cases()
        self.assertEqual(len({case["id"] for case in corpus}), len(corpus))
        def leaves(value):
            if isinstance(value, dict):
                if "value" in value and "source_text" in value:
                    yield value
                else:
                    for entry in value.values():
                        yield from leaves(entry)
            elif isinstance(value, list):
                for entry in value:
                    yield from leaves(entry)
        for case in corpus:
            self.assertTrue(all("SYNTHETIC FIXTURE ONLY" in page for page in case["pages"]))
            for value in leaves(case["payload"]):
                self.assertTrue(1 <= value["page"] <= len(case["pages"]))
                if case["id"] != "invented-source-quote":
                    self.assertIn(value["source_text"], case["pages"][value["page"] - 1])
            self.assertIsInstance(case["expected"], dict)
            self.assertIsInstance(case["exceptions"], list)

    def test_text_pdf_uses_embedded_text_and_scan_uses_ocr_boundary(self):
        import fitz
        from PIL import Image, ImageDraw
        with TemporaryDirectory() as directory:
            root = Path(directory)
            pdf_path = root / "synthetic.pdf"
            pdf = fitz.open()
            pdf.new_page().insert_text((40, 60), cases()[0]["pages"][0], fontsize=12)
            pdf.save(pdf_path)
            pdf.close()
            with patch("prescriptions.services.processing.ocr_image") as ocr:
                extracted = extract_pages(SimpleNamespace(file=SimpleNamespace(name=pdf_path.name, path=str(pdf_path))))
                ocr.assert_not_called()
            self.assertIn("Small cell carcinoma", extracted[0][1])
            image_path = root / "synthetic.png"
            image = Image.new("RGB", (1000, 400), "white")
            ImageDraw.Draw(image).text((20, 20), cases()[1]["pages"][0], fill="black", font_size=22)
            image.save(image_path)
            with patch("prescriptions.services.processing.ocr_image", return_value=(cases()[1]["pages"][0], 80, {"method": "synthetic-ocr"})) as ocr:
                extracted = extract_pages(SimpleNamespace(file=SimpleNamespace(name=image_path.name, open=lambda mode: image_path.open(mode))))
                ocr.assert_called_once()
            self.assertEqual(extracted[0][1], cases()[1]["pages"][0])
