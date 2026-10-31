# AAE4203 GNSS Laboratory - Group G19

Reproducible field-data processing and GPS single point positioning (SPP) for AAE4203, Semester 1, 2026/27. This repository contains the raw measurements, documented processing code, course-input caches, native MATLAB figures and both trajectory CSVs required for the code/data hand-in.

## Quick reproduction

Use Python 3.10 or newer. From the downloaded or cloned repository root:

```powershell
python -m pip install -r requirements.txt
python -B reproduce.py
```

The script verifies and extracts the two archives in `data/`, runs the example checks and all three GPS solver variants, regenerates both trajectories and measured tables, runs the course CSV checker, and verifies the SHA-256 hashes of both submissions. MATLAB is not needed for this cached-input route. A successful run prints `PASS` and writes `docs/reproduction_check.json`.

The two reproducible outputs are:

- `submission/G19_owndata.csv`: 712 own-data positions, GPS week 2442.
- `submission/G19_benchmark.csv`: 1437 benchmark positions, GPS week 2158.

These files use the elevation-weighted solver. They are reproducible candidates, not a claim that this variant has the lowest benchmark position error. Alternative solutions are regenerated under `outputs/own_uniform`, `outputs/own_huber`, `outputs/benchmark_uniform` and `outputs/benchmark_huber`.

## Reprocess the raw files and regenerate the report figures

Windows, MATLAB and the appropriate compiled MATLAB runtime interface are needed for the bundled native tools. MATLAB R2025a was used for this work. With MATLAB available on PATH:

```powershell
python -B reproduce.py --from-raw --matlab-plots
```

If MATLAB is not on PATH, supply the installed executable:

```powershell
python -B reproduce.py --from-raw --matlab-plots --matlab "C:/Program Files/MATLAB/R2025a/bin/matlab.exe"
```

The raw route runs RTKLIB `convbin` and single-rover `rnx2rtkp`, regenerates the own/example/benchmark GPS matrices using `rinex2csv`, and then repeats the positioning and CSV checks. Temporary native-tool files are retained outside the repository; their location is printed for inspection.

After the default reproduction has extracted the tools and data, the figures can also be regenerated directly in MATLAB from the repository root:

```matlab
addpath('code');
run_matlab_ppt_plots;
plot_static_teacher_function;
```

## Repository contents

| Location | Contents |
| --- | --- |
| `data/gnss_data_and_inputs.zip` | Original own UBX/RINEX/position logs, regenerated complete own RINEX, course example and UrbanNav observations/navigation, observation-derived CSV caches and recomputed RTKLIB comparison positions. Paths and individual hashes are listed in `data/manifest.json`. |
| `data/windows_rtk_tools.zip` | Course-supplied Windows MatRTKLIB and RTKLIB utilities with original notices; extracted to `vendor/`. |
| `code/` | GPS LS/WLS/Huber implementation, retained course solver/helpers, MATLAB conversion/plotting wrappers, raw preprocessing and table export. |
| `submission/` | Both five-column trajectory CSVs. |
| `docs/` | Recorded checks, measured comparison tables, data provenance and AI-use disclosure. |
| `figures/matlab_original/` | Four course-library plots, each as PNG and editable MATLAB FIG. |

## Field data and input checks

The receiver was a u-blox ZED-F9P used near PolyU Block X on 30 October 2026. The weather was sunny. The antenna was hand-held during walking; its exact model was not established. The group confirmed that the first 60 seconds were stationary and that walking around Block X followed. The installed u-center version was 24.05.

The complete UBX contains 768 observations at 1 Hz over a 767-second span. The original `my.obs` contained 544 epochs; regeneration recovered 224 additional epochs. The complete record is retained rather than treating the whole recording as stationary. The receiver's position output is standalone and is used only for comparison.

The original DGPS `.pos` used identical rover/base observations and is retained only as an original diagnostic file. It is not used as an independent reference. Fresh GPS-only and multi-system single-rover RTKLIB SPP comparisons are included and can be regenerated from the raw observations.

## Solver and statistics

All three implemented variants use the same GPS L1 observation-derived inputs and screening rules. The converter applies a 15-degree elevation mask and a 15 dB-Hz C/N0 threshold. The positioning model includes satellite-clock, ionospheric, tropospheric, TGD and first-order Earth-rotation corrections.

- `uniform`: equal-weight least squares.
- `elevation`: elevation-dependent weights, proportional to the square of the sine of elevation.
- `huber`: elevation WLS followed by Huber IRLS, with a 3 m a priori zenith pseudorange scale and a 2.5 threshold.

The state consists of ECEF X/Y/Z and receiver clock bias in metres. Each stage allows 80 iterations with a 1e-4 m state-update threshold. Rank-deficient, invalid and non-converged epochs are omitted with reasons, not filled with previous coordinates.

Own-data comparisons match GPS week/time on a 0.1-second grid and use SPP-minus-reference differences in a fixed ENU frame at the mean matched reference position. Standard deviations use N-1. The first-60-second scatter uses its own mean position as the origin. Agreement and scatter are not absolute positioning accuracy.

## Measured local results

| Dataset | Equal weights | Elevation weights | Huber |
| --- | ---: | ---: | ---: |
| Own data: solved / input epochs | 712 / 768 | 712 / 768 | 712 / 768 |
| Benchmark: solved / input epochs | 1437 / 1534 | 1437 / 1534 | 1419 / 1534 |
| Benchmark: local output coverage (%) | 93.677 | 93.677 | 92.503 |
| Benchmark: mean post-fit pseudorange RMS (m) | 3.434 | 4.038 | 4.300 |

The last row is measurement-fit diagnostics, not 2D/3D positioning RMSE. Local coverage uses observation epochs as its denominator; platform availability uses matched reference epochs. No benchmark reference trajectory or invented benchmark position scores are included. These local diagnostics do not replace the benchmark accuracy/rank results requested by the course.

On the full own-data record, elevation WLS has horizontal RMS differences of 3.224 m against RTKLIB GPS-only SPP and 29.809 m against the receiver solution, over 712 matched epochs. The confirmed first-60-second horizontal RMS about its own mean is 30.059 m. See the CSVs in `docs/` for the component means and sample standard deviations.

The historical example reproduces 186/186 epochs and 2D/3D RMS differences of 37.910758/51.042844 m against its receiver reference. The modern example conversion solves 113/186 epochs with its own masks. The two populations are kept separate and are not treated as a direct improvement comparison.

## Figure provenance

The four published figures are drawn by the unchanged course-supplied MatRTKLIB methods `Gobs.plot`, `Gobs.plotNSat`, `Gobs.plotSky` and `Gpos.plot`. The wrappers select data, set the origin, adjust formatting and export images. The static figure uses coordinates from the AI-assisted elevation-weighted SPP implementation.

The Python solver also generates auxiliary diagnostic plots under the ignored `figures/exploratory/` directory. They are not the course-native report figures.

## Sources and AI use

Course resources: https://github.com/weisongwen/AAE4203-S12627/tree/main/Lab1 . MatRTKLIB: https://github.com/taroz/MatRTKLIB . RTKLIB explorer: https://github.com/rtklibexplorer/RTKLIB . See `THIRD_PARTY_NOTICES.md` for the retained notices and data provenance.

OpenAI Codex assisted with interpreting requirements, developing/debugging scripts, executing processing, checking outputs, organising materials and drafting text. Recorded computational checks and translated key prompts are documented in `docs/AI_USE.md` and `docs/VALIDATION.md`. Independent group review of the code and its interpretation remains the group's responsibility.
