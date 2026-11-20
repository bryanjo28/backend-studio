"""Local-only animation API. Run one uvicorn worker without reload."""
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

STYLES = ['emerald', 'ember', 'arctic', 'sakura', 'retro']
PUBLIC_EXT = {'.png', '.jpg', '.jpeg', '.jfif', '.webp', '.wav', '.mp3', '.m4a', '.ogg', '.flac', '.mp4', '.txt', '.srt', '.vtt'}
SLUG = r'^[a-z0-9][a-z0-9_-]{0,63}$'


class Settings(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str = Field(default='Untitled', min_length=1, max_length=200)
    aspect: Literal['16:9', '9:16'] = '16:9'
    resolution: Literal['720p', '1080p', '1440p', '2160p'] = '1080p'
    fps: Literal[24, 30] = 24
    style: Literal['emerald', 'ember', 'arctic', 'sakura', 'retro'] = 'emerald'
    captions: bool = False
    renderer: Literal['growkaz','remotion'] = 'growkaz'


class Visual(BaseModel):
    model_config = ConfigDict(extra='forbid')
    background: str | None = None
    foreground: str | None = None
    title: str = Field(default='',max_length=160)
    subtitle: str = Field(default='',max_length=300)
    motion: Literal['push-in','pull-out','pan-left','pan-right','static'] = 'push-in'
    dim: float = Field(default=0.15,ge=0,le=0.7,allow_inf_nan=False)
    transition: Literal['fade','cut'] = 'fade'
    foregroundX: float = Field(default=0.65,ge=0.1,le=0.9,allow_inf_nan=False)
    foregroundScale: float = Field(default=0.65,ge=0.2,le=1,allow_inf_nan=False)


class NewProject(Settings):
    slug: str = Field(pattern=SLUG)
    template: Literal['empty', 'demo'] = 'empty'


class RenderRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    kind: Literal['sheet', 'preview', 'render', 'mix'] = 'sheet'
    start: float = Field(default=0, ge=0, le=86400, allow_inf_nan=False)
    end: float = Field(default=10, gt=0, le=86400, allow_inf_nan=False)
    scale: float = Field(default=0.5, ge=0.1, le=1, allow_inf_nan=False)


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    temp.replace(path)


def create_app(root=None):
    root = Path(root or Path(__file__).resolve().parents[1]).resolve()
    projects = root/'projects'
    projects.mkdir(exist_ok=True)
    jobs = {}
    lock = threading.RLock()
    worker = ThreadPoolExecutor(max_workers=1)
    app = FastAPI(title='Local Animation Studio API', version='1.0.0')
    origins = os.getenv('STUDIO_CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000').split(',')
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=['GET','POST','PUT','PATCH','DELETE'], allow_headers=['Content-Type'])

    def project(slug):
        if not re.fullmatch(SLUG, slug):
            raise HTTPException(422, 'Invalid project slug')
        p = (projects/slug).resolve()
        if p.parent != projects.resolve() or not (p/'config.json').is_file():
            raise HTTPException(404, 'Project not found')
        return p

    def summary(p):
        cfg = read_json(p/'config.json')
        story = read_json(p/'story/shots.json')
        with lock:
            history = [dict(j) for j in reversed(list(jobs.values())) if j['slug'] == p.name]
        artifacts = [file_url(p.name,f,p) for directory in ('build','out') for f in sorted((p/directory).rglob('*')) if f.is_file() and f.suffix.lower() in ('.mp4','.png','.wav') and 'parts' not in f.relative_to(p).parts]
        voice = (p/(cfg.get('voiceover') or '__missing__')).resolve()
        return {'slug':p.name, 'title':cfg.get('title',p.name), 'config':cfg, 'story':story,
                'has_story':bool(story.get('shots')), 'has_scene':bool(story.get('shots')) if cfg.get('renderer') == 'remotion' else bool(list((p/'scenes/shots').glob('*.js'))),
                'has_narration':voice.is_relative_to(p) and voice.is_file(),
                'has_full_render':(p/'build/video_silent.mp4').is_file(),
                'jobs':history, 'active_job':next((j for j in history if j['status'] in ('queued','running')),None),
                'last_job':history[0] if history else None, 'artifacts':artifacts}

    def idle(slug):
        if any(j['slug'] == slug and j['status'] in ('queued','running') for j in jobs.values()):
            raise HTTPException(409, 'Project has an active render; wait before editing')

    def file_url(slug, p, base):
        return f'/api/projects/{slug}/files/{p.relative_to(base).as_posix()}'

    def validate_story(story, allow_empty=False):
        shots = story.get('shots')
        if not isinstance(shots, list) or (not shots and not allow_empty):
            raise HTTPException(422, 'shots must be a nonempty array')
        end = 0.0
        ids = set()
        for shot in shots:
            if not isinstance(shot, dict):
                raise HTTPException(422, 'Invalid shot')
            sid, start, stop = shot.get('id'), shot.get('start'), shot.get('end')
            if not isinstance(sid, str) or not re.fullmatch(SLUG, sid) or sid in ids:
                raise HTTPException(422, 'Shot IDs must be unique simple names')
            if any(isinstance(v, bool) or not isinstance(v, (float,int)) or not math.isfinite(v) for v in (start, stop)):
                raise HTTPException(422, 'Shot start/end must be finite numbers')
            if abs(start-end) > 0.001 or stop <= start or stop > 86400:
                raise HTTPException(422, 'Shots must be contiguous from zero with positive duration')
            ids.add(sid)
            end = stop
        duration = story.get('duration', end)
        if not isinstance(duration, (int,float)) or not math.isfinite(duration) or abs(duration-end) > 0.001:
            raise HTTPException(422, 'duration must equal the final shot end')
        return end

    def validate_visuals(p, story):
        for shot in story['shots']:
            if 'visual' not in shot:
                continue
            try:
                visual = Visual.model_validate(shot['visual'])
            except ValueError as e:
                raise HTTPException(422, str(e))
            for relative in (visual.background,visual.foreground):
                if relative:
                    asset = (p/relative).resolve()
                    if not asset.is_relative_to((p/'input/assets').resolve()) or not asset.is_file() or asset.suffix.lower() not in ('.png','.jpg','.jpeg', '.jfif','.webp'):
                        raise HTTPException(422,'Visual assets must be uploaded project images under input/assets/')

    @app.get('/api/health')
    def health():
        return {'status':'ok', 'version':'1.0.0', 'renderer':(root/'render.mjs').exists(), 'ffmpeg':bool(shutil.which('ffmpeg')), 'node':bool(shutil.which('node'))}

    @app.get('/api/styles')
    def styles():
        return [{'id':s,'name':s.title()} for s in STYLES]

    @app.get('/api/projects')
    def list_projects():
        return [summary(p) for p in sorted(projects.iterdir()) if p.is_dir() and (p/'config.json').is_file() and re.fullmatch(SLUG,p.name)]

    @app.post('/api/projects', status_code=201)
    def new_project(data: NewProject):
        with lock:
            p = projects/data.slug
            if p.exists():
                raise HTTPException(409, 'Project already exists')
            if data.template == 'demo':
                source = root/'examples/reaction-time'
                if not source.exists():
                    raise HTTPException(409, 'Demo is not installed')
                shutil.copytree(source, p, ignore=shutil.ignore_patterns('build','out','__pycache__'))
                cfg = read_json(p/'config.json')
            else:
                cfg = {'duration':0, 'voiceover':None, 'script':None, 'fadeIn':0.5, 'fadeOut':0.8, 'music':{'enabled':True,'gainDb':-17}, 'sfx':{'enabled':True,'gainDb':-6}, 'loudness':-14}
                write_json(p/'story/shots.json', {'title':data.title,'duration':0,'shots':[],'music':[]})
            cfg.update(data.model_dump(exclude={'slug','template'}))
            for d in ['input/assets/characters','input/assets/backgrounds','input/assets/props','timeline','scenes/sets','scenes/shots','audio','build','out']:
                (p/d).mkdir(parents=True, exist_ok=True)
            write_json(p/'config.json',cfg)
            return summary(p)

    @app.get('/api/projects/{slug}')
    def get_project(slug: str):
        return summary(project(slug))

    @app.patch('/api/projects/{slug}/config')
    def update_config(slug: str, data: dict):
        p = project(slug)
        with lock:
            idle(slug)
            cfg = read_json(p/'config.json')
            values = {k:cfg[k] for k in Settings.model_fields if k in cfg}
            values.update(data)
            try:
                checked = Settings.model_validate(values)
            except ValueError as e:
                raise HTTPException(422, str(e))
            cfg.update(checked.model_dump())
            write_json(p/'config.json',cfg)
        return cfg

    @app.put('/api/projects/{slug}/story')
    def update_story(slug: str, story: dict):
        p = project(slug)
        duration = validate_story(story, allow_empty=True)
        validate_visuals(p,story)
        with lock:
            idle(slug)
            write_json(p/'story/shots.json',story)
            cfg = read_json(p/'config.json')
            cfg['duration'] = duration
            write_json(p/'config.json',cfg)
        return story

    @app.get('/api/projects/{slug}/story')
    def get_story(slug: str):
        return read_json(project(slug)/'story/shots.json')

    @app.get('/api/projects/{slug}/jobs')
    def project_jobs(slug: str):
        project(slug)
        with lock:
            return [dict(j) for j in reversed(list(jobs.values())) if j['slug'] == slug]

    @app.put('/api/projects/{slug}/storyline')
    def storyline(slug: str, data: dict):
        p = project(slug)
        text = data.get('text')
        if not isinstance(text,str) or len(text)>200000:
            raise HTTPException(422,'text must be a string of at most 200000 characters')
        with lock:
            idle(slug)
            (p/'story/bible.md').write_text(text,encoding='utf-8')
        return {'text':text}

    @app.get('/api/projects/{slug}/storyline')
    def get_storyline(slug: str):
        path = project(slug)/'story/bible.md'
        return {'text':path.read_text(encoding='utf-8') if path.exists() else ''}

    @app.get('/api/projects/{slug}/assets')
    def assets(slug: str):
        p = project(slug)
        return [{'path':f.relative_to(p).as_posix(),'url':file_url(slug,f,p),'size':f.stat().st_size} for f in sorted((p/'input').rglob('*')) if f.is_file() and f.suffix.lower() in PUBLIC_EXT]

    @app.post('/api/projects/{slug}/assets', status_code=201)
    def upload(slug: str, file: UploadFile = File(...), category: Literal['characters','backgrounds','props','voiceover','script'] = Form('props')):
        p = project(slug)
        ext = Path(file.filename or '').suffix.lower()
        allowed = {'.png','.jpg','.jpeg', '.jfif','.webp'} if category in ('characters','backgrounds','props') else ({'.txt','.srt','.vtt'} if category == 'script' else {'.mp3','.wav','.m4a','.ogg','.flac'})
        if ext not in allowed:
            raise HTTPException(422,'Unsupported file extension for this category')
        relative = f'input/assets/{category}/{uuid.uuid4().hex}{ext}' if category in ('characters','backgrounds','props') else f'input/{category}-{uuid.uuid4().hex}{ext}'
        dest = p/relative
        with lock:
            idle(slug)
            try:
                size = 0
                with dest.open('xb') as out:
                    while chunk := file.file.read(1024*1024):
                        size += len(chunk)
                        if size > 100*1024*1024:
                            raise HTTPException(413,'Maximum upload is 100 MiB')
                        out.write(chunk)
                if category in ('voiceover','script'):
                    cfg = read_json(p/'config.json')
                    cfg[category] = relative
                    write_json(p/'config.json',cfg)
            except Exception:
                dest.unlink(missing_ok=True)
                raise
            finally:
                file.file.close()
        return {'path':relative,'url':file_url(slug,dest,p),'size':size}

    @app.delete('/api/projects/{slug}/assets',status_code=204)
    def delete_asset(slug: str, path: str):
        p = project(slug)
        dest = (p/path).resolve()
        if not dest.is_relative_to(p) or not dest.is_relative_to((p/'input').resolve()) or not dest.is_file() or dest.suffix.lower() not in PUBLIC_EXT:
            raise HTTPException(404,'Aset tidak ditemukan')
        relative = dest.relative_to(p).as_posix()
        def contains(value):
            if isinstance(value,dict): return any(contains(v) for v in value.values())
            if isinstance(value,list): return any(contains(v) for v in value)
            return value == relative
        with lock:
            idle(slug)
            if not dest.is_file():
                raise HTTPException(404,'Aset tidak ditemukan')
            story = read_json(p/'story/shots.json')
            used_in_code = any(dest.name in f.read_text(encoding='utf-8',errors='ignore') for f in (p/'scenes').rglob('*.js'))
            if contains(story) or used_in_code:
                raise HTTPException(409,'Aset masih dipakai di adegan. Lepaskan atau ganti aset pada adegan, simpan, lalu hapus kembali.')
            cfg = read_json(p/'config.json')
            for key in ('voiceover','script'):
                if cfg.get(key) == relative: cfg[key] = None
            write_json(p/'config.json',cfg)
            dest.unlink()
        return Response(status_code=204)

    @app.get('/api/projects/{slug}/files/{relative:path}')
    def download(slug: str, relative: str):
        p = project(slug)
        dest = (p/relative).resolve()
        if not dest.is_relative_to(p) or not dest.is_file() or dest.suffix.lower() not in PUBLIC_EXT or relative.split('/')[0] not in ('input','build','out'):
            raise HTTPException(404,'File not available')
        return FileResponse(dest, media_type='image/jpeg' if dest.suffix.lower() == '.jfif' else None)

    def execute(jid, command, output_dir):
        with lock:
            job = jobs[jid]
            job.update(status='running',started_at=time.time())
        try:
            env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUNBUFFERED='1')
            proc = subprocess.Popen(command,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',env=env)
            errors = False
            for line in proc.stdout:
                with lock:
                    job['log'] = (job['log'] + line)[-24000:]
                    if any(t in line.lower() for t in ('shot error','[pageerror]','import error','shots have no scene')):
                        errors = True
            code = proc.wait()
            p = project(job['slug'])
            artifacts = [file_url(job['slug'],f,p) for f in output_dir.rglob('*') if f.is_file() and f.suffix.lower() in ('.png','.mp4','.wav') and f.stat().st_mtime >= job['started_at']-1 and 'parts' not in f.parts]
            with lock:
                job.update(status='succeeded' if code==0 and not errors and artifacts else 'failed',exit_code=code,artifacts=artifacts)
        except Exception as e:
            with lock:
                job.update(status='failed',error=str(e))
        finally:
            with lock:
                job['finished_at'] = time.time()

    @app.post('/api/projects/{slug}/jobs',status_code=202)
    def render(slug: str, data: RenderRequest):
        p = project(slug)
        story = read_json(p/'story/shots.json')
        if not story.get('shots'):
            raise HTTPException(409,'No shots. Author scenes first or create a demo project.')
        duration = validate_story(story)
        cfg = read_json(p/'config.json')
        is_remotion = cfg.get('renderer') == 'remotion'
        if is_remotion:
            validate_visuals(p,story)
        if not is_remotion and not list((p/'scenes/shots').glob('*.js')):
            raise HTTPException(409,'No scene modules. Story text alone cannot be rendered.')
        cmd = ['node',str(root/'render.mjs'),'--project',str(p),'--workers','1']
        output_dir = p/'build'
        if data.kind == 'sheet':
            cmd += ['--sheet','--scale',str(data.scale)]
            output_dir = p/'build/sheets'
        elif data.kind == 'preview':
            end = min(data.end,duration)
            if data.start >= end:
                raise HTTPException(422,'Preview start must precede end and project duration')
            cmd += ['--from',str(data.start),'--to',str(end),'--scale',str(data.scale)]
        elif data.kind == 'mix':
            cfg = read_json(p/'config.json')
            voice = (p/(cfg.get('voiceover') or '__missing__')).resolve()
            if not voice.is_relative_to(p) or not voice.is_file() or not (p/'build/video_silent.mp4').is_file():
                raise HTTPException(409,'Mix requires uploaded narration and a completed full render')
            cmd = [sys.executable,str(root/'audio/mix.py'),'--project',str(p)]
            output_dir = p/'out'
        if is_remotion and data.kind != 'mix':
            frontend = root.parent/'2d-project-studio'
            cmd = ['node',str(frontend/'scripts/render-remotion.mjs'),'--project',str(p),'--kind',data.kind,'--start',str(data.start),'--end',str(min(data.end,duration)),'--scale',str(data.scale)]
        with lock:
            idle(slug)
            if sum(j['status'] in ('running','queued') for j in jobs.values()) >= 8:
                raise HTTPException(429,'Render queue is full')
            jid = uuid.uuid4().hex
            job = {'id':jid,'slug':slug,'kind':data.kind,'status':'queued','created_at':time.time(),'log':'','artifacts':[]}
            jobs[jid] = job
            worker.submit(execute,jid,cmd,output_dir)
            return dict(job)

    @app.get('/api/jobs/{jid}')
    def get_job(jid: str):
        with lock:
            if jid not in jobs:
                raise HTTPException(404,'Job not found (job history resets when server restarts)')
            return dict(jobs[jid])

    return app


app = create_app()
