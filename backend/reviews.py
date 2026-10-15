"""Durable, version-bound Discord outbox; uncertain sends never retry by themselves."""
import json
import uuid

from .db import utcnow


class Reviews:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def decode(row):
        if not row:
            return None
        value = dict(row)
        value['targets'] = json.loads(value.pop('targets_json'))
        value['options'] = json.loads(value.pop('options_json'))
        return value

    def get(self, identifier):
        with self.db.connect() as conn:
            return self.decode(conn.execute('SELECT * FROM discord_reviews WHERE id=?', (identifier,)).fetchone())

    def latest(self, job_id):
        with self.db.connect() as conn:
            return self.decode(conn.execute('SELECT * FROM discord_reviews WHERE job_id=? ORDER BY created_at DESC LIMIT 1', (job_id,)).fetchone())

    def enqueue(self, job_id, preferences, *, kind='video', force=False):
        with self.db._write_lock, self.db.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            job = conn.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
            if not job:
                raise ValueError('Auftrag fehlt.')
            version = job['render_version'] if kind == 'video' else job['script_version']
            fingerprint = job['output_sha256'] if kind == 'video' else self.db._verified_script_hash(conn, job_id, version)
            if kind == 'video' and (not fingerprint or job['status'] not in {'video_review', 'video_rejected'}):
                raise ValueError('Nur ein fertiges ungepostetes Video kann zur Abnahme gesendet werden.')
            old = conn.execute('SELECT * FROM discord_reviews WHERE job_id=? ORDER BY created_at DESC LIMIT 1', (job_id,)).fetchone()
            if old and old['state'] in {'queued','sending','deciding','revising','planning','revision_requested','render_requested'}:
                return self.decode(old)
            if old and old['kind'] == kind and old['version'] == version and old['fingerprint'] == fingerprint and not force:
                return self.decode(old)
            identifier, now = uuid.uuid4().hex, utcnow()
            conn.execute("UPDATE discord_reviews SET state='superseded',updated_at=? WHERE job_id=? AND state IN ('queued','sent','failed','unknown')", (now, job_id))
            conn.execute('''INSERT INTO discord_reviews
                (id,job_id,kind,version,fingerprint,guild_id,channel_id,targets_json,options_json,state,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,'queued',?,?)''', (identifier,job_id,kind,version,fingerprint,
                preferences.discord_guild_id,preferences.discord_channel_id,json.dumps(preferences.publish_targets),
                json.dumps({'connection_revision':preferences.connection_revision,'youtube_privacy':preferences.youtube_privacy}),now,now))
            if kind == 'video' and job['status'] == 'video_rejected':
                conn.execute("UPDATE jobs SET status='video_review',updated_at=? WHERE id=?", (now, job_id))
            self.db._event(conn, job_id, 'discord_queued', 'Zur Discord-Abnahme eingereiht; noch nicht veröffentlicht.')
            conn.commit()
        return self.get(identifier)

    def transition(self, identifier, expected, state, *, message_id=None, actor_id=None, instructions=None, error=None, options=None):
        if not expected:
            return False
        with self.db._write_lock, self.db.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            placeholders = ','.join('?' for _ in expected)
            changed = conn.execute(f'''UPDATE discord_reviews SET state=?,updated_at=?,message_id=COALESCE(?,message_id),
                actor_id=COALESCE(?,actor_id),instructions=COALESCE(?,instructions),error=?,options_json=COALESCE(?,options_json)
                WHERE id=? AND state IN ({placeholders})''', (state,utcnow(),message_id,actor_id,instructions,error,
                json.dumps(options) if options is not None else None,identifier,*expected)).rowcount
            conn.commit()
            return bool(changed)

    def claim(self):
        with self.db._write_lock, self.db.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute("SELECT * FROM discord_reviews WHERE state IN ('queued','revision_requested','render_requested') ORDER BY updated_at LIMIT 1").fetchone()
            if not row:
                return None
            next_state = {'queued':'sending', 'revision_requested':'revising', 'render_requested':'planning'}[row['state']]
            conn.execute('UPDATE discord_reviews SET state=?,updated_at=? WHERE id=?', (next_state,utcnow(),row['id']))
            conn.commit()
            value = self.decode(row)
            value['state'] = next_state
            return value

    def recover(self):
        with self.db._write_lock, self.db.connect() as conn:
            conn.execute("UPDATE discord_reviews SET state='unknown',error=?,updated_at=? WHERE state='sending'", ('Übertragung unterbrochen; Discord prüfen. Keine automatische Wiederholung.',utcnow()))
            conn.execute("UPDATE discord_reviews SET state='failed',error=?,updated_at=? WHERE state IN ('revising','planning','deciding')", ('Vorgang unterbrochen; aktuelle Version prüfen und bei Bedarf erneut anfordern.',utcnow()))
            conn.commit()
