import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from legacylens.server import Handler, TOKEN


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.url=f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def post(self,path,data,token=TOKEN):
        req=urllib.request.Request(self.url+path,data=json.dumps(data).encode(),headers={'X-LegacyLens-Token':token,'Content-Type':'application/json'})
        return urllib.request.urlopen(req)

    def test_status(self):
        with urllib.request.urlopen(self.url+'/api/status') as r:
            self.assertEqual(json.load(r)['mode'],'local')

    def test_session_required(self):
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.post('/api/analyze',{'files':{'a.py':'x=1'}},token='bad')
        self.assertEqual(e.exception.code,403)

    def test_analyze_and_investigate(self):
        with self.post('/api/analyze',{'files':{'a.py':'def welcome():\n return "hello"'}}) as r:
            p=json.load(r)
        with self.post('/api/investigate',{'project':p['fingerprint'],'question':'welcome'}) as r:
            result=json.load(r)
        self.assertEqual(result['evidence'][0]['path'],'a.py')

    def test_approval_required(self):
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.post('/api/repair',{'approved':False})
        self.assertEqual(e.exception.code,403)

    def test_wrong_host_rejected(self):
        req=urllib.request.Request(self.url+'/api/status',headers={'Host':'attacker.example'})
        with self.assertRaises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(req)
        self.assertEqual(e.exception.code,403)

    def test_foreign_origin_rejected(self):
        req=urllib.request.Request(self.url+'/api/analyze',data=b'{}',headers={'X-LegacyLens-Token':TOKEN,'Origin':'https://attacker.example'})
        with self.assertRaises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(req)
        self.assertEqual(e.exception.code,403)
