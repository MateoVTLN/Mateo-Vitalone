# Academic reports (PDFs)

Put your university report PDFs in this folder, then register each one in
[`academic.js`](../academic.js) at the repo root:

1. Copy a PDF here, e.g. `docs/room_acoustics_report.pdf`
   (use simple filenames: no spaces or accents).
2. Open `academic.js` and add an entry to the `ACADEMIC_WORKS` array
   (a ready-to-copy template is in the comment at the top of that file).
3. Set its `pdf` field to the path, e.g. `"docs/room_acoustics_report.pdf"`.

The Academic page renders the new card automatically, including the topic
filter chips. Entries with `pdf: null` show a "Report coming soon" badge.
