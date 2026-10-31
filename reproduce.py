"""Unpack the supplied data/tools and reproduce both G19 trajectory CSVs."""
from pathlib import Path
import argparse,hashlib,json,os,platform,subprocess,sys,zipfile
from importlib.metadata import version
ROOT=Path(__file__).resolve().parent

def unpack():
    manifest=json.loads((ROOT/'data/manifest.json').read_text())
    for name,info in manifest['archives'].items():
        p=ROOT/'data'/name
        if hashlib.sha256(p.read_bytes()).hexdigest()!=info['sha256']:
            raise ValueError('Archive checksum mismatch: '+name)
        with zipfile.ZipFile(p) as z:
            for member in z.infolist():
                target=(ROOT/member.filename).resolve()
                if not target.is_relative_to(ROOT.resolve()):
                    raise ValueError('Archive path escapes repository: '+member.filename)
            z.extractall(ROOT)
        for rel,expected in manifest['members'][name].items():
            if hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()!=expected['sha256']:
                raise ValueError('Extracted file checksum mismatch: '+rel)
    return manifest

def run(command):
    subprocess.run(command,cwd=ROOT,check=True)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--from-raw',action='store_true',help='Regenerate RINEX, references and GPS caches; Windows/MATLAB required')
    ap.add_argument('--matlab-plots',action='store_true',help='Regenerate the four native course-library figures')
    ap.add_argument('--matlab',default='matlab',help='MATLAB executable or full path')
    args=ap.parse_args()
    manifest=unpack()
    for name in ['outputs','logs','submission','figures/exploratory']:(ROOT/name).mkdir(parents=True,exist_ok=True)
    if args.from_raw:
        if os.name!='nt': raise RuntimeError('Bundled native raw-data tools require Windows.')
        run([sys.executable,'-B','code/preprocess_raw.py','--matlab',args.matlab])
    run([sys.executable,'-B','code/analyze_gnss.py'])
    run([sys.executable,'-B','code/export_tables.py'])
    for name,week,folder in [('G19_owndata.csv',2442,'own'),('G19_benchmark.csv',2158,'benchmark')]:
        run([sys.executable,'-B','code/tools/check_submission.py','submission/'+name,'--week',str(week),'--epoch-file','inputs/'+folder+'/epochs.csv'])
        actual=hashlib.sha256((ROOT/'submission'/name).read_bytes()).hexdigest()
        if actual!=manifest['submissions'][name]['sha256']:
            raise AssertionError('Trajectory differs from the recorded submission: '+name)
    if args.matlab_plots:
        run([args.matlab,'-batch',"addpath('code'); run_matlab_ppt_plots; plot_static_teacher_function;",'-logfile','logs/matlab_native_figures.log'])
    result={'status':'passed','from_raw':args.from_raw,'native_matlab_figures_regenerated':args.matlab_plots,
        'python':platform.python_version(),'platform':platform.system(),
        'packages':{name:version(name) for name in ['numpy','pandas','matplotlib','pyubx2']},
        'submission_sha256':{n:hashlib.sha256((ROOT/'submission'/n).read_bytes()).hexdigest() for n in manifest['submissions']}}
    (ROOT/'docs/reproduction_check.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('PASS: both trajectory CSVs reproduce byte-for-byte and pass the course format/time checks.')
if __name__=='__main__':main()
