#!/usr/bin/env python3
"""按显式清单生成学生论文源码 ZIP；不打包字体、机器配置或原有论文产物。"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = Path('templates/thesis/package/files.json')


def safe_name(value: str) -> str:
    path = PurePosixPath(value)
    if not value or '\\' in value or path.is_absolute() or any(p in ('..', '.') for p in value.split('/')):
        raise ValueError(f'不安全的包内路径：{value}')
    return value


def source_bytes(root: Path, name: str) -> bytes:
    safe_name(name)
    path = root / name
    if any(part.is_symlink() for part in (path, *path.parents) if part != root and root in part.parents):
        raise ValueError(f'源码不能通过符号链接打包：{name}')
    if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f'包内依赖缺失：{name}')
    return path.read_bytes()


def package_bytes(root: Path = ROOT) -> tuple[bytes, dict]:
    spec = json.loads(source_bytes(root, SPEC.as_posix()))
    prefix = safe_name(spec['root_directory'])
    files: dict[str, bytes] = {}
    for source, target in spec['files'].items():
        safe_name(target)
        if target in files or target == 'template-manifest.json':
            raise ValueError(f'重复包内路径：{target}')
        if Path(target).suffix.lower() in ('.ttf', '.otf', '.ttc') or 'sztu-fonts.local' in target:
            raise ValueError(f'禁止打包字体或本机配置：{target}')
        files[target] = source_bytes(root, source)
    # 主入口及各正文片段的字面量 input/include 都必须存在。只验证实际代码，不扫描注释。
    for name, data in files.items():
        if not name.endswith('.tex'):
            continue
        text = re.sub(r'(?m)(?<!\\)%.*$', '', data.decode('utf-8'))
        for dependency in re.findall(r'\\(?:input|include)\{([^}]+)\}', text):
            if '\\' in dependency:
                raise ValueError(f'包内输入引用必须是确定路径：{name}')
            candidate = dependency if dependency.endswith('.tex') else dependency + '.tex'
            if candidate not in files:
                raise ValueError(f'{name} 缺少依赖 {candidate}')
    revision = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], capture_output=True, text=True)
    manifest = {
        'schema_version': 1, 'version': spec['version'],
        'source_revision': revision.stdout.strip() if revision.returncode == 0 else None,
        # 逐文件哈希标识实际工作区内容；source_revision 不宣称未提交修改已属于该提交。
        'files': {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())},
    }
    files['template-manifest.json'] = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode()
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(f'{prefix}/{name}', date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    payload = output.getvalue()
    receipt = {'version': spec['version'], 'sha256': hashlib.sha256(payload).hexdigest(), 'sizeBytes': len(payload)}
    return payload, receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--overwrite', action='store_true', help='显式覆盖先前生成的 ZIP')
    args = parser.parse_args()
    payload, receipt = package_bytes()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('wb' if args.overwrite else 'xb') as output:
        output.write(payload)
    receipt['filename'] = args.output.name
    args.output.with_suffix('.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(receipt, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
