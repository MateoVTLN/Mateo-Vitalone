/* ════════════════════════════════════════════════════════════
   Academic works — data only.
   To add a new work:
     1. Drop the report PDF into  docs/   (e.g. docs/my_report.pdf)
     2. Copy the template below into the ACADEMIC_WORKS array
        and fill it in. The gallery page renders it automatically,
        including the filter chips (built from the tags).

   Template:
   {
       title:    "Title of the work",
       year:     2026,
       course:   "Course name · Institution",
       abstract: "Two or three sentences describing the work.",
       tags:     ["Acoustics", "Signal processing"],
       pdf:      "docs/my_report.pdf",   // or null → shows "Report coming soon"
       code:     "https://github.com/…", // or null → no code button
   },
   ════════════════════════════════════════════════════════════ */

const ACADEMIC_WORKS = [
    {
        title:    "Neural Networks for Music Genre Classification",
        year:     2025,
        course:   "Machine Learning for Audio · Politecnico di Milano",
        abstract: "Automatic music genre classification on the FMA-small dataset (8 genres), " +
                  "comparing classical machine-learning pipelines (Random Forest, SVM on MFCC, " +
                  "chroma and spectral-contrast features extracted with librosa) against " +
                  "convolutional neural networks trained on mel-spectrograms. The CNN reached " +
                  "72% validation accuracy, outperforming the handcrafted-feature approaches.",
        tags:     ["Machine learning", "Audio", "MIR"],
        pdf:      null,
        code:     null,
    },
];
