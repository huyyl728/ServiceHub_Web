#!/usr/bin/env python3
"""Publish a sanitized ServiceHub project to a new PRIVATE GitHub repository.

Usage:
  python3 scripts/publish_github.py --dry-run
  python3 scripts/publish_github.py --publish
Requires Git, GitHub CLI (gh), and `gh auth login` on the user's own computer.
No bank details or API tokens are stored in this script.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKLOG = ROOT / 'docs' / 'GITHUB_BACKLOG.json'
DEFAULT_FULL = 'huyyl728/ServiceHub-6-Sprints'


def run(*cmd: str, input_data: str | None = None, check: bool = True) -> str:
    result = subprocess.run(cmd, cwd=ROOT, text=True, input=input_data,
                            capture_output=True, check=False)
    if check and result.returncode:
        raise RuntimeError(f"Lệnh thất bại: {' '.join(cmd)}\n{result.stderr.strip()}")
    return result.stdout.strip()


def gh_json(*args: str, data: dict | None = None):
    if data is not None:
        out = run('gh', 'api', *args, '--input', '-', input_data=json.dumps(data, ensure_ascii=False))
    else:
        out = run('gh', 'api', *args)
    return json.loads(out)


def prohibited(path: str) -> bool:
    s = path.replace('\\', '/').lower()
    base = Path(s).name
    return (
        (base.startswith('.env') and base != '.env.example')
        or base.endswith(('.db', '.sqlite', '.sqlite3', '.pem', '.key', '.pfx', '.log'))
        or base in ('.ds_store',)
        or s.startswith('static/uploads/') and s != 'static/uploads/.gitkeep'
        or '/__pycache__/' in ('/' + s + '/')
        or s.startswith('.git/')
    )


def git_setup(login: str, user_id: str) -> None:
    if not (ROOT / '.git').exists():
        run('git', 'init', '-b', 'main')
    if not run('git', 'config', '--local', 'user.name', check=False):
        run('git', 'config', '--local', 'user.name', login)
    if not run('git', 'config', '--local', 'user.email', check=False):
        run('git', 'config', '--local', 'user.email', f'{user_id}+{login}@users.noreply.github.com')
    run('git', 'add', '-A')
    tracked = run('git', 'ls-files', '-z').split('\0')
    unsafe = [path for path in tracked if path and prohibited(path)]
    if unsafe:
        raise RuntimeError('Phát hiện tệp không an toàn trong Git staging: ' + ', '.join(unsafe))
    env_example = (ROOT / '.env.example').read_text(encoding='utf-8')
    match = re.search(r'^SERVICEHUB_BANK_ACCOUNT=(.*)$', env_example, re.M)
    if match and match.group(1).strip().strip('"\'').isdigit():
        raise RuntimeError('Không thể publish: .env.example chứa số tài khoản thực/chỉ số. Hãy thay bằng placeholder.')
    if run('git', 'diff', '--cached', '--name-only'):
        run('git', 'commit', '-m', 'feat: import ServiceHub Python MVP and six-sprint backlog')
    if run('git', 'branch', '--show-current') != 'main':
        raise RuntimeError('Nhánh hiện tại không phải main; dừng để tránh đẩy nhầm branch.')


def ensure_remote(full: str, existed: bool) -> None:
    remote = run('git', 'remote', 'get-url', 'origin', check=False)
    if remote and full.lower() not in remote.lower():
        raise RuntimeError('Đã có origin khác: ' + remote + '. Dừng để không đẩy nhầm repository.')
    if not existed:
        run('gh', 'repo', 'create', full, '--private', '--source', '.', '--remote', 'origin', '--push')
    else:
        if not remote:
            run('git', 'remote', 'add', 'origin', f'https://github.com/{full}.git')
        run('git', 'push', '-u', 'origin', 'main')


def labels_for(sprint: int, status: str, priority: str) -> list[str]:
    return [f'sprint:{sprint}', f'status:{status}', f'priority:{priority}']


def ensure_labels() -> None:
    for i in range(1, 7):
        run('gh', 'label', 'create', f'sprint:{i}', '--repo', DEFAULT_FULL, '--color', '1D76DB',
            '--description', f'Nhóm công việc Sprint {i}', '--force')
    for key, color, desc in (
        ('status:code-present', '0E8A16', 'Đã có mã nguồn nhưng chưa tự động được nghiệm thu'),
        ('status:planned', 'FBCA04', 'Công việc trong backlog, chưa xác nhận hoàn thành'),
        ('priority:P0', 'D93F0B', 'Ưu tiên cao'),
        ('priority:P1', 'C2E0C6', 'Ưu tiên bình thường'),
    ):
        run('gh', 'label', 'create', key, '--repo', DEFAULT_FULL, '--color', color, '--description', desc, '--force')


def publish(full: str, backlog: dict) -> None:
    if not shutil.which('gh'):
        raise RuntimeError('Chưa có GitHub CLI. Trên Mac dùng `brew install gh` rồi `gh auth login`.')
    if not shutil.which('git'):
        raise RuntimeError('Cần cài Git trước khi chạy script.')
    run('gh', 'auth', 'status')
    account = gh_json('user')
    login, user_id = account['login'], str(account['id'])
    owner = full.split('/')[0]
    if login.lower() != owner.lower():
        raise RuntimeError(f'Bạn đang đăng nhập gh với {login}; script dành cho {owner}. Dừng để tránh tạo nhầm repo.')
    git_setup(login, user_id)
    # `gh api` returns nonzero on 404; no repo yet is expected.
    existing = subprocess.run(['gh', 'api', f'repos/{full}'], cwd=ROOT, capture_output=True, text=True)
    if existing.returncode == 0:
        repo_info = json.loads(existing.stdout)
        if not repo_info.get('private'):
            raise RuntimeError('Repository đã tồn tại nhưng không Private; dừng để tránh công khai mã nguồn.')
        if repo_info.get('archived'):
            raise RuntimeError('Repository đã archive; không thể push.')
        existed = True
    elif '404' in existing.stderr or 'Not Found' in existing.stderr:
        existed = False
    else:
        raise RuntimeError('Không kiểm tra được tên repository: ' + existing.stderr.strip())
    ensure_remote(full, existed)
    # Milestones and issues are only created once code is pushed.
    ensure_labels()
    milestones_raw = gh_json(f'repos/{full}/milestones?state=all&per_page=100')
    milestone_map = {x['title']: x['number'] for x in milestones_raw}
    for sprint in backlog['milestones']:
        title = sprint['title']
        if title not in milestone_map:
            m = gh_json('-X', 'POST', f'repos/{full}/milestones', data={
                'title': title, 'description': sprint['description'], 'state': 'open',
            })
            milestone_map[title] = m['number']
            print('  + Milestone:', title)
    existing_issues = gh_json(f'repos/{full}/issues?state=all&per_page=100')
    existing_titles = {i['title'] for i in existing_issues if 'pull_request' not in i}
    sprint_titles = {s['number']: s['title'] for s in backlog['milestones']}
    created = 0
    for item in backlog['issues']:
        if item['title'] in existing_titles:
            continue
        body = (f"**Sprint:** {item['sprint']} · **Mã:** {item['key']} · "
                f"**Trạng thái ban đầu:** {item['status']}\n\n"
                f"### Mô tả công việc\n- [ ] {item['description']}\n\n"
                f"### Tiêu chí nghiệm thu\n- [ ] {item['acceptance']}\n"
                '- [ ] Có link commit/PR, ảnh hoặc log kiểm thử liên quan.\n\n'
                '> `code-present` không đồng nghĩa đã nghiệm thu: đóng Issue sau khi xác minh.')
        gh_json('-X', 'POST', f'repos/{full}/issues', data={
            'title': item['title'], 'body': body,
            'milestone': milestone_map[sprint_titles[item['sprint']]],
            'labels': labels_for(item['sprint'], item['status'], item['priority']),
        })
        created += 1
        print('  + Issue:', item['key'])
    # Verify essential code file after push.
    gh_json(f'repos/{full}/contents/server.py?ref=main')
    gh_json(f'repos/{full}/contents/static/js/app.js?ref=main')
    print('\nTHÀNH CÔNG: ' + f'https://github.com/{full}')
    print(f'6 milestone, {len(backlog["issues"])} issue trong backlog; {created} issue mới tạo lần này.')
    print('Các Issue đều Open để nhóm đính bằng chứng và nghiệm thu trước khi đóng.')


def main():
    parser = argparse.ArgumentParser(description='Publish ServiceHub to new private GitHub repo')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--dry-run', action='store_true', help='Preview without touching GitHub or Git')
    mode.add_argument('--publish', action='store_true', help='Create private repo, push code, milestones, issues')
    args = parser.parse_args()
    backlog = json.loads(BACKLOG.read_text(encoding='utf-8'))
    full = backlog['repository']
    if full != DEFAULT_FULL:
        raise RuntimeError(f'Unexpected repository: {full}')
    if args.dry_run:
        print(f'Repository: {full} (PRIVATE)')
        print('Source:', ROOT)
        print('Milestones:', len(backlog['milestones']))
        print('Issues:', len(backlog['issues']))
        print('By sprint:', {i: sum(t['sprint'] == i for t in backlog['issues']) for i in range(1, 7)})
        print('Source files:', len([x for x in ROOT.rglob('*') if x.is_file() and '.git' not in x.parts and not prohibited(str(x.relative_to(ROOT)))]))
        print('No GitHub changes made.')
    else:
        publish(full, backlog)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, subprocess.SubprocessError, OSError) as exc:
        print('LỖI:', str(exc), file=sys.stderr)
        sys.exit(1)
