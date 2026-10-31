"""Regenerate RINEX and RTKLIB comparisons without modifying source data."""
import argparse,subprocess,tempfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--rtklib-dir',type=Path,default=ROOT/'vendor/RTKLIB');ap.add_argument('--matrtklib-dir',type=Path,default=ROOT/'vendor/matRTKLIB');ap.add_argument('--matlab',default='matlab');args=ap.parse_args()
    # Native RTKLIB path expansion cannot reliably handle non-ASCII Windows paths.
    stage=Path(tempfile.mkdtemp(prefix='AAE4203_G19_'))
    shutil.copy2(ROOT/'raw/COM5___9600_261030_090901.ubx',stage/'own.ubx')
    shutil.copy2(ROOT/'code/spp.conf',stage/'spp.conf')
    commands=[[str(args.rtklib_dir.resolve()/'convbin.exe'),'-r','ubx','-v','3.04','-od','-os','-oi','-ot','-ol','-o','full.obs','-n','full.nav','own.ubx']]
    for tag,systems in [('gps','G'),('multi','G,R,E,C')]:commands.append([str(args.rtklib_dir.resolve()/'rnx2rtkp.exe'),'-k','spp.conf','-p','0','-e','-sys',systems,'-d','3','-y','2','-o',f'rtklib_{tag}.pos','full.obs','full.nav'])
    for i,command in enumerate(commands):
        result=subprocess.run(command,cwd=stage,capture_output=True,check=True)
        (ROOT/'logs'/f'raw_reprocess_{i}.log').write_bytes(result.stdout+result.stderr)
    for n in ['full.obs','full.nav']:shutil.copy2(stage/n,ROOT/'raw'/n)
    for f in stage.glob('rtklib_*.pos*'):shutil.copy2(f,ROOT/'outputs'/f.name)
    # Force fresh course matrices when this explicit raw-data path is requested.
    quote=lambda s:str(s).replace('\\','/').replace("'","''")
    expression=f"addpath('code'); addpath('{quote(args.matrtklib_dir.resolve())}'); rinex2csv('raw/full.obs','raw/full.nav','inputs/own'); rinex2csv('raw/blockx_2025.obs','raw/blockx_2025.nav','inputs/example_modern'); rinex2csv('raw/urbannav_deep1.obs','raw/urbannav_deep1.nav','inputs/benchmark'); prepare_inputs('{quote(args.matrtklib_dir.resolve())}');"
    subprocess.run([args.matlab,'-batch',expression,'-logfile','logs/matlab_reprocess.log'],cwd=ROOT,check=True)
    print('Raw preprocessing completed. Run: python -B code/analyze_gnss.py')
    print('Native-tool temporary directory retained:',stage)
if __name__=='__main__':main()
