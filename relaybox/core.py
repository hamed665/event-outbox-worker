"""Local outbox: atomic entity+event write; fenced leases and manual recovery."""
import json
import math
import sqlite3
import uuid

def validate_time(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("finite numeric timestamp required")

class StaleLease(ValueError): pass

class Outbox:
    def __init__(self,path=':memory:',max_attempts=3):
        if type(max_attempts) is not int or max_attempts < 1: raise ValueError('positive max_attempts required')
        self.max_attempts=max_attempts
        self.db=sqlite3.connect(path,isolation_level=None,timeout=5)
        self.db.row_factory=sqlite3.Row
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS entities(tenant TEXT, entity_id TEXT, body TEXT, PRIMARY KEY(tenant,entity_id));
        CREATE TABLE IF NOT EXISTS outbox(tenant TEXT, event_id TEXT, entity_id TEXT, payload TEXT,
          state TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, available REAL NOT NULL,
          lease_until REAL, token TEXT, last_error TEXT, PRIMARY KEY(tenant,event_id));
        CREATE INDEX IF NOT EXISTS ready_events ON outbox(state,available,lease_until);
        """)

    def write(self,tenant,event_id,entity_id,body,now):
        validate_time(now)
        if not all(isinstance(v,str) and v for v in (tenant,event_id,entity_id)): raise ValueError('identifiers required')
        encoded=json.dumps(body,sort_keys=True,separators=(',',':'),allow_nan=False)
        self.db.execute('BEGIN IMMEDIATE')
        try:
            old=self.db.execute('SELECT entity_id,payload FROM outbox WHERE tenant=? AND event_id=?',(tenant,event_id)).fetchone()
            if old:
                if (old['entity_id'],old['payload']) != (entity_id,encoded): raise ValueError('event key payload mismatch')
                self.db.commit(); return False
            self.db.execute('INSERT INTO entities VALUES(?,?,?) ON CONFLICT(tenant,entity_id) DO UPDATE SET body=excluded.body',(tenant,entity_id,encoded))
            self.db.execute("INSERT INTO outbox(tenant,event_id,entity_id,payload,state,available) VALUES(?,?,?,?,'pending',?)",(tenant,event_id,entity_id,encoded,now))
            self.db.commit(); return True
        except BaseException:
            self.db.rollback(); raise

    def claim(self,now,lease_seconds=30):
        validate_time(now)
        validate_time(lease_seconds)
        if lease_seconds <= 0: raise ValueError('positive lease required')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            # Crashed workers eventually consume their retry budget too.
            self.db.execute("UPDATE outbox SET state='dead',token=NULL WHERE state='leased' AND lease_until<=? AND attempts>=?",(now,self.max_attempts))
            row=self.db.execute("""SELECT * FROM outbox WHERE attempts<? AND
              ((state='pending' AND available<=?) OR (state='leased' AND lease_until<=?))
              ORDER BY available,tenant,event_id LIMIT 1""",(self.max_attempts,now,now)).fetchone()
            if not row: self.db.commit(); return None
            token=uuid.uuid4().hex
            self.db.execute("UPDATE outbox SET state='leased',attempts=attempts+1,lease_until=?,token=? WHERE tenant=? AND event_id=?",(now+lease_seconds,token,row['tenant'],row['event_id']))
            self.db.commit()
            return {**dict(row),'state':'leased','attempts':row['attempts']+1,'token':token,'lease_until':now+lease_seconds,'body':json.loads(row['payload'])}
        except BaseException:
            self.db.rollback(); raise

    def finish(self,job,now,error=None):
        validate_time(now)
        self.db.execute('BEGIN IMMEDIATE')
        try:
            current=self.db.execute("SELECT * FROM outbox WHERE tenant=? AND event_id=? AND state='leased' AND token=? AND lease_until>?",(job['tenant'],job['event_id'],job['token'],now)).fetchone()
            if not current: raise StaleLease('lease expired or superseded')
            if error is None: state,available='delivered',now
            else:
                state='dead' if current['attempts']>=self.max_attempts else 'pending'
                available=now+min(3600,2**min(current['attempts'],12))
            self.db.execute('UPDATE outbox SET state=?,available=?,token=NULL,lease_until=NULL,last_error=? WHERE tenant=? AND event_id=?',(state,available,str(error)[:500] if error is not None else None,job['tenant'],job['event_id']))
            self.db.commit(); return state
        except BaseException:
            self.db.rollback(); raise

    def requeue(self,tenant,event_id,now):
        validate_time(now)
        return self.db.execute("UPDATE outbox SET state='pending',attempts=0,available=?,last_error=NULL WHERE tenant=? AND event_id=? AND state='dead'",(now,tenant,event_id)).rowcount==1

    def stats(self):
        return {r['state']:r['n'] for r in self.db.execute('SELECT state,COUNT(*) AS n FROM outbox GROUP BY state')}

    def close(self): self.db.close()
