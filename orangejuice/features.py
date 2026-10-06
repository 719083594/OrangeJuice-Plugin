"""Registered function inventory. Never import plugin source or evaluate regexes."""
from collections import defaultdict
from pathlib import PurePosixPath
import math


def text(value, limit=500):
    return value[:limit] if isinstance(value, str) else ''


def source(value):
    value = text(value).replace('\\', '/')
    parts = value.split('/')
    if not value or value.startswith('/') or ':' in value or any(p in ('', '.', '..') for p in parts):
        return ''
    return str(PurePosixPath(value))


def same_event(a, b):
    return a == b or a.startswith(b + '.') or b.startswith(a + '.')


def inventory(runtime, group=None):
    runtime = runtime if isinstance(runtime, dict) else {}
    raw = runtime.get('featureInventory')
    available = isinstance(raw, dict) and raw.get('schemaVersion') == 1
    items, files = [], []
    group = group if isinstance(group, dict) else {}
    default = group.get('default') if isinstance(group.get('default'), dict) else {}
    default_available = isinstance(group.get('default'), dict)
    disabled = default.get('disable') if isinstance(default.get('disable'), list) else []
    enabled = default.get('enable') if isinstance(default.get('enable'), list) else []
    if available:
        for index, item in enumerate((raw.get('features') if isinstance(raw.get('features'), list) else [])[:2000]):
            if not isinstance(item, dict):
                continue
            path = source(item.get('source'))
            rules = [{k: text(rule.get(k), 2000 if k == 'pattern' else 160) for k in ('pattern', 'flags', 'handler', 'permission', 'event')}
                     for rule in item.get('rules', [])[:80] if isinstance(rule, dict)] if isinstance(item.get('rules'), list) else []
            kind = item.get('kind') if item.get('kind') in ('command', 'notice', 'hook', 'integration', 'task', 'module') else 'integration'
            name = text(item.get('name'), 160) or '未命名功能'
            state = 'not-applicable' if kind in ('task', 'module') else 'unknown' if not default_available else 'disabled' if name in disabled else 'not-allowed' if enabled and name not in enabled else 'enabled'
            priority = item.get('priority')
            items.append({'id': str(index), 'name': name, 'description': text(item.get('description'), 1000), 'source': path,
                          'directory': path.split('/')[0] if path else '', 'origin': item.get('origin') if item.get('origin') in ('framework', 'extension') else 'unknown',
                          'kind': kind, 'event': text(item.get('event'), 160), 'rules': rules, 'cron': text(item.get('cron'), 200),
                          'scheduled': item.get('scheduled') is True, 'hooks': [text(x, 160) for x in (item.get('hooks') if isinstance(item.get('hooks'), list) else [])[:80] if isinstance(x, str)],
                          'handlers': [text(x, 160) for x in (item.get('handlers') if isinstance(item.get('handlers'), list) else [])[:80] if isinstance(x, str)],
                          'priority': priority if isinstance(priority, (int, float)) and not isinstance(priority, bool) and math.isfinite(priority) else None, 'defaultState': state})
        for item in (raw.get('files') if isinstance(raw.get('files'), list) else [])[:1500]:
            if not isinstance(item, dict) or not source(item.get('source')):
                continue
            files.append({'source': source(item['source']), 'origin': item.get('origin') if item.get('origin') in ('framework', 'extension') else 'unknown',
                          'featureCount': sum(x['source'] == source(item['source']) for x in items),
                          'importedClasses': item.get('importedClasses') if isinstance(item.get('importedClasses'), int) else None})
    groups, by_name, by_rule = [], defaultdict(list), defaultdict(set)
    for item in items:
        if item['kind'] != 'module':
            by_name[item['name']].append(item)
        for rule in item['rules']:
            if rule['pattern']:
                by_rule[(rule['pattern'], rule['flags'])].add((item['id'], rule['event'] or item['event']))
    for name, entries in by_name.items():
        if len(entries) > 1:
            groups.append({'type': 'name', 'label': '同名功能：' + name, 'ids': [x['id'] for x in entries], 'evidence': name})
    for (pattern, flags), entries in by_rule.items():
        by_event = defaultdict(set)
        for item_id, event in entries:
            if event:by_event[event].add(item_id)
        ids = set()
        for event, event_ids in by_event.items():
            if len(event_ids)>1:ids.update(event_ids)
            parts = event.split('.')
            for depth in range(1,len(parts)):
                ancestor_ids = by_event.get('.'.join(parts[:depth]),set())
                if ancestor_ids and len(event_ids | ancestor_ids)>1:ids.update(event_ids | ancestor_ids)
        if ids:
            groups.append({'type': 'rule', 'label': '相同触发规则', 'ids': sorted(ids, key=int), 'evidence': '/' + pattern + '/' + flags})
    broad = [item['id'] for item in items if any(rule['pattern'] in ('.*', '^.*$', '(.*)', '^(.*)$') for rule in item['rules'])]
    return {'available': available, 'stale': runtime.get('stale', True), 'timestamp': runtime.get('timestamp'), 'items': items, 'files': files,
            'duplicates': groups[:100], 'duplicateTruncated':len(groups)>100, 'broadEntries': broad, 'truncated': bool(raw.get('truncated')) if available else False,
            'groupControl': {'available': default_available, 'overrideCount': sum(k != 'default' for k in group), 'configId': 'group.yaml'}}
