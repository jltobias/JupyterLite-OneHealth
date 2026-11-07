"""Regression checks for source selection and provider retry headers; no data invented for teaching."""
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from acquire_data import BANDS, covering_candidates, retry_delay

def main():
    bbox=[-119.90,36.65,-119.65,36.90]
    # Minimal STAC protocol fixtures isolate selection, without pretending to be observations.
    assets={band:{} for band in BANDS}
    partial={'id':'LC09_L2SP_partial','bbox':[-120,36.7,-119,37],'assets':assets}
    covering={'id':'LC09_L2SP_covering','bbox':[-120,36,-119,37],'assets':assets}
    assert covering_candidates([partial,covering],bbox)==[covering]
    assert covering_candidates([partial],bbox)==[]
    assert retry_delay('2',0)==2 and retry_delay(None,1)==4
    date=format_datetime(datetime.now(timezone.utc)+timedelta(seconds=12),usegmt=True)
    assert 9<=retry_delay(date,0)<=13
    for value in ('nan','60','invalid-date'):
        try: retry_delay(value,0)
        except RuntimeError: pass
        else: raise AssertionError(value)
    print('Acquisition coverage selection and numeric/date Retry-After checks passed.')

if __name__=='__main__': main()
