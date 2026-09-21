#!/usr/bin/env python3
"""Font setup failure, persistence, and directory precedence regressions."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import check_fonts as checker
from common.python import font_files


class FontSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='font UX ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fontdir = self.root / 'my fonts'
        self.fontdir.mkdir()
        self.fonts = {}
        definitions = checker.load_font_policy()['font_files']
        for key in checker.FONTS:
            path = self.fontdir / definitions[key]['candidates'][0]
            path.touch()
            self.fonts[key] = path
        for target, value in [('ROOT', self.root)]:
            p = patch.object(checker, target, value); p.start(); self.addCleanup(p.stop)
        p = patch.dict(os.environ, {}, clear=True); p.start(); self.addCleanup(p.stop)

    def check(self, directory=None, save=True):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return checker.check(directory, save=save)

    def test_missing_preserves_pdf_and_configuration(self):
        pdf = self.root / 'old.pdf'; pdf.write_bytes(b'old PDF')
        config = self.root / 'sztu-fonts.local.tex'; config.write_text('old config')
        with patch.object(checker, 'discover_font_files', return_value=({}, ['KaiTi (Kaiti.ttf)'])):
            self.assertEqual(self.check(), 1)
        self.assertEqual(pdf.read_bytes(), b'old PDF')
        self.assertEqual(config.read_text(), 'old config')

    def test_success_remembers_directory_and_engine_receives_spaces(self):
        def probe(command, **kwargs):
            source = (kwargs['cwd'] / 'fonts.tex').read_text()
            self.assertIn('Path={' + self.fontdir.as_posix() + '/', source)
            self.assertIn('-no-shell-escape', command)
            return subprocess.CompletedProcess(command, 0, 'ok')
        with patch.object(checker, 'discover_font_files', return_value=(self.fonts, [])) as discovery, patch.object(checker.shutil, 'which', return_value='/bin/xelatex'), patch.object(checker.subprocess, 'run', side_effect=probe):
            self.assertEqual(self.check(self.fontdir), 0)
            self.assertEqual(self.check(), 0)
            self.assertEqual(discovery.call_args.kwargs['local_font_dir'], self.fontdir)
        config = (self.root / 'sztu-fonts.local.tex').read_text()
        self.assertIn('\\sztu@configuredtrue', config)
        self.assertIn(str(self.fontdir), config)

    def test_unchanged_config_preserves_timestamp(self):
        path = self.root / 'config.tex'
        checker.write_if_changed(path, 'same')
        before = path.stat().st_mtime_ns
        checker.write_if_changed(path, 'same')
        self.assertEqual(path.stat().st_mtime_ns, before)

    def test_no_save_leaves_no_configuration(self):
        with patch.object(checker, 'discover_font_files', return_value=(self.fonts, [])), patch.object(checker.shutil, 'which', return_value='/bin/xelatex'), patch.object(checker.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'ok')):
            self.assertEqual(self.check(self.fontdir, save=False), 0)
        self.assertFalse((self.root / 'sztu-fonts.local.tex').exists())
        self.assertFalse((self.root / 'sztu-fonts.local.json').exists())

    def test_moved_saved_directory_retries_automatic_discovery(self):
        (self.root / 'sztu-fonts.local.json').write_text(json.dumps({'font_dir': str(self.root / 'moved')}))
        with patch.object(checker, 'discover_font_files', return_value=(self.fonts, [])) as discovery, patch.object(checker.shutil, 'which', return_value='/bin/xelatex'), patch.object(checker.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'ok')):
            self.assertEqual(self.check(), 0)
            self.assertIsNone(discovery.call_args.kwargs['local_font_dir'])

    def test_invalid_directory(self):
        self.assertEqual(self.check(self.root / 'gone'), 2)

    def test_load_failure_does_not_save(self):
        with patch.object(checker, 'discover_font_files', return_value=(self.fonts, [])), patch.object(checker.shutil, 'which', return_value='/bin/xelatex'), patch.object(checker.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, 'bad font')):
            self.assertEqual(self.check(self.fontdir), 1)
        self.assertFalse((self.root / 'sztu-fonts.local.tex').exists())
        self.assertEqual((self.root / 'tmp/font-check/latest.log').read_text(), 'bad font')

    def test_directory_priority_beats_candidate_filename_priority(self):
        system = self.root / 'system'; system.mkdir()
        (system / 'simsun.ttf').touch()
        explicit = self.root / 'explicit'; explicit.mkdir()
        chosen = explicit / 'simsun.ttc'; chosen.touch()
        with patch.object(font_files, 'font_roots', return_value=[explicit, system]):
            found, missing = font_files.discover_font_files(['SimSun'])
        self.assertEqual(found['SimSun'], chosen.resolve())
        self.assertFalse(missing)

    def test_build_clean_checks_before_touching_previous_files(self):
        import shutil
        shutil.copy(Path(__file__).resolve().parents[1] / 'build.sh', self.root)
        (self.root / 'scripts').mkdir()
        (self.root / 'scripts/check_fonts.py').write_text('raise SystemExit(1)\n')
        for name in ('sztuthesis_main.pdf', 'sztuthesis_main.aux'):
            (self.root / name).write_text('keep')
        result = subprocess.run(['/bin/bash', 'build.sh', '--clean'], cwd=self.root, env={'PATH': '/usr/bin:/bin'}, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        for name in ('sztuthesis_main.pdf', 'sztuthesis_main.aux'):
            self.assertEqual((self.root / name).read_text(), 'keep')

if __name__ == '__main__':
    unittest.main()
