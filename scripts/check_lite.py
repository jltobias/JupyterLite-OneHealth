"""Clear precomputed outputs, then execute actual notebooks in fresh Pyodide workers.

Playwright/Chrome are separate verification tools, not site runtime dependencies.
"""
import argparse,os
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:8000/JupyterLite-OneHealth/');p.add_argument('--all',action='store_true');p.add_argument('--notebook',choices=[x.name for x in (ROOT/'content').glob('*.ipynb')]);a=p.parse_args()
 files=sorted((ROOT/'content').glob('*.ipynb')) if a.all else [ROOT/'content/00_provenance_profile.ipynb']
 if a.notebook:files=[ROOT/'content'/a.notebook]
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path='C:/Program Files/Google/Chrome/Application/chrome.exe' if os.name=='nt' else None,headless=True)
  for path in files:
   context=browser.new_context()
   page=context.new_page();page.goto(a.url+'lite/lab/index.html?path='+path.name)
   page.wait_for_selector('.jp-Notebook .jp-CodeCell',timeout=90000)
   page.get_by_role('menuitem',name='Edit',exact=True).click()
   page.get_by_role('menuitem',name='Clear Outputs of All Cells',exact=True).click()
   assert page.locator('.jp-OutputArea-output').count()==0
   page.get_by_role('menuitem',name='Run',exact=True).click()
   page.get_by_role('menuitem',name='Run All Cells',exact=True).click()
   # A new image can only be produced by this actual fresh worker execution.
   try:
    page.wait_for_function('document.querySelector(".jp-OutputArea img") || document.querySelector(".jp-OutputArea-error")',timeout=420000)
    assert page.locator('.jp-OutputArea-error').count()==0,page.locator('.jp-OutputArea-error').all_inner_texts()
    assert page.locator('.jp-OutputArea img').count()>0
    # Windowed notebooks unmount cells outside the viewport. Revisit the setup
    # output after checking the freshly generated figure at the bottom.
    page.locator('.jp-Notebook').evaluate('(element) => element.scrollTo(0, 0)')
    page.wait_for_function('Array.from(document.querySelectorAll(".jp-OutputArea")).some(el => el.textContent.includes("LC09_L2SP_042035_20240830_02_T1"))',timeout=15000)
    print('Fresh Pyodide execution passed: '+path.name,flush=True)
   except Exception:
    print(page.locator('body').inner_text()[-2500:],flush=True);raise
   context.close()
  browser.close()
if __name__=='__main__':main()
