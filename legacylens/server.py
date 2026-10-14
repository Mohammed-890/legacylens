"""Local application server with bounded, read-only repository analysis."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import argparse
import json
from pathlib import Path
import secrets
import threading
from urllib.parse import urlparse
from .engine import analyze, investigate, impact
from . import agent
from .repair import fixture_files, proposal, execute_approved

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = {}
LOCK = threading.Lock()
TOKEN = secrets.token_urlsafe(32)
JOBS = threading.BoundedSemaphore(2)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(ROOT/'web'),**kwargs)

    def end_headers(self):
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'")
        super().end_headers()

    def json_response(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def valid_host(self):
        return self.headers.get('Host') in {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}

    def do_GET(self):
        if not self.valid_host():
            return self.json_response({'error':'Invalid host'},403)
        if self.path == '/api/status':
            return self.json_response({'mode':'local','llm':agent.configured(),'token':TOKEN})
        if self.path == '/api/demo':
            return self.json_response(analyze(fixture_files(),'Northstar · Billing Service'))
        if self.path == '/api/proposal':
            return self.json_response(proposal())
        if self.path.startswith('/api/'):
            return self.json_response({'error':'Unknown endpoint'},404)
        return super().do_GET()

    def do_POST(self):
        if not self.valid_host() or self.headers.get('X-LegacyLens-Token') != TOKEN:
            return self.json_response({'error':'Invalid session. Reload this local application.'},403)
        origin = self.headers.get('Origin')
        if origin and origin not in {f'http://127.0.0.1:{self.server.server_port}', f'http://localhost:{self.server.server_port}'}:
            return self.json_response({'error':'Cross-origin requests are not allowed.'},403)
        try:
            length = int(self.headers.get('Content-Length','0'))
            if length < 1 or length > 3_000_000:
                return self.json_response({'error':'Request exceeds limits.'},413)
            data = json.loads(self.rfile.read(length))
            if not isinstance(data,dict):
                raise ValueError('Expected a JSON object.')
        except (ValueError, UnicodeError):
            return self.json_response({'error':'Invalid request body.'},400)
        if not JOBS.acquire(blocking=False):
            return self.json_response({'error':'Two analyses are already running. Try again shortly.'},429)
        try:
            if self.path == '/api/analyze':
                project = analyze(data.get('files'), str(data.get('name','Imported repository')))
                with LOCK:
                    if len(PROJECTS)>=8:
                        del PROJECTS[next(iter(PROJECTS))]
                    PROJECTS[project['fingerprint']] = project
                return self.json_response(project)
            if self.path == '/api/repair':
                if data.get('approved') is not True:
                    return self.json_response({'error':'Explicit diff approval is required.'},403)
                return self.json_response(execute_approved(data.get('proposal_id')))
            if self.path in {'/api/investigate','/api/impact'}:
                if data.get('project') == 'demo':
                    project = analyze(fixture_files(),'Northstar · Billing Service')
                else:
                    with LOCK:
                        project = PROJECTS.get(data.get('project'))
                    if project is None:
                        return self.json_response({'error':'Repository expired. Import it again.'},404)
                if self.path == '/api/impact':
                    return self.json_response(impact(project,data.get('path')))
                question = data.get('question','')
                if not isinstance(question,str) or not 1<=len(question.strip())<=1500:
                    raise ValueError('Question must be 1–1500 characters.')
                # Cloud transmission must be explicitly chosen in the UI for each request.
                result = agent.run(project,question) if data.get('use_llm') is True else investigate(project,question)
                return self.json_response(result)
            return self.json_response({'error':'Unknown endpoint'},404)
        except ValueError as exc:
            self.json_response({'error':str(exc)},400)
        except Exception:
            # Do not expose provider credentials, request headers or repository contents in errors.
            self.json_response({'error':'Investigation failed. Check provider configuration or retry in local evidence mode.'},502)
        finally:
            JOBS.release()

    def log_message(self,fmt,*args):
        if args:
            print(f'LegacyLens HTTP {str(args[0])[:180]}', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--host',choices=['127.0.0.1','0.0.0.0'],default='127.0.0.1',help='Use 0.0.0.0 only inside the supplied container.')
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host,args.port),Handler)
    print(f'LegacyLens running at http://127.0.0.1:{args.port}',flush=True)
    server.serve_forever()


if __name__=='__main__':
    main()
