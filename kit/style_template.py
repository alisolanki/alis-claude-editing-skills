from pathlib import Path
import argparse,json,shutil,subprocess,os,sys,html,re,math,urllib.request

def main(skill_dir):
    skill_dir=Path(skill_dir).resolve();pack=skill_dir.parents[1]
    parser=argparse.ArgumentParser(description='Build this 4.2-second editing template (vertical 9:16 or horizontal 16:9).')
    parser.add_argument('spec',nargs='?',type=Path)
    parser.add_argument('--prepare-only',action='store_true')
    args=parser.parse_args()
    spec=json.loads(args.spec.read_text()) if args.spec else {}
    base=args.spec.resolve().parent if args.spec else pack
    def path(v):
        q=Path(v);return q if q.is_absolute() else base/q
    out=path(spec.get('out','.work/'+skill_dir.name+'.mp4')).resolve()
    comp=out.parent/(out.stem+'.composition');comp.mkdir(parents=True,exist_ok=True)
    shutil.copytree(pack/'kit/fonts',comp/'fonts',dirs_exist_ok=True)
    vendor=pack/'kit/vendor/gsap-3.15.0.min.js'
    if not vendor.is_file():
        vendor.parent.mkdir(parents=True,exist_ok=True)
        temporary=vendor.with_suffix('.download')
        try:
            with urllib.request.urlopen('https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js', timeout=30) as response:
                temporary.write_bytes(response.read())
            if b'GSAP 3.15.0' not in temporary.read_bytes()[:500]:
                raise ValueError('Unexpected GSAP download; retry or supply the pinned file in kit/vendor')
            temporary.replace(vendor)
        finally:
            temporary.unlink(missing_ok=True)
    (comp/'vendor').mkdir(exist_ok=True)
    shutil.copyfile(vendor,comp/'vendor/gsap.min.js')
    (comp/'assets').mkdir(exist_ok=True)
    fmt=str(spec.get('format','vertical')).lower()
    fmt={'9:16':'vertical','portrait':'vertical','16:9':'horizontal','landscape':'horizontal'}.get(fmt,fmt)
    if fmt not in ('vertical','horizontal'):raise ValueError('format must be vertical or horizontal')
    size=(1080,1920) if fmt=='vertical' else (1920,1080)
    tpl=skill_dir/('template.html' if fmt=='vertical' else 'template-16x9.html')
    if not tpl.is_file():raise FileNotFoundError(f'{skill_dir.name} has no {fmt} template yet ({tpl.name})')
    source=tpl.read_text()
    assets=set(re.findall(r'(?:src|href)="assets/([^"\s]+)"',source))
    media_start=float(spec.get('media_start',.04))
    if not math.isfinite(media_start) or media_start<0:
        raise ValueError('media_start must be a finite, non-negative number')
    overrides=spec.get('assets',{})
    if 'speaker_cut.webm' in assets and (('speaker.mp4' in overrides) != ('speaker_cut.webm' in overrides)) and 'speaker.mp4' in assets:
        raise ValueError('Replace speaker.mp4 and speaker_cut.webm together with frame-matched footage')
    unknown=set(overrides)-assets
    if unknown:raise ValueError('Unknown asset keys: '+', '.join(sorted(unknown)))
    for name in assets:
        # defaults: your own files dropped into assets/my-media/ win over the bundled samples
        mine=pack/'assets/my-media'/(name if fmt=='vertical' else name.replace('speaker','speaker-16x9'))
        src=path(overrides[name]) if name in overrides else mine if mine.is_file() else pack/'assets/style-showcase'/name
        if not src.is_file():
            if name.startswith('speaker'):
                raise FileNotFoundError(f'No speaker footage: pass "assets": {{"{name}": "your-file"}} in the spec, or put it at {mine}. '
                                        'No sample speaker is bundled; make a cutout with kit/cutout.py.')
            raise FileNotFoundError(src)
        if src.suffix.lower() in ['.mp4','.webm']:
            probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(src)]))
            v=next(s for s in probe['streams'] if s['codec_type']=='video')
            if (v['width'],v['height'])!=size:raise ValueError(f'{name}: prepare a {size[0]}x{size[1]} source first')
            if float(probe['format']['duration'])<float(spec.get('media_start',.04))+4.2:raise ValueError(f'{name}: source is shorter than the requested 4.2-second window')
        shutil.copyfile(src,comp/'assets'/name)
    if 'media_start' in spec:
        source=re.sub(r'data-media-start="[^"]+"',f'data-media-start="{float(spec["media_start"]):.6f}"',source)
    for before,after in spec.get('text',{}).items():
        # Only plain HTML text substitutions; GSAP textContent strings should be edited in the template.
        if before not in source:raise ValueError('Text not found: '+before)
        source=source.replace(before,html.escape(str(after),quote=True))
    (comp/'index.html').write_text(source)
    (comp/'hyperframes.json').write_text(json.dumps({'media':{'autoProxy':False}}))
    print(comp,flush=True)
    if args.prepare_only:return
    cli=['node',os.environ['HYPERFRAMES_CLI']] if os.environ.get('HYPERFRAMES_CLI') else ['npx','--yes','hyperframes@0.8.214']
    subprocess.run(cli+['check',str(comp),'--json'],check=True)
    subprocess.run(cli+['render',str(comp),'-o',str(out),'--fps','30','--quality','looks','--workers','2'],check=True)
    subprocess.run(['ffmpeg','-v','error','-i',str(out),'-f','null','-'],check=True)
    print(out)
