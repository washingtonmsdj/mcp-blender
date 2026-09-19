"""Local .blend copies and guarded recovery; no automatic deletion or cloud upload."""
import hashlib
import json
import math
import shutil
import time
import uuid
from pathlib import Path


def identifier(value):
    if not isinstance(value, str) or uuid.UUID(value).hex != value:
        raise ValueError('checkpoint_id must be a UUID hex string')
    return value


def root_path(project):
    root = (Path(project) / '.ordax/blender/checkpoints').resolve()
    if not root.is_relative_to(Path(project).resolve()):
        raise ValueError('Checkpoint directory escapes project')
    return root


def _inside(root, path):
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError('Checkpoint path escapes storage')
    return resolved


def _write(path, data):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data), encoding='utf-8')
    temporary.replace(path)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def listing(project, limit=20):
    root = root_path(project)
    records = []
    if root.is_dir():
        for path in root.glob('*/checkpoint.json'):
            try:
                identifier(path.parent.name)
                path = _inside(root, path)
                if path.stat().st_size > 65536:
                    continue
                data = json.loads(path.read_text(encoding='utf-8'))
                created = data.get('created_at') if isinstance(data, dict) else None
                if isinstance(created, (int, float)) and math.isfinite(created) and data.get('checkpoint_id') == path.parent.name:
                    records.append(data)
            except (ValueError, OSError, TypeError, AttributeError):
                continue
    records.sort(key=lambda item: item.get('created_at', 0), reverse=True)
    return {'checkpoints': records[:max(1, min(100, int(limit)))], 'total': len(records),
            'integrity': 'Hashes are verified when restoring, not while listing'}


def _ready():
    import bpy
    if bpy.context.mode != 'OBJECT' or bpy.app.is_job_running('RENDER'):
        raise ValueError('Checkpoint operations require Object Mode and no running render')
    if any(image.is_dirty and image.type not in ('RENDER_RESULT', 'COMPOSITING') for image in bpy.data.images):
        raise ValueError('Save dirty image data explicitly before checkpointing; a .blend is not a complete external-asset backup')


def create(state, label='manual'):
    import bpy
    if not state['allow_checkpoints']:
        raise ValueError('Checkpoint creation is not authorized in this session')
    if not isinstance(label, str) or len(label) > 160:
        raise ValueError('Checkpoint label must contain at most 160 characters')
    _ready()
    root = root_path(state['project'])
    root.mkdir(parents=True, exist_ok=True)
    if len(list(root.iterdir())) >= 100:
        raise ValueError('Checkpoint storage reached 100 entries; review retention locally')
    if shutil.disk_usage(root).free < 512 * 1024 * 1024:
        raise ValueError('Less than 512 MiB free; checkpoint refused')
    checkpoint_id = uuid.uuid4().hex
    directory = root / checkpoint_id
    directory.mkdir()
    path = directory / 'checkpoint.blend'
    source = bpy.data.filepath
    dirty = bpy.data.is_dirty
    saved = bpy.ops.wm.save_as_mainfile(filepath=str(path), copy=True, relative_remap=True,
                                       compress=False, check_existing=False)
    if 'FINISHED' not in saved or not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError('Blender did not finish saving the checkpoint')
    if bpy.data.filepath != source:
        raise RuntimeError('Checkpoint unexpectedly changed active file; inspect Blender before continuing')
    metadata = {'checkpoint_id': checkpoint_id, 'sha256': digest(path),
                'label': label, 'created_at': time.time(), 'source_file': source,
                'source_was_dirty': dirty, 'size_bytes': path.stat().st_size,
                'blender_version': bpy.app.version_string,
                'external_assets': 'Not copied; preserve external resources and caches separately'}
    _write(directory / 'checkpoint.json', metadata)
    return metadata


def restore(state, arguments, command_id):
    import bpy
    if not state['allow_restore'] or not state['allow_checkpoints']:
        raise ValueError('Restoration and safety backups must both be authorized locally')
    if arguments.get('confirm_replace_scene') is not True:
        raise ValueError('confirm_replace_scene: true is required')
    checkpoint_id = identifier(arguments.get('checkpoint_id'))
    _ready()
    root = root_path(state['project'])
    directory = _inside(root, root / checkpoint_id)
    path = _inside(root, directory / 'checkpoint.blend')
    metadata_path = _inside(root, directory / 'checkpoint.json')
    if metadata_path.stat().st_size > 65536:
        raise ValueError('Invalid checkpoint metadata')
    metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    expected = arguments.get('expected_sha256')
    if not isinstance(expected, str) or len(expected) != 64 or metadata.get('checkpoint_id') != checkpoint_id or metadata.get('sha256') != expected or digest(path) != expected:
        raise ValueError('Checkpoint hash/id mismatch; inspect before restoring')
    backup = create(state, f'before restoring {checkpoint_id}')
    state['operation_checkpoint'] = backup
    # Same directory preserves remapped relative asset paths. Never open the immutable checkpoint itself.
    recovery = directory / f'recovery-{identifier(command_id)}.blend'
    if recovery.exists():
        raise ValueError('Recovery working copy already exists; inspect previous outcome')
    with path.open('rb') as source, recovery.open('xb') as output:
        shutil.copyfileobj(source, output)
    if digest(recovery) != expected:
        raise ValueError('Recovery working copy failed integrity verification')
    journal = {'restored_checkpoint_id': checkpoint_id, 'safety_checkpoint': backup,
               'working_file': str(recovery), 'status': 'opening',
               'original_file_overwritten': False}
    state['recovery'] = journal
    _write(directory / f'recovery-{command_id}.json', journal)
    state['session'] = uuid.uuid4().hex  # Invalidate commands queued against the previous scene.
    opened = bpy.ops.wm.open_mainfile(filepath=str(recovery), load_ui=False, use_scripts=False)
    if 'FINISHED' not in opened or Path(bpy.data.filepath).resolve() != recovery.resolve():
        raise RuntimeError('Restore did not finish; inspect recovery journal and current Blender state')
    journal.update(status='restored', session=state['session'])
    _write(directory / f'recovery-{command_id}.json', journal)
    return journal
