"""Private provider selectors; unverifiable identities are never reported verified."""
from contextvars import ContextVar
from pathlib import Path
import os
from .util import WorkflowError, digest, json_text, read_json

expected = ContextVar('plovi_identity_selector', default=None)
ALLOWED_ENV = {'codex': {'CODEX_HOME'}, 'claude': {'CLAUDE_CONFIG_DIR'}, 'cursor': set()}


def policy(project):
    value=read_json(project.config/'local/provider-identities.json',{})
    if not isinstance(value,dict) or set(value)-set(ALLOWED_ENV):raise WorkflowError('Invalid private provider identity policy')
    for provider, entry in value.items():
        if not isinstance(entry,dict) or set(entry)-{'config_env','verification'}:raise WorkflowError('Invalid private provider identity entry')
        if entry.get('verification','allow-unverified') not in {'required','allow-unverified'}:raise WorkflowError('Invalid provider identity verification policy')
        env=entry.get('config_env',{})
        if not isinstance(env,dict) or set(env)-ALLOWED_ENV[provider] or any(not isinstance(v,str) or not Path(v).is_absolute() for v in env.values()):
            raise WorkflowError('Provider configuration selectors must use supported absolute config paths')
    return value


def fingerprint(project):
    return digest(json_text({'providers':policy(project),'claude':read_json(project.config/'local/claude-account.json'),
                             'claude_required':(project.config/'local/claude-account.required').exists()}))


def assert_unchanged(project):
    previous=expected.get()
    if previous is not None and previous!=fingerprint(project):
        raise WorkflowError('Provider identity configuration changed during execution; review and rebind before continuing')


def environment(project,cwd,*,inherited=None):
    from .providers import claude_environment
    assert_unchanged(project)
    selected=policy(project)
    env=dict(os.environ if inherited is None else inherited)
    for provider, entry in selected.items():
        if provider!='claude' and entry.get('verification')=='required':
            raise WorkflowError('This provider cannot expose a verified account identity; review its provider policy before use')
        env.update(entry.get('config_env',{}))
    guarded=claude_environment(project,cwd,inherited=env)
    if selected.get('claude',{}).get('verification')=='required' and guarded is None:
        raise WorkflowError('Configure the required private Claude account guard before use')
    return guarded or (env if selected else None)


def capabilities(project):
    selected=policy(project)
    return {p:('configured-guard' if p=='claude' and (project.config/'local/claude-account.json').exists() else
               'required-unavailable' if selected.get(p,{}).get('verification')=='required' else 'unverified')
            for p in project.profile['agents']}
