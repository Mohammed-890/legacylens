"""Static analysis and grounded retrieval. Repository content is never executed."""
from __future__ import annotations

import ast
import hashlib
import math
import re
from pathlib import PurePosixPath

MAX_FILES = 160
MAX_BYTES = 2_000_000
EXTENSIONS = {'.py', '.sql', '.md', '.txt', '.json', '.yaml', '.yml', '.toml'}
SECRET_NAMES = {'.env', 'credentials.json', 'id_rsa', 'id_ed25519'}


def validate_files(files):
    if not isinstance(files, dict) or not 1 <= len(files) <= MAX_FILES:
        raise ValueError(f'Provide between 1 and {MAX_FILES} text files.')
    result = {}
    for name, content in files.items():
        if not isinstance(name, str) or not isinstance(content, str):
            raise ValueError('File names and contents must be strings.')
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or '\\' in name or len(name) > 200:
            raise ValueError('Unsafe file path.')
        if path.name in SECRET_NAMES or path.suffix not in EXTENSIONS:
            continue
        if any(p.startswith('.') or p in {'node_modules', '__pycache__', 'venv'} for p in path.parts):
            continue
        if '\x00' in content:
            raise ValueError('Binary files are not supported.')
        result[str(path)] = content
    if not result:
        raise ValueError('No supported source files found.')
    if sum(len(s.encode()) for s in result.values()) > MAX_BYTES:
        raise ValueError('Repository exceeds the 2 MB text limit.')
    return result


def tokens(text):
    return re.findall(r'[a-z][a-z0-9_]+', text.lower())


def analyze(files, name='Repository'):
    files = validate_files(files)
    nodes, edges, findings, chunks, warnings = [], [], [], [], []
    modules = {p[:-3].replace('/', '.'): p for p in files if p.endswith('.py')}
    stems = {}
    for mod, path in modules.items():
        stems.setdefault(mod.rsplit('.', 1)[-1], []).append(path)
    def resolve(mod, current):
        if mod in modules:
            return modules[mod]
        sibling = str(PurePosixPath(current).parent / (mod.replace('.', '/') + '.py'))
        if sibling in files:
            return sibling
        candidates = stems.get(mod.rsplit('.', 1)[-1], [])
        return candidates[0] if len(candidates) == 1 else None
    def finding(path, line, severity, title, detail, rule):
        findings.append(dict(id=f'F{len(findings)+1:02}', path=path, line=line,
                             severity=severity, title=title, detail=detail, rule=rule))
    for path, source in sorted(files.items()):
        lines = source.splitlines()
        kind = 'database' if path.endswith('.sql') else 'docs' if path.endswith(('.md', '.txt')) else 'module'
        functions = []
        if path.endswith('.py'):
            try:
                tree = ast.parse(source)
                for n in ast.walk(tree):
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        functions.append(dict(name=n.name, line=n.lineno, end=n.end_lineno))
                    imports = []
                    if isinstance(n, ast.Import):
                        imports = [a.name for a in n.names]
                    elif isinstance(n, ast.ImportFrom):
                        # Relative module resolution uses the importing package, not a global basename.
                        if n.level:
                            parts = list(PurePosixPath(path).parent.parts)
                            if n.level > len(parts) + 1:
                                continue
                            parts = parts[:len(parts) - n.level + 1]
                            base = '.'.join(parts + ([n.module] if n.module else []))
                            imports = [base] if n.module else [('.'.join(parts + [a.name])) for a in n.names]
                        else:
                            imports = [n.module] if n.module else []
                    for mod in imports:
                        target = resolve(mod, path)
                        if target and target != path:
                            edges.append(dict(source=path, target=target, type='imports', line=n.lineno))
                    if isinstance(n, ast.ExceptHandler) and n.type is None:
                        finding(path, n.lineno, 'medium', 'Bare exception handler', 'This catches interrupts and can obscure failures. Catch a specific exception and preserve context.', 'bare-except')
                    if isinstance(n, ast.Call):
                        called = ast.unparse(n.func)
                        if called in {'eval', 'exec'}:
                            finding(path, n.lineno, 'high', 'Dynamic code execution', f'{called} executes supplied code. Review the input trust boundary.', 'dynamic-exec')
                        if called.endswith('.execute') and n.args and isinstance(n.args[0], (ast.JoinedStr, ast.BinOp)):
                            finding(path, n.lineno, 'high', 'Constructed SQL query', 'SQL is assembled dynamically at this call. Use bound parameters for untrusted values; inspect the data flow.', 'sql-interpolation')
                        if called in {'requests.get', 'requests.post', 'requests.put', 'requests.delete'} and not any(k.arg == 'timeout' for k in n.keywords):
                            finding(path, n.lineno, 'medium', 'HTTP request without timeout', 'A stalled remote service may keep this call blocked indefinitely.', 'missing-timeout')
                    if isinstance(n, ast.FunctionDef) and any(isinstance(d, (ast.List, ast.Dict, ast.Set)) for d in n.args.defaults):
                        finding(path, n.lineno, 'medium', 'Mutable default argument', 'This object is shared across calls and can leak state between requests.', 'mutable-default')
            except SyntaxError as exc:
                warnings.append(dict(path=path, line=exc.lineno, message='Python syntax could not be parsed; text retrieval is still available.'))
        nodes.append(dict(id=path, label=PurePosixPath(path).name, kind=kind, lines=len(lines), functions=functions))
        # Fixed windows give stable, auditable citations even for unsupported syntax.
        for start in range(0, len(lines), 24):
            chunks.append(dict(id=f'E{len(chunks)+1:03}', path=path, start=start+1,
                               end=min(start+24, len(lines)), text='\n'.join(lines[start:start+24])))
    for node in nodes:
        node['issues'] = sum(f['path'] == node['id'] for f in findings)
    digest = hashlib.sha256('\n'.join(p+'\0'+s for p,s in sorted(files.items())).encode()).hexdigest()[:12]
    return dict(name=name[:80], fingerprint=digest, files=files, nodes=nodes, edges=edges,
                findings=findings, chunks=chunks, warnings=warnings,
                stats=dict(files=len(files), lines=sum(n['lines'] for n in nodes),
                           functions=sum(len(n['functions']) for n in nodes), findings=len(findings)))


def search(project, query, limit=5):
    """BM25 lexical retrieval; scores are relevance, not confidence probabilities."""
    terms = set(tokens(query))
    documents = [tokens(c['path']+' '+c['text']) for c in project['chunks']]
    if not documents or not terms:
        return []
    avg = sum(map(len, documents))/len(documents)
    df = {t: sum(t in d for d in documents) for t in terms}
    ranked = []
    for chunk, doc in zip(project['chunks'], documents):
        score = 0
        for term in terms:
            count = doc.count(term)
            idf = math.log(1 + (len(documents)-df[term]+.5)/(df[term]+.5))
            score += idf * count * 2.2/(count+1.2*(.25+.75*len(doc)/max(avg,1)))
        if score:
            ranked.append({**chunk, 'score': round(score, 3)})
    return sorted(ranked, key=lambda c: (-c['score'], c['id']))[:limit]


def impact(project, target):
    if target not in project['files']:
        raise ValueError('Select a file in this repository.')
    visited = {target}
    frontier = [target]
    paths = []
    while frontier:
        current = frontier.pop(0)
        for edge in project['edges']:
            if edge['target'] == current and edge['source'] not in visited:
                visited.add(edge['source'])
                frontier.append(edge['source'])
                paths.append(edge)
    return dict(target=target, affected=sorted(visited-{target}), paths=paths,
                limitation='Static Python import dependencies only. Runtime calls, SQL lineage and dynamic imports are not inferred.')


def investigate(project, question):
    evidence = search(project, question)
    trace = [dict(tool='search_source', status='complete', detail=f'Retrieved {len(evidence)} source windows with BM25.')]
    cited_findings = [f for f in project['findings'] if any(c['path']==f['path'] and c['start']<=f['line']<=c['end'] for c in evidence)]
    answer = 'The available source does not contain a relevant match. Try a function, table, file name, or error message.'
    if evidence:
        answer = 'Relevant source evidence was found. Review the cited implementation and its callers before concluding a root cause.'
        if cited_findings:
            answer += ' Static checks flagged: ' + '; '.join(f['title'] for f in cited_findings) + '.'
        else:
            answer += ' No configured static rule matched these passages; that does not prove they are correct.'
        trace.append(dict(tool='read_source', status='complete', detail=f"Inspect {evidence[0]['path']}:{evidence[0]['start']}–{evidence[0]['end']}."))
    return dict(mode='local-evidence', answer=answer, evidence=evidence, trace=trace,
                citations=[c['id'] for c in evidence], findings=cited_findings,
                limitation='Deterministic source retrieval, not an LLM diagnosis. Configure a provider to enable agent investigation.')
