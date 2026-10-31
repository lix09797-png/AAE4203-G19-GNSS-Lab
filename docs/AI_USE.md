# AI-use disclosure and selected prompts

Tool: OpenAI Codex. The prompts below are English translations of actual Chinese-language user instructions.

| Prompt | Recorded verification approach |
| --- | --- |
| These are my collected data and course guides. Complete the tasks according to the instructor's requirements, using the lab report requirements as the main reference. | Cross-check the tutorial, slides and report template; distinguish confirmed field facts from unknown equipment details. |
| Do not write the report yet. First obtain the required results from the data. | Check raw-data completeness, units/time, synthetic-state recovery, example regression and CSV format; compare own-data SPP with recomputed RTKLIB and receiver positions. |
| According to the instructor's slides, should MATLAB be run to obtain the results? | Execute the course MatRTKLIB sequence, inspect exported figures, regenerate input matrices and check numerical consistency. |
| The collection procedure matches that description; use the first 60 seconds for static analysis. | Check the selected GPS-time interval, 60 finite epochs and ENU centring; calculate sample standard deviations and RMS about the mean. |
| I can only include figures generated using the instructor-provided code. Reorganise what this page should contain accordingly. | Trace the published figures to native MatRTKLIB plotting methods, preserve their source and inspect exported images. |
| Package the materials and clearly indicate where each item belongs in the report. | Check material links and compare table entries with saved numerical outputs. |
| I will provide screenshots; guide me step by step on what to fill in on each page. | Cross-check draft descriptions with confirmed field details and numerical entries with saved result tables. |

AI-assisted code development and debugging are included in this disclosure. The positioning code is not represented as an unchanged instructor implementation. Group members must independently review and understand the submitted work; automated checks do not establish surveyed accuracy.
