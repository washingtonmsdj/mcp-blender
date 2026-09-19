"""Load explicitly in Blender's Python Console; no socket, worker thread or auto-save.

runpy.run_path(COMPANION_PATH)['start'](PROJECT_ROOT)
"""
import hashlib
import json
import runpy
import time
import uuid
from pathlib import Path

import bpy

_STATE = None


def _write(path, data):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data), encoding='utf-8')
    temporary.replace(path)


def _scene(limit=64):
    objects = list(bpy.context.scene.objects)
    return {'file': bpy.data.filepath, 'unsaved_changes': bpy.data.is_dirty,
            'scene': bpy.context.scene.name, 'mode': bpy.context.mode,
            'object_count': len(objects), 'truncated': len(objects) > limit,
            'objects': [{'name': o.name, 'type': o.type,
                         'selected': o.select_get(), 'location': list(o.location),
                         'dimensions': list(o.dimensions)} for o in objects[:limit]]}


def _dispatch(request):
    state = _STATE
    if request.get('session') != state['session']:
        raise ValueError('Session changed; observe again before acting')
    if float(request['deadline']) < time.time():
        raise ValueError('Command expired before execution')
    current_file = bpy.data.filepath
    if current_file and not Path(current_file).resolve().is_relative_to(state['project']):
        raise ValueError('Open Blender file is outside the paired project')
    args = request.get('arguments', {})
    if request['action'] == 'inspect':
        return _scene(max(1, min(1000, int(args.get('limit', 64)))))
    if request['action'] == 'capture':
        capture = runpy.run_path(str(Path(__file__).with_name('blender_multiview.py')))['capture']
        return capture(args, state['ipc'] / 'captures' / request['id'])
    if request['action'] != 'run_script' or not state['allow_scripts']:
        raise ValueError('Action not allowed by this local companion')
    script = Path(args['script']).resolve()
    if not script.is_relative_to(state['scripts']) or not script.is_relative_to(state['project']) or script.suffix.lower() != '.py':
        raise ValueError('Script is outside the locally authorized scripts directory')
    content = script.read_bytes()
    if hashlib.sha256(content).hexdigest() != args['sha256']:
        raise ValueError('Script changed after submission')
    # Deliberately trusted local code, NOT a Python security sandbox.
    exec(compile(content, str(script), 'exec'), {'__name__': '__main__', '__file__': str(script), 'bpy': bpy})
    return _scene()


def _tick():
    state = _STATE
    if state is None:
        return None
    try:
        _write(state['ipc'] / 'presence.json', {
            'session': state['session'], 'project_root': str(state['project']),
            'file': bpy.data.filepath, 'allow_scripts': state['allow_scripts'],
            'blender_version': bpy.app.version_string, 'observed_at': time.time(),
            'actions': ['inspect', 'capture'] + (['run_script'] if state['allow_scripts'] else []),
        })
        # One command per timer tick keeps the event loop available between commands.
        for path in sorted((state['ipc'] / 'inbox').glob('*.json')):
            try:
                if uuid.UUID(path.stem).hex != path.stem:
                    continue
            except ValueError:
                continue
            response = state['ipc'] / 'responses' / path.name
            claimed = state['ipc'] / 'processing' / path.name
            if response.exists() or claimed.exists():
                continue  # Never replay a command, including after an uncertain crash.
            path.replace(claimed)
            started = time.monotonic()
            try:
                request = json.loads(claimed.read_text(encoding='utf-8'))
                if request.get('id') != path.stem:
                    raise ValueError('Command identifier mismatch')
                data = _dispatch(request)
                ok, summary = True, 'Blender live command completed'
            except Exception as error:
                ok, summary, data = False, f'{type(error).__name__}: {error}', {}
            data.update(command_id=path.stem, session=state['session'], transport='blender-live',
                        duration_seconds=round(time.monotonic() - started, 3))
            _write(response, {'ok': ok, 'summary': summary, 'data': data})
            break
    except Exception as error:
        print(f'OrdaX companion error: {error}')
    return .2


def start(project_root, *, allow_scripts=False, scripts_dir='automation/blender'):
    """Explicitly pair this Blender instance. Existing scene is never loaded or saved."""
    global _STATE
    if _STATE is not None:
        raise RuntimeError('Companion is already running')
    project = Path(project_root).resolve(strict=True)
    if not project.is_dir():
        raise ValueError('Project root must be a directory')
    scripts = (project / scripts_dir).resolve()
    if not scripts.is_relative_to(project):
        raise ValueError('scripts_dir must remain inside project')
    if bpy.data.filepath and not Path(bpy.data.filepath).resolve().is_relative_to(project):
        raise ValueError('Open file does not belong to this project')
    ipc = (project / '.ordax/blender').resolve()
    if not ipc.is_relative_to(project):
        raise ValueError('IPC directory must remain inside project')
    for name in ('inbox', 'processing', 'responses'):
        (ipc / name).mkdir(parents=True, exist_ok=True)
    lock = (ipc / 'session.lock').open('a+b')
    try:
        import os
        if os.name == 'nt':
            import msvcrt
            if lock.seek(0, 2) == 0:
                lock.write(b'0')
                lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except Exception:
        lock.close()
        raise RuntimeError('Another Blender companion already owns this project')
    _STATE = {'project': project, 'scripts': scripts, 'ipc': ipc, 'lock': lock,
              'session': uuid.uuid4().hex, 'allow_scripts': bool(allow_scripts)}
    try:
        bpy.app.timers.register(_tick, first_interval=.2, persistent=True)
    except Exception:
        lock.close()
        _STATE = None
        raise
    _tick()
    return {'session': _STATE['session'], 'project': str(project)}


def stop():
    global _STATE
    if _STATE is None:
        return
    if bpy.app.timers.is_registered(_tick):
        bpy.app.timers.unregister(_tick)
    # Remove our heartbeat before releasing the exclusive session lock.
    (_STATE['ipc'] / 'presence.json').unlink(missing_ok=True)
    _STATE['lock'].close()
    _STATE = None
