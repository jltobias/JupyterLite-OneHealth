"""Fresh-kernel notebook execution and structural checks for the real-data lessons."""
import argparse, os, sys
from pathlib import Path
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager

ROOT=Path(__file__).resolve().parents[1]
def main():
    for key,folder in [('JUPYTER_RUNTIME_DIR','jupyter-runtime'),('IPYTHONDIR','ipython'),('MPLCONFIGDIR','matplotlib')]:
        local=ROOT/'.cache'/folder;local.mkdir(parents=True,exist_ok=True);os.environ[key]=str(local)
    p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');p.add_argument('--write',action='store_true');args=p.parse_args()
    files=sorted((ROOT/'content').glob('*.ipynb'));assert len(files)==11
    for path in files:
        nb=nbformat.read(path,as_version=4);nbformat.validate(nb)
        codes=[c for c in nb.cells if c.cell_type=='code']
        text='\n'.join(c.source for c in nb.cells if c.cell_type=='markdown')
        assert len(codes)>=3 and 'Sources and attribution' in text and 'Interpret and extend' in text,path
        if args.execute:
            km=KernelManager(kernel_name='python3')
            km.kernel_spec.argv=[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}']
            client=NotebookClient(nb,km=km,timeout=240,resources={'metadata':{'path':str(ROOT/'content')}},allow_errors=False)
            try:
                client.execute()
            finally:
                if km.has_kernel: km.shutdown_kernel(now=True)
            assert any(o.get('data',{}).get('image/png') for c in nb.cells if c.cell_type=='code' for o in c.get('outputs',[])),f'No figure: {path}'
            if args.write: nbformat.write(nb,path)
        print(('Executed' if args.execute else 'Validated')+' '+path.name,flush=True)
    generated=ROOT/'content/my-evidence-brief.json'
    if generated.exists(): generated.unlink()
if __name__=='__main__':main()
