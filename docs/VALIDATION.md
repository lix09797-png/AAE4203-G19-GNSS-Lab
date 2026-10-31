# Validation record

The processing checks include a synthetic exact-state recovery test (<1 mm threshold), the 186-epoch historical example regression, GPS-week/time and unit checks, strict trajectory CSV checks and one-to-one reference matching. Recorded original values are retained in `expected_results.json`; a fresh reproduction writes `reproduction_check.json` and checks the exact hashes of both submission CSVs.

The static plot requires exactly 60 finite positions and asserts that the centred ENU mean is below 1e-5 m and that its sample standard deviations agree with the recorded values within 1e-5 m. Expected elevation-WLS sample standard deviations are E=25.282787, N=16.722212 and U=39.569610 m, with horizontal RMS about the mean 30.058900 m.

Own-data comparison checks use 712 matched epochs. The E/N/U means against RTKLIB GPS SPP are 0.186626/-0.898424/2.138477 m; sample standard deviations are 1.653995/2.613551/9.535148 m. The corresponding horizontal RMS difference is 3.224113 m. Against the receiver, the horizontal RMS difference is 29.809116 m. These are differences between solutions, not surveyed errors.

For independent group review: rerun the example, verify selected GPS time matches and ECEF-to-ENU differences, recalculate a mean/sample standard deviation/RMS from the exported tables, and confirm each member can explain the algorithm and its limitations.
