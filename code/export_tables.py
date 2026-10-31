"""Export measured result tables; no reference trajectory or invented scores are used."""
from pathlib import Path
import csv,json
ROOT=Path(__file__).resolve().parents[1]
r=json.loads((ROOT/'outputs/results_summary.json').read_text())
def write(name,rows):
    with (ROOT/'docs'/name).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
rows=[]
for m in r['own_comparisons']:
    rows.append({'comparison':m['comparison'],'matched_epochs':m['matched_epochs'],
        **dict(zip(['mean_e_m','mean_n_m','mean_u_m'],m['mean_enu_m'])),
        **dict(zip(['sample_std_e_m','sample_std_n_m','sample_std_u_m'],m['sample_std_enu_m'])),
        'rms_difference_2d_m':m['rms_difference_2d_m'],'rms_difference_3d_m':m['rms_difference_3d_m'],
        'p95_difference_2d_m':m['p95_difference_2d_m']})
write('own_solution_comparisons.csv',rows)
write('benchmark_local_diagnostics.csv',[{'version':v['method'],'input_epochs':v['input_epochs'],
    'solved_epochs':v['solved_epochs'],'local_output_coverage_percent':v['coverage_percent'],
    'mean_postfit_pseudorange_rms_m':v['mean_postfit_rms_m'],
    'interpretation':'Measurement-fit and output-coverage diagnostics; not position RMSE'}
    for v in r['variants'] if v['dataset'].startswith('benchmark')])
write('static_first60_statistics.csv',[{'method':v['method'],'epochs':v['epochs'],
    **dict(zip(['sample_std_e_m','sample_std_n_m','sample_std_u_m'],v['sample_std_enu_m'])),
    'horizontal_rms_about_mean_m':v['rms_horizontal_about_mean_m'],
    'p95_horizontal_about_mean_m':v['p95_horizontal_about_mean_m']} for v in r['static_statistics']])
print('Exported own-data comparisons, first-60-second statistics and benchmark local diagnostics.')
