import io
import json
import os
import unittest
from unittest.mock import patch
from legacylens.agent import run
from legacylens.engine import analyze


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.project=analyze({'a.py':'def hello():\n    return "world"'})

    def response(self,message):
        return io.BytesIO(json.dumps({'choices':[{'message':message}],'usage':{'prompt_tokens':10,'completion_tokens':5}}).encode())

    @patch.dict(os.environ,{'LLM_API_KEY':'fake','LLM_MODEL':'test-model'})
    def test_tool_call_and_valid_citation(self):
        calls=[self.response({'content':None,'tool_calls':[{'id':'t1','type':'function','function':{'name':'read_source','arguments':'{"path":"a.py"}'}}]}),self.response({'content':'{"answer":"hello returns world [E001]","citations":["E001"]}'})]
        with patch('urllib.request.urlopen',side_effect=calls):
            result=run(self.project,'What does hello do?')
        self.assertEqual(result['mode'],'live-agent')
        self.assertEqual(result['citations'],['E001'])
        self.assertEqual(result['usage']['input_tokens'],20)

    @patch.dict(os.environ,{'LLM_API_KEY':'fake','LLM_MODEL':'test-model'})
    def test_fabricated_citation_rejected(self):
        with patch('urllib.request.urlopen',return_value=self.response({'content':'{"answer":"fiction","citations":["E999"]}'})):
            result=run(self.project,'hello')
        self.assertEqual(result['mode'],'local-evidence')

    @patch.dict(os.environ,{},clear=True)
    def test_without_key_local(self):
        self.assertEqual(run(self.project,'hello')['mode'],'local-evidence')


if __name__=='__main__':
    unittest.main()
