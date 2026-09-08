# PyTest

Ad-hoc debugging / verification scripts. These are **not** unit tests — the real
doctype tests live next to their doctypes under `bb_academy/doctype/*/test_*.py`
and `bb_academy/tests/`.

Run one with:

    bench --site <site> execute bb_tution_management.PyTest.<module>.<function>

e.g.

    bench --site dreamtech-bench.local execute bb_tution_management.PyTest.test_fees.run
