# Native course-library figures

01_observations uses gt.Gobs.plot; 02_satellite_counts uses gt.Gobs.plotNSat; 03_skyplot uses gt.Gobs.plotSky; 04_static_first60 uses gt.Gpos.plot with the mean of the confirmed first 60 seconds as its ENU origin. Each PNG has an editable FIG counterpart. The native plotting functions are unchanged; wrappers select inputs, set the origin, adjust formatting and export the figures. The static input coordinates come from the AI-assisted elevation-weighted GPS-SPP implementation.
