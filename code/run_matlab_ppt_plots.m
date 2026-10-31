function run_matlab_ppt_plots(matrtklib_dir)
% Execute the MATLAB sequence in AAE4203 Week 9 PPT pp.23,45-46.
% Own full log replaces the course's example observations/navigation.
root=fileparts(fileparts(mfilename('fullpath'))); cd(root);
if nargin<1
    matrtklib_dir=fullfile(root,'vendor','matRTKLIB');
end
addpath(matrtklib_dir); addpath(fullfile(root,'code'));
set(groot,'defaultFigureVisible','off');
out_dir=fullfile(root,'figures','matlab_original');
if ~isfolder(out_dir);mkdir(out_dir);end
obs=gt.Gobs('raw/full.obs');
nav=gt.Gnav('raw/full.nav');
fprintf('PPT MATLAB sequence: %d epochs, %d satellite IDs\n',obs.n,obs.nsat);
obs.plot;
f=gcf;f.Position=[80 80 1300 1050];
xlabel('GPST on 2026-10-30');ylabel('Satellite ID');
title('Own full log: native MatRTKLIB observation/CNR plot');
savefig(f,fullfile(out_dir,'01_observations.fig'));
exportgraphics(f,fullfile(out_dir,'01_observations.png'),'Resolution',180);
close(f);
obs.plotNSat;
f=gcf;f.Position=[80 80 1300 650];
xlabel('GPST on 2026-10-30');ylabel('Number of primary-band observations');
savefig(f,fullfile(out_dir,'02_satellite_counts.fig'));
exportgraphics(f,fullfile(out_dir,'02_satellite_counts.png'),'Resolution',180);
close(f);
obs.plotSky(nav);
f=gcf;f.Position=[80 80 1150 950];
title('Own full log: native MatRTKLIB sky plot');
savefig(f,fullfile(out_dir,'03_skyplot.fig'));
exportgraphics(f,fullfile(out_dir,'03_skyplot.png'),'Resolution',180);
close(f);
% Same course function as the PPT. Fresh conversion log is retained.
rinex2csv('raw/full.obs','raw/full.nav','inputs/own');
fprintf('MATLAB PPT plots and five measurement CSVs saved successfully.\n');
end
