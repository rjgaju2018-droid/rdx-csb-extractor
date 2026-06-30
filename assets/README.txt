Apna logo yahan rakho is naam se:

    rdx_soloution_logo.png

(ya phir `logo.png`)

App in dono naamon se logo dhoondhta hai is folder ke andar:
    rdx_csb_app.py wali jagah par hi.

Agar logo nahi milega to app text-based "RDx Solution" title dikha dega — error nahi aayega.

NOTE: App ke andar ye path set hai:
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "rdx_soloution_logo.png")

Matlab logo file `rdx_csb_app.py` ke **same folder** mein honi chahiye —
is `assets/` folder mein nahi (sirf reference ke liye yeh folder banaya hai).
Agar chaaho to logo seedha root folder mein rakho.
