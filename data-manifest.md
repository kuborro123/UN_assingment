# Input data manifest

These hashes identify the source versions used by the audited pipeline. A hash
change means that the reconciliation counts and assertions must be reviewed.

| Input | SHA-256 |
| --- | --- |
| `Speakers_by_session.xlsx` | `1ab9a073a67cea005dec17de93fb5b8bd0215bbaca1476f735532bf0268a7dbb` |
| `UcdpPrioConflict_v26_1.csv` | `2aea044f1bcae7b050bb6c79fb796743e787edeed3b90e74e146cfc4e5b05447` |
| `SIPRI-Milex-data-1949-2025_v1.2.xlsx` | `6cc3a30b1064f9f02e60236667eef82e08cad42910ce630909d004ad2c398a9d` |

The text corpus contains 11,141 files whose names match the expected
`ISO_session_year.txt` pattern inside the 80 session directories. Individual
file accounting is written to `outputs/audit/` whenever the notebook runs.
