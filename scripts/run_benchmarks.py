"""Matriz C1-C6; subprocessos isolados, três repetições, JSON/CSV/SVG sem dependências extras."""
import argparse
import csv
import json
import os
import platform
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from genresearch.ingestion.pipeline import generate_corpus, ingest


def matrix():
    rows=[]
    for size in (120, 1200):
        for case in ('C1','C2'):
            rows.append({'case':case,'documents':size})
    for consumers in (1,2,4):
        rows.append({'case':'C3','consumers':consumers,'cache_capacity':1,'unique_queries':40})
    for capacity, unique in ((2,5),(8,5),(8,40)):
        rows.append({'case':'C4','cache_capacity':capacity,'unique_queries':unique})
    for size in (120,1200):
        rows.append({'case':'C5','documents':size})
    rows.append({'case':'C6'})
    return rows


def svg_bars(rows, path, title, metric, ylabel):
    width=850; height=75+len(rows)*38
    values=[float(r[metric]) for r in rows]
    maximum=max(values+[1])
    esc=lambda s:__import__('html').escape(str(s))
    lines=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
           '<rect width="100%" height="100%" fill="white"/>',
           f'<text x="16" y="26" font-size="18" font-family="sans-serif">{esc(title)}</text>',
           f'<text x="16" y="46" font-size="12" fill="#555" font-family="sans-serif">{esc(ylabel)}</text>']
    for i,r in enumerate(rows):
        y=67+i*38
        label=r['label']; value=float(r[metric]); length=round(480*value/maximum)
        lines.extend([f'<text x="16" y="{y+17}" font-size="13" font-family="sans-serif">{esc(label)}</text>',
                      f'<rect x="290" y="{y}" width="{length}" height="22" fill="#2563a5"/>',
                      f'<text x="{300+length}" y="{y+16}" font-size="12" font-family="sans-serif">{value:.2f}</text>'])
    lines.append('</svg>'); path.write_text('\n'.join(lines),encoding='utf-8')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--repetitions',type=int,default=3)
    p.add_argument('--quick',action='store_true',help='validação rápida; não substitui 3 repetições oficiais')
    a=p.parse_args()
    if a.repetitions<1: p.error('repetitions >= 1')
    configs=matrix()
    if a.quick: configs=[{'case':'C1','documents':120},{'case':'C2','documents':120},
                         {'case':'C3','consumers':2,'cache_capacity':1,'unique_queries':40},
                         {'case':'C4','cache_capacity':8,'unique_queries':5},{'case':'C5','documents':120},
                         {'case':'C6'}]
    sizes=sorted(set(c.get('documents',120) for c in configs))
    for size in sizes:
        corpus=ROOT/f'data/generated/benchmark_{size}_corpus.jsonl'
        index=ROOT/f'data/generated/benchmark_{size}_index.jsonl'
        print(f'Preparando corpus {size} documentos...',flush=True)
        generate_corpus(corpus,size,42)
        ingest(corpus,index)
    out=ROOT/'results/raw/benchmark_av2.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    runs=[]; failures=[]
    for config_id,config in enumerate(configs):
        for repeat in range(1,(1 if a.quick else a.repetitions)+1):
            command=[sys.executable,str(ROOT/'scripts/benchmark_case.py')]
            for key,value in {**config,'repeat':repeat}.items():
                command.extend(['--'+key.replace('_','-'),str(value)])
            proc=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=120)
            if proc.returncode:
                failures.append({'config':config,'repeat':repeat,'stderr':proc.stderr[-2000:]})
                print('FALHA',config,repeat,proc.stderr[-300:],flush=True)
            else:
                result=json.loads(proc.stdout)
                result['config_id']=config_id
                runs.append(result)
                print(f"{result['case']} cfg={config_id} rep={repeat}: {result['elapsed_ms']:.2f} ms",flush=True)
    metadata={'timestamp_utc':datetime.now(timezone.utc).isoformat(),
              'python':sys.version,'kernel':platform.release(),
              'platform':platform.platform(),'command':sys.argv,
              'commit':subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True).stdout.strip(),
              'filesystems':subprocess.run(['df','-T',str(ROOT)],capture_output=True,text=True).stdout.strip(),
              'note':'RSS/VSZ coletados em dois instantes; podem subestimar picos. /proc/self/io read_bytes mede E/S física e pode ser zero com cache de páginas quente.'}
    out.write_text(json.dumps({'metadata':metadata,'configs':configs,'runs':runs,'failures':failures},indent=2,ensure_ascii=False),encoding='utf-8')
    summary=[]
    for i,config in enumerate(configs):
        group=[r for r in runs if r['config_id']==i]
        if not group:continue
        times=[r['elapsed_ms'] for r in group]
        def avg(path):
            values=[]
            for r in group:
                obj=r
                for k in path:obj=obj.get(k) if isinstance(obj,dict) else None
                if isinstance(obj,(int,float)):values.append(obj)
            return round(statistics.mean(values),4) if values else ''
        summary.append({'config_id':i,**config,'n':len(group),
                        'mean_elapsed_ms':round(statistics.mean(times),4),
                        'median_elapsed_ms':round(statistics.median(times),4),
                        'p95_elapsed_ms':round(sorted(times)[min(len(times)-1,__import__('math').ceil(.95*len(times))-1)],4),
                        'mean_rss_end_kib':avg(['process','rss_kib_end']),
                        'mean_vsz_end_kib':avg(['process','vsz_kib_end']),
                        'mean_minor_faults':avg(['process','minor_faults_delta']),
                        'mean_major_faults':avg(['process','major_faults_delta']),
                        'mean_read_bytes':avg(['process','io_delta','read_bytes']),
                        'mean_throughput':avg(['pipeline','throughput_req_s']),
                        'mean_cache_hit_rate':avg(['hit_rate']),
                        'mean_latency_p95_ms':avg(['latency_p95_ms']),
                        'mean_read_first_ms':avg(['read_ms_first']),
                        'mean_read_second_ms':avg(['read_ms_second'])})
    csv_path=ROOT/'results/metrics/benchmark_summary.csv';csv_path.parent.mkdir(parents=True,exist_ok=True)
    keys=list(dict.fromkeys(k for r in summary for k in r))
    with csv_path.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows(summary)
    plots=ROOT/'results/plots';plots.mkdir(parents=True,exist_ok=True)
    svg_bars([{'label':f"{r['case']} {r.get('documents',120)} docs",'value':r['mean_read_first_ms']} for r in summary if r['case'] in ('C1','C2')],
             plots/'reading.svg','Leitura de indice C1 vs C2','value','Primeira leitura (ms)')
    svg_bars([{'label':f"C3 {r['consumers']} consumidores",'value':r['mean_throughput']} for r in summary if r['case']=='C3'],
             plots/'concurrency.svg','Vazao por numero de consumidores','value','Requisicoes por segundo')
    svg_bars([{'label':f"C4 cache={r['cache_capacity']} consultas={r['unique_queries']}",'value':r['mean_cache_hit_rate']*100} for r in summary if r['case']=='C4'],
             plots/'cache.svg','Taxa de acerto do cache','value','Hits (%)')
    print('\nArquivos:',out,csv_path,plots,sep='\n')
    if failures: raise SystemExit(f'{len(failures)} configuracoes falharam; veja benchmark_av2.json')

if __name__=='__main__':main()
