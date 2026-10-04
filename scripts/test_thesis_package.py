"""下载包交付边界：闭包、无本机材料、内容完整性及可重复构建。"""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch

import build_thesis_package as builder


class ThesisPackageTests(unittest.TestCase):
    def test_package_is_reproducible_and_contains_only_portable_sources(self):
        first, receipt = builder.package_bytes()
        second, _ = builder.package_bytes()
        self.assertEqual(first, second)
        self.assertEqual(receipt['sha256'], hashlib.sha256(first).hexdigest())
        with zipfile.ZipFile(io.BytesIO(first)) as archive:
            prefix = 'SZTU-Thesis-2026/'
            names = [name.removeprefix(prefix) for name in archive.namelist()]
            self.assertIn('AGENTS.md', names)
            self.assertIn('scripts/build_thesis.py', names)
            self.assertIn('templates/common/python/font_files.py', names)
            for name in names:
                self.assertNotIn(Path(name).suffix, ('.ttf', '.otf', '.ttc', '.aux', '.bbl', '.log'))
                self.assertNotIn('private', name)
                self.assertNotIn('sztu-fonts.local', name)
            manifest = json.loads(archive.read(prefix + 'template-manifest.json'))
            for name, digest in manifest['files'].items():
                content = archive.read(prefix + name)
                self.assertEqual(hashlib.sha256(content).hexdigest(), digest)
                if Path(name).suffix in ('.tex', '.py', '.md', '.json', '.cls'):
                    self.assertNotIn(b'/Users/chen/', content)
            body = archive.read(prefix + 'content/content.tex').decode()
            self.assertIn('此处说明研究对象', body)
            self.assertNotIn('爱你们', body)
            cls = archive.read(prefix + 'SZTUthesis.cls').decode()
            self.assertNotIn('{STXingkai.ttf}', cls)
            self.assertNotIn('{STXinwei.ttf}', cls)

    def test_missing_declared_dependency_fails_before_output(self):
        original = builder.source_bytes
        def missing(root, name):
            if name.endswith('content/abstracten.tex'):
                raise ValueError('包内依赖缺失')
            return original(root, name)
        with patch.object(builder, 'source_bytes', side_effect=missing):
            with self.assertRaisesRegex(ValueError, '依赖缺失'):
                builder.package_bytes()

    def test_unlisted_tex_input_is_rejected(self):
        original = builder.source_bytes
        def changed(root, name):
            data = original(root, name)
            return data + b'\n\\input{not-packaged}\n' if name == 'sztuthesis_main.tex' else data
        with patch.object(builder, 'source_bytes', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'not-packaged'):
                builder.package_bytes()

    def test_symlinks_and_traversal_are_rejected(self):
        for name in ('../secret', '/etc/passwd', 'a/../secret', 'a\\secret'):
            with self.assertRaises(ValueError):
                builder.safe_name(name)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'original').write_text('data')
            (root / 'linked').symlink_to(root / 'original')
            with self.assertRaisesRegex(ValueError, '符号链接'):
                builder.source_bytes(root, 'linked')


if __name__ == '__main__':
    unittest.main()
