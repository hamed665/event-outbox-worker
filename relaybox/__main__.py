import json
from .core import Outbox
queue=Outbox()
queue.write('demo-shop','event-1','order-1',{'status':'paid','amount_cents':2500},now=0)
first=queue.claim(now=0)
queue.finish(first,now=1,error='synthetic downstream timeout')
retry=queue.claim(now=3)
queue.finish(retry,now=4)
print(json.dumps({'delivery_attempts':retry['attempts'],'states':queue.stats()},indent=2))
queue.close()
