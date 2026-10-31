"""Reproduce GPS SPP variants, validation statistics and scientific figures.
Only observation-derived course inputs enter positioning; references are evaluation-only.
"""
from pathlib import Path
import csv,json,hashlib,sys,collections,struct,shutil
from datetime import datetime
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pyubx2 import UBXReader
from WLSE_spp import read_inputs,run as historical_run,reference_metrics
from tools.legacy_solver import ecef_to_lla
from tools.check_submission import check
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs'; FIG=ROOT/'figures'/'exploratory'
C=299792458.; OMEGA=7.2921151467e-5
HEADER=['gps_week','gps_tow_s','x_ecef_m','y_ecef_m','z_ecef_m']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':120,'savefig.dpi':190})
COLORS={'G':'#1766A4','R':'#C67B19','E':'#24836D','C':'#975C9F'}

def rotation(xyz):
    lat,lon,h=ecef_to_lla(*xyz); a,b=np.radians([lat,lon])
    return np.array([[-np.sin(b),np.cos(b),0],[-np.sin(a)*np.cos(b),-np.sin(a)*np.sin(b),np.cos(a)],[np.cos(a)*np.cos(b),np.cos(a)*np.sin(b),np.sin(a)]])

def model(sp,x):
    """GPS pseudorange prediction/Jacobian with first-order Earth-rotation correction.
    Satellite and receiver ECEF coordinates and the clock state are in metres.
    """
    d=sp-x[:3]; r=np.linalg.norm(d,axis=1)
    sag=OMEGA/C*(sp[:,0]*x[1]-sp[:,1]*x[0])
    H=np.column_stack([-d/r[:,None],np.ones(len(sp))])
    H[:,0]+=-OMEGA/C*sp[:,1]; H[:,1]+=OMEGA/C*sp[:,0]
    sine=d@rotation(x[:3])[2]/r if np.linalg.norm(x[:3])>6e6 else np.ones(len(sp))
    return r+sag+x[3],H,sine

def solve(sp,corrected,seed,method):
    """Solve [x, y, z, receiver-clock-metres] by iterative GPS-only LS/WLS.
    Huber starts from elevation WLS; failures are omitted rather than forward-filled.
    """
    x=np.r_[seed,0.]; base=None
    # A converged elevation WLS initializes the Huber experiment.
    stages=['elevation','huber'] if method=='huber' else [method]
    for stage in stages:
        converged=False
        for it in range(80):
            pred,H,sine=model(sp,x); v=corrected-pred
            w=np.ones(len(sp)) if stage=='uniform' else np.maximum(sine,.05)**2
            if stage=='huber':
                # Fixed a priori zenith pseudorange scale, 3 m; threshold 2.5 sigma.
                z=np.abs(v)*np.sqrt(w)/3.
                w*=np.minimum(1.,2.5/np.maximum(z,1e-12))
            a=np.sqrt(w)
            dx,_,rank,_=np.linalg.lstsq(H*a[:,None],v*a,rcond=None)
            if rank<4: raise ValueError('rank deficient GPS geometry')
            x+=dx
            if np.linalg.norm(dx)<1e-4: converged=True;break
        if not converged: raise ValueError(stage+' iteration did not converge')
    if not np.isfinite(x).all() or not 6.30e6<np.linalg.norm(x[:3])<6.42e6: raise ValueError('not an Earth surface solution')
    pred,H,sine=model(sp,x); v=corrected-pred
    R=rotation(x[:3]); Q=np.linalg.inv(H.T@H); QE=R@Q[:3,:3]@R.T
    return x,v,float(np.sqrt(QE[0,0]+QE[1,1])),float(np.sqrt(np.trace(Q[:3,:3]))),int(np.sum(np.abs(v)*np.maximum(sine,.05)/3>2.5)) if method=='huber' else 0

def run_variant(folder,tag,method):
    arrays,epochs=read_inputs(folder); rows=[]; residuals=[]; omitted=[]; seed=np.zeros(3)
    ids=pd.read_csv(folder/'satellites.csv').iloc[:,0].astype(str).to_numpy() if (folder/'satellites.csv').exists() else np.arange(arrays['pseudoranges_meas'].shape[0]).astype(str)
    for k,(week,tow) in enumerate(epochs):
        sp=arrays['satellite_positions'][:,3*k:3*k+3]
        v=[arrays[n][:,k] for n in ['pseudoranges_meas','satellite_clock_bias','ionospheric_delay','tropospheric_delay','group_delay']]
        mask=np.isfinite(sp).all(axis=1)
        for a in v: mask &= np.isfinite(a)
        if mask.sum()<4:
            omitted.append([week,tow,'fewer than four valid GPS measurements']);continue
        pr,clk,ion,trp,tgd=[a[mask] for a in v]
        try: x,res,hdop,pdop,down=solve(sp[mask],pr+clk-ion-trp-tgd,seed,method)
        except (ValueError,np.linalg.LinAlgError) as ex:
            omitted.append([week,tow,str(ex)]);continue
        seed=x[:3].copy()
        rows.append([week,tow,*x[:3],x[3],int(mask.sum()),hdop,pdop,float(np.sqrt(np.mean(res**2))),down])
        for sat,r in zip(ids[mask],res): residuals.append([week,tow,sat,r])
    d=OUT/tag; d.mkdir(exist_ok=True)
    cols=HEADER+['clock_bias_m','used_measurements','hdop','pdop','postfit_rms_m','downweighted_measurements']
    df=pd.DataFrame(rows,columns=cols); df.to_csv(d/'solution_details.csv',index=False)
    pd.DataFrame(residuals,columns=['gps_week','gps_tow_s','satellite_id','residual_m']).to_csv(d/'residuals.csv',index=False)
    pd.DataFrame(omitted,columns=['gps_week','gps_tow_s','reason']).to_csv(d/'omitted_epochs.csv',index=False)
    metrics={'dataset':tag,'method':method,'input_epochs':len(epochs),'solved_epochs':len(df),'coverage_percent':100*len(df)/len(epochs),'accuracy_status':'benchmark position accuracy not evaluated locally' if tag.startswith('benchmark') else 'receiver comparison only; no independent truth','mean_postfit_rms_m':float(df.postfit_rms_m.mean()),'downweighted_epochs':int((df.downweighted_measurements>0).sum())}
    (d/'summary.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    return df,metrics

def write_submission(df,path):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(HEADER)
        for row in df[HEADER].itertuples(index=False,name=None):w.writerow([int(row[0]),f'{row[1]:.1f}',*[f'{x:.3f}' for x in row[2:]]])

def parse_receiver():
    refs=[];pvts=[];dops=[];counts=collections.Counter();vers=[];rawtimes=[];bad=0
    with (ROOT/'raw/COM5___9600_261030_090901.ubx').open('rb') as f:
        for raw,msg in UBXReader(f,protfilter=2):
            if msg is None:continue
            name=msg.identity;counts[name]+=1
            if name=='RXM-RAWX':rawtimes.append([int(msg.week),float(msg.rcvTow)])
            elif name=='NAV-HPPOSECEF':
                if msg.invalidEcef:bad+=1;continue
                # pyubx2 combines the high precision parts into these centimetre fields.
                refs.append([2442,float(msg.iTOW)/1000,float(msg.ecefX)/100,float(msg.ecefY)/100,float(msg.ecefZ)/100,float(msg.pAcc)/1000])
            elif name=='NAV-PVT':pvts.append([2442,float(msg.iTOW)/1000,float(msg.gSpeed)/1000,float(msg.hAcc)/1000,int(msg.gnssFixOk),int(msg.diffSoln),int(msg.carrSoln),int(msg.numSV)])
            elif name=='NAV-DOP':dops.append([2442,float(msg.iTOW)/1000,float(msg.hDOP),float(msg.vDOP),float(msg.pDOP)])
            elif name=='MON-VER':vers.append(raw[6:-2].replace(b'\x00',b' ').decode('ascii','replace'))
    ref=pd.DataFrame(refs,columns=HEADER+['receiver_pacc_m']);ref.to_csv(OUT/'receiver_ecef.csv',index=False)
    pvt=pd.DataFrame(pvts,columns=['gps_week','gps_tow_s','speed_mps','receiver_hacc_m','fix_ok','differential','carrier_solution','num_sv']);pvt.to_csv(OUT/'receiver_pvt.csv',index=False)
    dop=pd.DataFrame(dops,columns=['gps_week','gps_tow_s','hdop','vdop','pdop']);dop.to_csv(OUT/'receiver_dop.csv',index=False)
    info={'ubx_message_counts':dict(counts),'receiver_versions':vers,'invalid_receiver_ecef_messages':bad,'rawx_epochs':len(rawtimes),'first_epoch':rawtimes[0],'last_epoch':rawtimes[-1],'duration_seconds':rawtimes[-1][1]-rawtimes[0][1],'receiver_reference_warning':'standalone receiver solution, not ground truth'}
    (OUT/'ubx_summary.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
    return ref,pvt,dop,info

def parse_pos(path):
    rows=[]
    for l in path.read_text(encoding='utf-8',errors='replace').splitlines():
        if not l.strip() or l.startswith('%'):continue
        a=l.split()
        if '/' in a[0]:
            seconds=(datetime.strptime(a[0]+' '+a[1],'%Y/%m/%d %H:%M:%S.%f')-datetime(1980,1,6)).total_seconds()
            week=int(seconds//604800);tow=seconds-week*604800
        else: week,tow=int(a[0]),float(a[1])
        rows.append([week,tow,*map(float,a[2:5]),int(a[5])])
    return pd.DataFrame(rows,columns=HEADER+['quality'])

def compare(a,b,label):
    """One-to-one time matching and SPP-minus-reference differences in fixed ENU.
    The frame origin is the mean matched reference; standard deviations use N-1.
    """
    # Rounded time matching follows course's 0.1-s contract; verify one-to-one.
    a=a.copy();b=b.copy()
    for d in [a,b]: d['gps_tow_s']=d.gps_tow_s.round(1)
    m=a[HEADER].merge(b[HEADER],on=HEADER[:2],suffixes=('_a','_b'),validate='one_to_one')
    if len(m)==0:raise ValueError('no matched epochs '+label)
    pa=m[[c+'_a' for c in HEADER[2:]]].to_numpy();pb=m[[c+'_b' for c in HEADER[2:]]].to_numpy()
    enu=(pa-pb)@rotation(pb.mean(axis=0)).T;h=np.linalg.norm(enu[:,:2],axis=1)
    result={'comparison':label,'matched_epochs':len(m),'mean_enu_m':enu.mean(axis=0).tolist(),'sample_std_enu_m':enu.std(axis=0,ddof=1).tolist(),'rms_difference_2d_m':float(np.sqrt(np.mean(h*h))),'rms_difference_3d_m':float(np.sqrt(np.mean(np.sum(enu*enu,axis=1)))),'p95_difference_2d_m':float(np.percentile(h,95))}
    table=pd.DataFrame(enu,columns=['east_m','north_m','up_m']);table.insert(0,'gps_tow_s',m.gps_tow_s)
    table.to_csv(OUT/(label+'.csv'),index=False)
    return result,table

def savefig(name):
    plt.savefig(FIG/(name+'.png'),bbox_inches='tight');plt.close()

def plots(raw,own,ref,pvt,dop,diffs,bench):
    t0=raw.gps_tow_s.min();full_grid=np.sort(raw.gps_tow_s.unique());raw=raw.copy();
    # NaNs mark unsolved epochs; do not draw lines across missing solutions.
    own_plot=own.set_index('gps_tow_s').reindex(full_grid).rename_axis('gps_tow_s').reset_index();raw['minutes']=(raw.gps_tow_s-t0)/60;raw['system']=raw.satellite_id.str[0]
    counts=raw.groupby(['gps_tow_s','system']).satellite_id.nunique().unstack(fill_value=0)
    fig,ax=plt.subplots(2,1,figsize=(10,7),sharex=True)
    for s in COLORS:
        if s in counts:ax[0].plot((counts.index-t0)/60,counts[s],label=s,color=COLORS[s])
        g=raw[raw.system==s].groupby('gps_tow_s').cno_dbhz
        med=g.median();lo=g.quantile(.1);hi=g.quantile(.9)
        ax[1].plot((med.index-t0)/60,med,label=s,color=COLORS[s]);ax[1].fill_between((med.index-t0)/60,lo,hi,color=COLORS[s],alpha=.12)
    ax[0].set(ylabel='Unique tracked satellites',title='Full own-data log: primary-frequency observations')
    ax[0].legend(ncol=4);ax[1].set(xlabel='Minutes from first observation',ylabel='C/N0 (dB-Hz)',title='Median and 10th-90th percentile across satellites');ax[1].axhline(30,color='grey',ls='--',lw=.8)
    for a in ax:a.grid(alpha=.2)
    fig.tight_layout();savefig('01_raw_quality')
    fig,ax=plt.subplots(subplot_kw={'projection':'polar'},figsize=(7,7));ax.set_theta_zero_location('N');ax.set_theta_direction(-1)
    for s in COLORS:
        d=raw[(raw.system==s)&raw.azimuth_deg.notna()&(raw.elevation_deg>=0)]
        ax.scatter(np.radians(d.azimuth_deg),90-d.elevation_deg,s=3,alpha=.22,color=COLORS[s],label=s)
    ax.set_ylim(0,90);ax.set_title('Satellite sky tracks during the complete record',pad=32);ax.set_yticks([0,30,60,90],['90 deg','60 deg','30 deg','0 deg']);ax.legend(loc='lower left',bbox_to_anchor=(1,0),markerscale=3);savefig('02_skyplot')
    fig,ax=plt.subplots(2,1,figsize=(10,6),sharex=True)
    ax[0].plot((own_plot.gps_tow_s-t0)/60,own_plot.hdop,label='GPS solver HDOP');ax[0].plot((dop.gps_tow_s-t0)/60,dop.hdop,label='Receiver HDOP',alpha=.7)
    ax[1].plot((own_plot.gps_tow_s-t0)/60,own_plot.pdop,label='GPS solver PDOP');ax[1].plot((dop.gps_tow_s-t0)/60,dop.pdop,label='Receiver PDOP',alpha=.7)
    for a in ax:a.legend();a.grid(alpha=.2);a.set_ylabel('DOP (dimensionless)')
    ax[0].set_title('Geometry: GPS-only solver and multiconstellation receiver');ax[1].set_xlabel('Minutes from first observation');fig.tight_layout();savefig('03_dop')
    origin=ref[HEADER[2:]].to_numpy().mean(axis=0);R=rotation(origin)
    fig,ax=plt.subplots(1,2,figsize=(11,5))
    for df,label in [(ref,'Receiver reference'),(own_plot,'GPS elevation WLS')]:
        enu=(df[HEADER[2:]].to_numpy()-origin)@R.T
        ax[0].plot(enu[:,0],enu[:,1],lw=1,alpha=.7,label=label)
    enu=(own[HEADER[2:]].to_numpy()-origin)@R.T
    sc=ax[1].scatter(enu[:,0],enu[:,1],c=(own.gps_tow_s-t0)/60,s=7,cmap='viridis');fig.colorbar(sc,ax=ax[1],label='Minutes')
    for a in ax:a.set(xlabel='East (m)',ylabel='North (m)');a.axis('equal');a.grid(alpha=.2)
    ax[0].legend();ax[0].set_title('Observed trajectory, including walking');ax[1].set_title('SPP trajectory by time; spread includes motion');fig.tight_layout();savefig('04_trajectory')
    fig,ax=plt.subplots(3,1,figsize=(10,7),sharex=True)
    for label,d in diffs.items():
        d=d.assign(gps_tow_s=d.gps_tow_s.round(1)).set_index('gps_tow_s').reindex(np.round(full_grid,1)).rename_axis('gps_tow_s').reset_index()
        for a,c in zip(ax,['east_m','north_m','up_m']):a.plot((d.gps_tow_s-t0)/60,d[c],label=label.replace('SPP_minus_','SPP - ').replace('_',' '),lw=.8,alpha=.8)
    for a,c in zip(ax,['East difference (m)','North difference (m)','Up difference (m)']):a.set_ylabel(c);a.grid(alpha=.2)
    ax[0].legend();ax[0].set_title('Time-matched differences between solutions; not true positioning errors');ax[-1].set_xlabel('Minutes from first observation');fig.tight_layout();savefig('05_solution_differences')
    fig,ax=plt.subplots(2,1,figsize=(10,6),sharex=True)
    ax[0].plot((own_plot.gps_tow_s-t0)/60,own_plot.postfit_rms_m);ax[0].set(ylabel='Pseudorange residual RMS (m)',title='GPS elevation WLS diagnostics')
    ax[1].plot((pvt.gps_tow_s-t0)/60,pvt.speed_mps);ax[1].set(xlabel='Minutes from first observation',ylabel='Receiver ground speed (m/s)',title='Motion indicator; first 60 seconds confirmed static by the user')
    for a in ax:a.grid(alpha=.2)
    fig.tight_layout();savefig('06_residuals_and_motion')
    raw.groupby('system').agg(observation_records=('satellite_id','size'),unique_satellites=('satellite_id','nunique'),cno_mean_dbhz=('cno_dbhz','mean'),cno_median_dbhz=('cno_dbhz','median'),fraction_below_30_dbhz=('cno_dbhz',lambda x:float((x<30).mean())),elevation_median_deg=('elevation_deg','median')).to_csv(OUT/'raw_quality_by_system.csv')
    counts.describe().to_csv(OUT/'satellite_count_statistics.csv')
    counts.to_csv(OUT/'satellites_per_epoch.csv')

def static_analysis(results,ref,t0):
    stats=[];fig,ax=plt.subplots(1,2,figsize=(11,5))
    for name,df in [('uniform',results['own_uniform']),('elevation',results['own_elevation']),('huber',results['own_huber']),('receiver',ref)]:
        d=df[(df.gps_tow_s>=t0-.02)&(df.gps_tow_s<t0+60-.02)]
        xyz=d[HEADER[2:]].to_numpy();mean=xyz.mean(axis=0);enu=(xyz-mean)@rotation(mean).T;radius=np.linalg.norm(enu[:,:2],axis=1)
        st={'method':name,'epochs':len(d),'window_start_tow_s':float(t0),'duration_seconds':60,'mean_ecef_m':mean.tolist(),'mean_llh':list(ecef_to_lla(*mean)),'sample_std_enu_m':enu.std(axis=0,ddof=1).tolist(),'rms_horizontal_about_mean_m':float(np.sqrt(np.mean(radius**2))),'p95_horizontal_about_mean_m':float(np.percentile(radius,95)),'interpretation':'scatter about own mean; not absolute accuracy'}
        stats.append(st)
        if name in ['elevation','huber','receiver']:ax[0].scatter(enu[:,0],enu[:,1],s=12,alpha=.7,label=name)
        if name=='elevation':
            sc=ax[1].scatter(enu[:,0],enu[:,1],c=(d.gps_tow_s-t0),s=20,cmap='viridis');fig.colorbar(sc,ax=ax[1],label='Seconds from first observation')
            for c,v in zip(['east_m','north_m','up_m'],enu.T):d=d.assign(**{c:v})
            d.to_csv(OUT/'static_first60_elevation.csv',index=False)
    for a in ax:a.set(xlabel='East about own mean (m)',ylabel='North about own mean (m)');a.axis('equal');a.grid(alpha=.2)
    ax[0].set_title('Confirmed first 60 seconds: centered scatter');ax[0].legend()
    ax[1].set_title('Elevation WLS: centered static scatter')
    fig.tight_layout();savefig('07_static_first60')
    (OUT/'static_first60_statistics.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
    pd.DataFrame([{'method':x['method'],'epochs':x['epochs'],'std_e_m':x['sample_std_enu_m'][0],'std_n_m':x['sample_std_enu_m'][1],'std_u_m':x['sample_std_enu_m'][2],'rms_h_about_mean_m':x['rms_horizontal_about_mean_m'],'p95_h_about_mean_m':x['p95_horizontal_about_mean_m']} for x in stats]).to_csv(OUT/'static_first60_statistics.csv',index=False)
    return stats

def checks():
    rng=np.random.default_rng(19);true=np.array([-2418200.,5385800.,2405780.,4200.])
    dirs=rng.normal(size=(12,3));dirs/=np.linalg.norm(dirs,axis=1)[:,None];sp=true[:3]+dirs*2.3e7
    pred,_,_=model(sp,true)
    x,*_=solve(sp,pred,np.zeros(3),'uniform')
    assert np.linalg.norm(x-true)<.001
    a,e=read_inputs(ROOT/'inputs/example');rows,rej=historical_run(a,e,'historical');m=reference_metrics(rows,ROOT/'inputs/example/NAV-HPPOSECEF.csv',e)
    assert len(rows)==186 and abs(m['rmse_2d_m']-37.911)<.002 and abs(m['rmse_3d_m']-51.043)<.002
    return {'synthetic_exact_state_error_m':float(np.linalg.norm(x-true)),'historical_example_regression':m}

def main():
    for directory in [OUT, FIG, ROOT/'submission', ROOT/'logs']:
        directory.mkdir(parents=True,exist_ok=True)
    validation=checks();(OUT/'verification.json').write_text(json.dumps(validation,indent=2))
    # Each new algorithm is exercised on the example before benchmark processing.
    results={};summaries=[]
    for dataset,folder in [('example',ROOT/'inputs/example_modern'),('own',ROOT/'inputs/own'),('benchmark',ROOT/'inputs/benchmark')]:
        for method in ['uniform','elevation','huber']:
            tag=dataset+'_'+method;df,m=run_variant(folder,tag,method);results[tag]=df;summaries.append(m);print(tag,len(df),flush=True)
    ref,pvt,dop,info=parse_receiver()
    gps=parse_pos(OUT/'rtklib_gps.pos');multi=parse_pos(OUT/'rtklib_multi.pos')
    metrics=[];diffs={}
    for label,b in [('SPP_minus_receiver',ref),('SPP_minus_RTKLIB_GPS',gps),('SPP_minus_RTKLIB_multi',multi)]:
        m,d=compare(results['own_elevation'],b,label);metrics.append(m);diffs[label]=d
    m,d=compare(gps,ref,'RTKLIB_GPS_minus_receiver');metrics.append(m)
    for method in ['uniform','huber']:
        m,d=compare(results['own_'+method],ref,method+'_SPP_minus_receiver');metrics.append(m)
    # Evaluate each modern example method against its provided receiver reference.
    eref=pd.read_csv(ROOT/'inputs/example/NAV-HPPOSECEF.csv');edf=pd.DataFrame({'gps_week':[int(read_inputs(ROOT/'inputs/example_modern')[1][0][0])]*len(eref),'gps_tow_s':eref.iTOW/1000,'x_ecef_m':eref.ecefX/100,'y_ecef_m':eref.ecefY/100,'z_ecef_m':eref.ecefZ/100})
    example_metrics=[]
    for method in ['uniform','elevation','huber']:
        m,d=compare(results['example_'+method],edf,'example_'+method+'_minus_receiver');example_metrics.append(m)
    # Preserve candidate CSVs for review; elevation WLS is retained for the two reproducible candidate CSVs; it is not an accuracy ranking.
    for dataset,name in [('own','owndata'),('benchmark','benchmark')]:
        final=ROOT/'submission'/f'G19_{name}.csv';write_submission(results[dataset+'_elevation'],final)
        errors,n,cov=check(final,week=2158 if dataset=='benchmark' else 2442,epoch_file=ROOT/'inputs'/('own' if dataset=='own' else 'benchmark')/'epochs.csv')
        assert not errors,(name,errors)
        validation[name+'_submission']={'errors':errors,'rows':n,'obs_coverage_percent':cov}
        for method in ['uniform','huber']:write_submission(results[dataset+'_'+method],OUT/(dataset+'_'+method)/f'G19_{name}.csv')
    raw=pd.read_csv(ROOT/'inputs/own/raw_observations.csv');static_stats=static_analysis(results,ref,raw.gps_tow_s.min());plots(raw,results['own_elevation'],ref,pvt,dop,diffs,results['benchmark_elevation'])
    full={'own_comparisons':metrics,'example_modern_comparisons':example_metrics,'variants':summaries,'raw_log':info,'verification':validation,'static_statistics':static_stats}
    (OUT/'results_summary.json').write_text(json.dumps(full,indent=2),encoding='utf-8')
    (OUT/'verification.json').write_text(json.dumps(validation,indent=2),encoding='utf-8')
    pd.DataFrame(summaries).to_csv(OUT/'ablation_local_metrics.csv',index=False)
    pd.DataFrame([{'file':str(f.relative_to(ROOT)),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in (ROOT/'raw').iterdir() if f.is_file()]).to_csv(OUT/'source_manifest.csv',index=False)
    print(json.dumps({'own_comparisons':metrics,'example_modern_comparisons':example_metrics,'verification':validation},indent=2))
if __name__=='__main__':main()
