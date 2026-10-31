function plot_static_teacher_function
% Plot the first 60 seconds using the unmodified course MatRTKLIB Gpos.plot.
% Only CSV selection, origin setting and figure export are handled here.
root = fileparts(fileparts(mfilename('fullpath')));
addpath(fullfile(root,'vendor','matRTKLIB'));
outputDir = fullfile(root,'figures','matlab_original');
if ~isfolder(outputDir); mkdir(outputDir); end
T = readtable(fullfile(root,'outputs','own_elevation','solution_details.csv'));
startTow = 464960.005;
keep = T.gps_week == 2442 & T.gps_tow_s >= startTow & T.gps_tow_s < startTow + 60;
S = T(keep,:);
assert(height(S) == 60, 'The confirmed static window must contain 60 epochs.');
xyz = [S.x_ecef_m S.y_ecef_m S.z_ecef_m];
assert(all(isfinite(xyz),'all'));
p = gt.Gpos(xyz,'xyz');
origin = p.mean();
p.setOrgGpos(origin);
assert(max(abs(mean(p.enu,1))) < 1e-5, 'ENU positions must be centered at their mean.');
expectedStd = [25.282786726521294 16.722211599961355 39.569609978290075];
assert(max(abs(std(p.enu,0,1)-expectedStd)) < 1e-5);
set(groot,'defaultFigureVisible','off');
p.plot(); % Native teacher-provided plotting function: East-North and Up panels.
f = gcf;
f.Position = [100 100 1000 650];
savefig(f,fullfile(outputDir,'04_static_first60.fig'));
exportgraphics(f,fullfile(outputDir,'04_static_first60.png'),'Resolution',180);
close(f);
metadata = struct('plot_function','gt.Gpos.plot (unmodified course MatRTKLIB)', ...
    'input_file','outputs/own_elevation/solution_details.csv', ...
    'solver','GPS L1 SPP with elevation-dependent weights', ...
    'gps_week',2442,'start_tow_s',startTow,'end_tow_exclusive_s',startTow+60, ...
    'epochs',height(S),'mean_ecef_m',mean(xyz,1), ...
    'sample_std_enu_m',std(p.enu,0,1), ...
    'horizontal_rms_about_mean_m',sqrt(mean(sum(p.enu(:,1:2).^2,2))));
fid = fopen(fullfile(outputDir,'04_static_first60_provenance.json'),'w','n','UTF-8');
assert(fid >= 0);
fwrite(fid,jsonencode(metadata,PrettyPrint=true),'char');
fclose(fid);
fprintf('Native plot saved: %d epochs; std ENU %.6f %.6f %.6f m; horizontal RMS %.6f m\n', ...
    metadata.epochs,metadata.sample_std_enu_m,metadata.horizontal_rms_about_mean_m);
fprintf('Gpos source: %s\n',which('gt.Gpos'));
end
