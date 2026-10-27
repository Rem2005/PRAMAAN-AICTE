# Sample roster CSVs

Two synthetic files for trying the roster intake flow. **Every value is fabricated** —
invented local references, invented course codes, and `999…` placeholder identifiers.
Nothing here is a real student record, and the `apaar_id` column contains placeholder
values, not real APAAR IDs. The backend parses `apaar_id` only to detect duplicates and
never persists or returns it.

| File | Purpose |
| --- | --- |
| `sample-roster.csv` | 10 rows that pass validation. |
| `sample-roster-with-errors.csv` | The same 10 rows plus 3 deliberately broken rows, to demonstrate row-level error reporting. |

## Expected results

`sample-roster.csv` uploads as **10 valid rows, 0 invalid** and reaches `VALIDATED`, so it
can be confirmed.

`sample-roster-with-errors.csv` uploads as **10 valid, 3 invalid** and reaches
`VALIDATION_FAILED`. Confirmation is refused until every row is corrected. The three
errors are:

| Row | `local_ref` | Error |
| --- | --- | --- |
| 12 | `SYN-00011` | `seat_category is required` |
| 13 | `SYN-00012` | `invalid entry_level 'YEAR_ONE'` |
| 14 | `SYN-00001` | `duplicate local_ref 'SYN-00001'` |

## Column contract

`local_ref`, `course_code`, `academic_year`, `seat_category`, `entry_level` and
`identity_status` are required; `apaar_id` is optional. These are the documented fixed
column names from `backend/app/services/roster.py` (`REQUIRED_COLUMNS`) — free column
mapping is not implemented, so the header row must match exactly.

`academic_year` must equal the academic year of the batch it is uploaded to. Both files use
`2026-2027`, which is the batch year the intake screen and `seed-demo` default to. Change
the column if your batch uses a different year.

Allowed values:

- `seat_category`: `CAP_GENERAL`, `CAP_OBC`, `CAP_SC`, `CAP_ST`, `CAP_EWS`
- `entry_level`: `FIRST_YEAR`, `SECOND_YEAR`, `THIRD_YEAR`, `FOURTH_YEAR`
- `identity_status`: `DOMESTIC_APAAR`, `INTERNATIONAL`, `NRI`

`course_code` is free text; the values above (`CE-UG-FT-S1` = programme, level, mode,
term) are illustrative only and encode no official course list.

## Verification

`backend/tests/test_sample_roster.py` uploads both files through the real
`POST /api/v1/batches` and `POST /api/v1/batches/{id}/validate` endpoints and asserts the
counts and error messages in the tables above. `frontend/src/lib/sampleRoster.test.ts`
asserts that the CSV the intake screen downloads for academic year `2026-2027` matches these
files row for row, so the two cannot drift apart.
