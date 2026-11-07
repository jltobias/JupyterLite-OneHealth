"""Serve _site at its configured project prefix for accurate local route testing."""
import argparse,json
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8000);p.add_argument('--base-url');a=p.parse_args()
 prefix=a.base_url if a.base_url is not None else json.loads((ROOT/'_site/build-info.json').read_text())['base_url']
 class Handler(SimpleHTTPRequestHandler):
  def prepare_path(self):
   if prefix and (self.path==prefix or self.path=='/'):
    self.send_response(302);self.send_header('Location',prefix+'/');self.end_headers();return False
   if prefix and not self.path.startswith(prefix+'/'):self.send_error(404);return False
   self.path=self.path[len(prefix):] if prefix else self.path
   return True
  def do_GET(self):
   if self.prepare_path():super().do_GET()
  def do_HEAD(self):
   if self.prepare_path():super().do_HEAD()
  def end_headers(self):
   self.send_header('Cache-Control','no-store');super().end_headers()
 server=ThreadingHTTPServer(('127.0.0.1',a.port),partial(Handler,directory=str(ROOT/'_site')))
 print(f'Serving http://127.0.0.1:{a.port}{prefix}/',flush=True)
 try:server.serve_forever()
 except KeyboardInterrupt:pass
if __name__=='__main__':main()
