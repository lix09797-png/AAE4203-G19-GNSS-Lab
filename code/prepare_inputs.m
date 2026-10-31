function prepare_inputs(matrtklib_dir)
% Reproduce course GPS conversion and export full-constellation diagnostics.
root=fileparts(fileparts(mfilename('fullpath'))); cd(root);
if nargin<1; matrtklib_dir=fullfile(root,'vendor','matRTKLIB'); end
addpath(matrtklib_dir); addpath(fullfile(root,'code'));
if ~isfile('inputs/own/epochs.csv'); rinex2csv('raw/full.obs','raw/full.nav','inputs/own'); end
if ~isfile('inputs/example_modern/epochs.csv'); rinex2csv('raw/blockx_2025.obs','raw/blockx_2025.nav','inputs/example_modern'); end
obs=gt.Gobs('raw/full.obs'); nav=gt.Gnav('raw/full.nav');
sat=gt.Gsat(obs,nav);
% Header position used for geometry diagnostics only, never as a final answer.
sat.setRcvPos(gt.Gpos([-2418216.2426 5385801.2351 2405784.9877],'xyz'));
[k,j]=find(isfinite(obs.L1.P) & obs.L1.P>1e7);
ix=sub2ind([obs.n obs.nsat],k,j);
ids=obs.satstr(j); ids=ids(:);
t=table(reshape(obs.time.week(k),[],1),reshape(obs.time.tow(k),[],1),ids,obs.L1.P(ix),obs.L1.S(ix),sat.az(ix),sat.el(ix),sat.svh(ix), ...
 'VariableNames',{'gps_week','gps_tow_s','satellite_id','pseudorange_m','cno_dbhz','azimuth_deg','elevation_deg','health'});
writetable(t,'inputs/own/raw_observations.csv');
fprintf('Diagnostic records: %d\n',height(t));
end
