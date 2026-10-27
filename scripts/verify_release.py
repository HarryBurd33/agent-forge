#!/usr/bin/env python3
"""Verify Agent Forge's concrete source contracts without external dependencies."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote


def require(condition, message):
    if not condition:
        raise ValueError(message)


def safe_file(root, name):
    path = root / name
    require(not Path(name).is_absolute() and '..' not in Path(name).parts, 'unsafe manifest path')
    require(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(root.resolve()), 'missing or unsafe file: ' + name)
    return path


def check_manifest(root, manifest_path):
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    require(manifest.get('schema_version') == 1, 'unsupported manifest')
    for name, digest in manifest['files'].items():
        require(hashlib.sha256(safe_file(root, name).read_bytes()).hexdigest() == digest, 'manifest mismatch: ' + name)
    return len(manifest['files'])


def verify(root):
    skill = root / 'agent-forge'
    content = safe_file(skill, 'SKILL.md').read_text(encoding='utf-8')
    require(content.startswith('---\n'), 'missing skill frontmatter')
    front = content.split('---', 2)[1]
    require(re.search(r'^name: agent-forge$', front, re.M), 'wrong skill name')
    description = re.search(r'^description: (.+)$', front, re.M)
    require(description and 1 <= len(description.group(1)) <= 1024, 'invalid description')
    ui = safe_file(skill, 'agents/openai.yaml').read_text(encoding='utf-8')
    require('display_name: "Agent Forge"' in ui and '$agent-forge' in ui, 'wrong UI metadata')
    license_text = safe_file(root, 'LICENSE').read_text(encoding='utf-8')
    require(license_text == safe_file(skill, 'LICENSE').read_text(encoding='utf-8'), 'root and skill licenses differ')
    require('MIT License' in license_text and 'Permission is hereby granted, free of charge' in license_text, 'MIT license missing')
    links = 0
    for path in skill.rglob('*'):
        if not path.is_file() or '__pycache__' in path.parts or path.suffix == '.pyc':
            continue
        require(not path.is_symlink(), 'symlink in skill')
        data = path.read_text(encoding='utf-8')
        require(not re.search(r'/Users/[^/\s]+/(?:Documents|\.codex|\.agents)/', data), 'private machine path in export')
        if path.suffix == '.json':
            json.loads(data)
        if path.suffix == '.py':
            compile(data, str(path), 'exec')
        if path.suffix == '.md':
            for target in re.findall(r'\]\(([^\n)]+)\)', data):
                target = target.split(' ', 1)[0].strip('<>')
                if '://' in target or target.startswith('#'):
                    continue
                target = unquote(target.split('#', 1)[0])
                require((path.parent / target).exists(), 'broken link: ' + str(path) + ' → ' + target)
                links += 1
    files = check_manifest(skill, safe_file(skill, 'validation/MANIFEST.json'))
    public = root / 'release-manifest.json'
    exported = check_manifest(root, public) if public.exists() else None
    if public.exists():
        expected = set(json.loads(public.read_text())['files']) | {'release-manifest.json'}
        actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and '.git' not in p.relative_to(root).parts and '__pycache__' not in p.parts and p.suffix != '.pyc'}
        require(actual == expected, 'export inventory differs from allowlist')
    return {'ok': True, 'skill_manifest_files': files, 'local_links': links, 'public_manifest_files': exported, 'license': 'MIT', 'limit': 'Static contracts only; no domain or live integration guarantee'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path, nargs='?', default=Path('.'))
    args = parser.parse_args()
    try:
        result = verify(args.root.resolve())
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
