import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
import zipfile


SPEC = importlib.util.spec_from_file_location(
    "distribution_verifier", Path(__file__).resolve().parents[1] / "scripts" / "verify_distribution_artifacts.py"
)
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


class DistributionArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.content = {
            "erpnextswiss/__init__.py": b"__version__='1.0'\n",
            "erpnextswiss/public/xsd/camt.053.001.08.xsd": b"<schema/>",
            "erpnextswiss/public/fonts/test.woff": b"synthetic font fixture",
            "erpnextswiss/public/reader.wasm": b"\x00asm synthetic fixture",
        }
        for name, data in self.content.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

    def artifacts(self, wheel_content=None, sdist_content=None):
        wheel = self.root / "test.whl"
        sdist = self.root / "test.tar.gz"
        with zipfile.ZipFile(wheel, "w") as archive:
            for name, data in (self.content if wheel_content is None else wheel_content).items():
                archive.writestr(name, data)
        with tarfile.open(sdist, "w:gz") as archive:
            for name, data in (self.content if sdist_content is None else sdist_content).items():
                member = tarfile.TarInfo("erpnextswiss-1.0/" + name)
                member.size = len(data)
                archive.addfile(member, io.BytesIO(data))
        return wheel, sdist

    def test_complete_byte_identical_app_is_accepted(self):
        wheel, sdist = self.artifacts()
        self.assertEqual(verifier.verify(self.root, wheel, sdist), 4)

    def test_missing_or_changed_resource_in_either_archive_fails(self):
        for artifact in ("wheel", "sdist"):
            for fault in ("missing", "changed"):
                content = self.content.copy()
                target = "erpnextswiss/public/xsd/camt.053.001.08.xsd"
                if fault == "missing":
                    del content[target]
                else:
                    content[target] = b"different"
                wheel, sdist = self.artifacts(**{artifact + "_content": content})
                with self.assertRaisesRegex(AssertionError, artifact + ": missing="):
                    verifier.verify(self.root, wheel, sdist)

    def test_gateway_cannot_enter_python_artifacts(self):
        content = {**self.content, "gateway/ebics/src/Test.php": b"<?php"}
        wheel, sdist = self.artifacts(wheel_content=content)
        with self.assertRaisesRegex(AssertionError, "Unintended top-level"):
            verifier.verify(self.root, wheel, sdist)
        wheel, sdist = self.artifacts(sdist_content=content)
        with self.assertRaisesRegex(AssertionError, "Gateway must be built separately"):
            verifier.verify(self.root, wheel, sdist)

    def test_new_format_requires_manifest_review(self):
        (self.root / "erpnextswiss" / "new.format").write_bytes(b"new data")
        wheel, sdist = self.artifacts()
        with self.assertRaisesRegex(AssertionError, "explicit packaging decision"):
            verifier.verify(self.root, wheel, sdist)

    def test_baseline_content_cannot_disappear(self):
        baseline = self.root / "baseline.whl"
        with zipfile.ZipFile(baseline, "w") as archive:
            archive.writestr("erpnextswiss/legacy.txt", b"keep this")
        wheel, sdist = self.artifacts()
        with self.assertRaisesRegex(AssertionError, "Existing packaged app content"):
            verifier.verify(self.root, wheel, sdist, baseline)


if __name__ == "__main__":
    unittest.main()
