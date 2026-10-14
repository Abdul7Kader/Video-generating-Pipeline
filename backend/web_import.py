"""Explicit manual JSON exchange with web LLMs, sharing production validation."""
from __future__ import annotations

import json
import re

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from . import planner, story
from .assets import render_plan_readiness
from .continuity import normalize_continuity
from .plan import finalize_scene_plan
from .production import production_plan_readiness
from .schemas import JobCreate, ScriptDraft, Scene, VersionAction
from .visual_coverage import visual_coverage_issues


class WebStoryRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request: JobCreate
    response: str = Field(default='', max_length=100000)


class WebRevision(VersionAction):
    model_config = ConfigDict(extra='forbid')
    instructions: str = Field(min_length=3, max_length=4000)
    response: str = Field(default='', max_length=100000)


class WebBoard(VersionAction):
    model_config = ConfigDict(extra='forbid')
    response: str = Field(default='', max_length=300000)


def parse_response(text):
    if not isinstance(text, str) or len(text.encode('utf-8')) > 1024 * 1024:
        raise ValueError('Die Antwort ist zu groß oder kein Text.')
    text = text.strip()
    fenced = re.fullmatch(r'```(?:json)?\s*\n(.*?)\n```', text, re.S | re.I)
    if fenced:
        text = fenced.group(1)

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError()
            result[key] = value
        return result

    def constant(_):
        raise ValueError()

    try:
        value = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
        if not isinstance(value, dict):
            raise ValueError()
        # Bound nesting before handing an untrusted object to schema validation.
        def depth(node, level=0):
            if level > 24:
                raise ValueError()
            for child in node.values() if isinstance(node, dict) else node if isinstance(node, list) else []:
                depth(child, level+1)
        depth(value)
        return value
    except (ValueError, RecursionError):
        raise ValueError('Bitte die vollständige JSON-Antwort einfügen. Zusätzliche Texte, doppelte Felder und ungültige Zahlen sind nicht erlaubt.') from None


def validate_story(request, response, *, previous=None, instructions=''):
    try:
        value = story.StoryDraft.model_validate(parse_response(response)).model_dump()
    except ValidationError:
        raise ValueError('Die Antwort braucht title, description, narration, visual_summary und fact_check_notes gemäß dem kopierten Prompt, ohne zusätzliche Felder.') from None
    _, budget = story.story_prompt(request, previous=previous, instructions=instructions)
    issues = story.story_quality_issues(value, budget[1], budget[2])
    if issues:
        raise ValueError(' '.join(issues))
    return story.build_story(request, value, budget, previous=previous, instructions=instructions)


def prompt_text(prompt, schema):
    return planner._system_prompt()+'\n\n'+prompt+'\nReturn ONLY one JSON object. No prose outside JSON. Schema:\n'+json.dumps(schema, ensure_ascii=False)


def validate_board(request, approved, response):
    raw = parse_response(response)
    if set(raw) - set(ScriptDraft.model_fields):
        raise ValueError('Der Zeichenplan enthält nicht erlaubte Zusatzfelder.')
    for scene in raw.get('scenes', []) if isinstance(raw.get('scenes'), list) else []:
        if not isinstance(scene, dict) or set(scene) - set(Scene.model_fields):
            raise ValueError('Die Zeichenantwort enthält ungültige Szenen oder Zusatzfelder.')
        if scene.get('source_strategy') not in (None, 'procedural') or any(scene.get(key) for key in ('source_ref', 'asset_query', 'asset_prompt')):
            raise ValueError('Der Web-Zeichenplan darf keine externen Medien oder Dateipfade verwenden.')
    try:
        plan = ScriptDraft.model_validate(raw).model_dump()
    except ValidationError as exc:
        locations = ', '.join('.'.join(map(str, item['loc'])) for item in exc.errors(include_input=False)[:6])
        raise ValueError('Zeichenplan entspricht nicht dem Schema. Prüfe diese Felder: '+locations) from None
    planner._validate_editorial_output(plan)
    if story.spoken_story(plan) != story.spoken_story(approved):
        raise ValueError('Der Zeichenplan hat den freigegebenen Sprechertext verändert. Alle Wörter vollständig und unverändert übernehmen.')
    plan['scenes'] = normalize_continuity(plan['scenes'])
    issues = production_plan_readiness(request.production_config.model_dump(), plan['scenes']) + render_plan_readiness(plan['scenes']) + visual_coverage_issues(plan['scenes'], request.topic)
    if issues:
        raise ValueError(' '.join(issues))
    plan['title'], plan['description'] = approved['title'], approved['description']
    plan['metadata'] = {'workflow': 'storyboard', 'provider': 'web_import', 'model': None,
        'approved_story_hash': approved['content_hash'], 'approved_story_version': approved['version'],
        'continuity_policy': 'identity-and-props-v1', **{key: approved.get('metadata', {}).get(key) for key in ('visual_summary', 'fact_check_notes', 'story_quality', 'web_input_hash')}}
    return finalize_scene_plan(plan, request.duration_seconds, approved)
